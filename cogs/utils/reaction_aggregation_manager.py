import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Column
from sqlalchemy.sql.sqltypes import DATETIME
from sqlalchemy.types import VARCHAR, BigInteger, Integer

try:
    from .db import engine
    from .remind_schedule import calc_next_remind_at, reschedule_with_new_hour
except BaseException:
    import sys

    sys.path.append("../utils")
    from db import engine
    from remind_schedule import calc_next_remind_at, reschedule_with_new_hour

Base = declarative_base()

# create_tableは複数cogのon_ready/before_loopから並行して呼ばれうるため、
# DDL(ALTER TABLE)の競合を避けてプロセス内で直列化する
_create_table_lock = asyncio.Lock()


@dataclass
class ReactionParameter:
    message_id: int
    command_id: int
    guild_id: int
    channel_id: int
    target_value: int
    sum: int
    matte: int
    author_id: int
    created_at: datetime
    notified_at: datetime | None
    remind: int | None
    next_remind_at: datetime | None
    ping_id: list[int]


class ReactionAggregation(Base):
    __tablename__ = "reactionaggregation"

    message_id = Column(BigInteger, primary_key=True)  # メッセージID
    guild_id = Column(BigInteger, nullable=False)  # ギルドID
    command_id = Column(BigInteger, nullable=False)  # コマンドID
    channel_id = Column(BigInteger, nullable=False)  # チャンネルID
    target_value = Column(Integer, nullable=False)  # 目標値
    sum = Column(Integer, default=0)  # 現在の合計値
    matte = Column(Integer, default=0)  # 待ってがついている数
    author_id = Column(BigInteger, nullable=False)  # 集めてる人のID
    created_at = Column(DATETIME, nullable=False)  # 集計開始時間
    notified_at = Column(DATETIME)  # 集計完了時間
    remind = Column(
        Integer, default=None
    )  # 旧リマインド管理カラム（未使用、互換のため残置）
    next_remind_at = Column(DATETIME, default=None)  # 次回リマインド予定時刻
    ping_id = Column(VARCHAR, default="")  # メンション先のID


class AggregationManager:
    @staticmethod
    def return_dataclass(db_data) -> ReactionParameter:
        """DBからの情報をデータクラスに変換する関数、もうちょっとなんとかならんか？？？


        Args:
            db_data (sqlalchemyの): DBから取り出したデータ

        Returns:
            ReactionParameter: データクラス
        """

        """
        ping_id_list = []
        guild_id_list_str = guild[0].ping_id.split(',')
        for guild_id_str in guild_id_list_str:
            if guild_id_str != '':
                id = int(guild_id_str)
                ping_id_list.append(id)
        """
        ping_id_list = [int(id) for id in db_data[0].ping_id.split(",") if id != ""]

        # awareなUTCのdatetimeに変換
        created_at = db_data[0].created_at.replace(tzinfo=ZoneInfo("UTC"))
        notified_at = None
        if db_data[0].notified_at is not None:
            notified_at = db_data[0].notified_at.replace(tzinfo=ZoneInfo("UTC"))
        next_remind_at = None
        if db_data[0].next_remind_at is not None:
            next_remind_at = db_data[0].next_remind_at.replace(tzinfo=ZoneInfo("UTC"))

        db_data_raw = ReactionParameter(
            message_id=db_data[0].message_id,
            command_id=db_data[0].command_id,
            guild_id=db_data[0].guild_id,
            channel_id=db_data[0].channel_id,
            target_value=db_data[0].target_value,
            sum=db_data[0].sum,
            matte=db_data[0].matte,
            author_id=db_data[0].author_id,
            created_at=created_at,
            notified_at=notified_at,
            remind=db_data[0].remind,
            next_remind_at=next_remind_at,
            ping_id=ping_id_list,
        )
        return db_data_raw

    async def create_table(self) -> None:
        async with _create_table_lock:
            async with engine.begin() as conn:
                await conn.run_sync(ReactionAggregation.metadata.create_all)

                result = await conn.exec_driver_sql(
                    "PRAGMA table_info(reactionaggregation)"
                )
                columns = {row[1] for row in result.fetchall()}
                if "next_remind_at" not in columns:
                    await conn.exec_driver_sql(
                        "ALTER TABLE reactionaggregation ADD COLUMN next_remind_at DATETIME"
                    )
                    # 旧remindカラムで初回送信済みだった行が未送信扱いに戻らないよう、
                    # 1週間後基準の直近21時へバックフィルする（デプロイ直後の一斉再通知を防ぐ）
                    migration_time = datetime.now(tz=ZoneInfo("UTC"))
                    backfill_at = calc_next_remind_at(
                        migration_time + timedelta(days=7), 21
                    ).replace(tzinfo=None)
                    await conn.exec_driver_sql(
                        "UPDATE reactionaggregation SET next_remind_at = ? WHERE remind IS NOT NULL",
                        (backfill_at,),
                    )

    async def register_aggregation(
        self,
        message_id: int,
        command_id: int,
        guild_id: int,
        channel_id: int,
        target_value: int,
        author_id: int,
        created_at: datetime,
        ping_id: str,
    ) -> None:
        """リアクション集計のパラメータを登録する関数

        Args:
            message_id (int): メッセージID
            command_id (int): コマンドID
            guild_id (int): サーバID
            channel_id (int): チャンネルID
            target_value (int): 目標値
            author_id (int): 集計者のID
            created_at (datetime): 作成日時
            ping_id (str): 対象のID
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                new_aggregation = ReactionAggregation(
                    message_id=message_id,
                    command_id=command_id,
                    guild_id=guild_id,
                    channel_id=channel_id,
                    target_value=target_value,
                    author_id=author_id,
                    created_at=created_at,
                    ping_id=ping_id,
                )

                session.add(new_aggregation)

    async def get_guild_list(self, guild_id: int) -> list[ReactionParameter] | None:
        """ギルドごとのリアクションのデータオブジェクトをリストで返す関数

        Args:
            guild_id (int): サーバーID

        Returns:
            list: ReactionParameterのリスト
        """
        guild_list = []

        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(ReactionAggregation).where(
                    ReactionAggregation.guild_id == guild_id
                )
                result = await session.execute(stmt)
                result = result.fetchall()

                # guild_list_raw = [guild[0] for guild in result]
                for guild in result:
                    guild_raw = self.return_dataclass(guild)
                    guild_list.append(guild_raw)

        if len(guild_list) == 0:
            return None
        else:
            return guild_list

    async def is_exist(self, message_id: int) -> bool:
        """引数のメッセージIDが集計中かを判定する関数

        Args:
            guild_id (int): サーバーID

        Returns:
            bool: あったらTrue、なかったらFalse
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(ReactionAggregation).where(
                    ReactionAggregation.message_id == message_id
                )
                result = await session.execute(stmt)
                result = result.fetchone()
                if result is not None:
                    return True
                else:
                    return False

    async def remove_aggregation(self, message_id: int) -> None:
        """リアクション集計を削除するコマンド

        Args:
            message_id (int): メッセージID
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = delete(ReactionAggregation).where(
                    ReactionAggregation.message_id == message_id
                )
                await session.execute(stmt)

    async def get_aggregation(self, message_id: int) -> ReactionParameter | None:
        """メッセージIDから集計中の情報を返す関数

        Args:
            message_id (int): 対象のメッセージID

        Returns:
            Union[None, ReactionParameter]: あれば情報、なければNone
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(ReactionAggregation).where(
                    ReactionAggregation.message_id == message_id
                )
                result = await session.execute(stmt)
                result = result.fetchone()
                if result is None:
                    return None
                else:
                    return self.return_dataclass(result)

    async def set_value_to_ping_id(self, message_id: int, ping_id: list[int]) -> None:
        """メンション対象のIDを更新する。"""
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = (
                    update(ReactionAggregation)
                    .where(ReactionAggregation.message_id == message_id)
                    .values(ping_id=",".join([str(id) for id in ping_id]))
                )
                await session.execute(stmt)

    async def set_value_to_sum(self, message_id: int, val: int) -> None:
        """sumカラムに値をセットする関数

        Args:
            message_id (int): メッセージID
            val (int): 値
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = (
                    update(ReactionAggregation)
                    .where(ReactionAggregation.message_id == message_id)
                    .values(sum=val)
                )
                await session.execute(stmt)

    async def set_value_to_matte(self, message_id: int, val: int) -> None:
        """matteカラムに値をセットする関数

        Args:
            message_id (int): メッセージID
            val (int): 値
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = (
                    update(ReactionAggregation)
                    .where(ReactionAggregation.message_id == message_id)
                    .values(matte=val)
                )
                await session.execute(stmt)

    async def set_value_to_notified(
        self, message_id: int, notified_time: datetime
    ) -> None:
        """通知時刻をセットする関数

        Args:
            message_id (int): メッセージID
            notified_time (datetime): 値
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = (
                    update(ReactionAggregation)
                    .where(ReactionAggregation.message_id == message_id)
                    .values(notified_at=notified_time)
                )
                await session.execute(stmt)

    async def unset_value_to_notified(self, message_id: int) -> None:
        """通知時刻をアンセットする関数

        Args:
            message_id (int): メッセージID
            notified_time (datetime): 値
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = (
                    update(ReactionAggregation)
                    .where(ReactionAggregation.message_id == message_id)
                    .values(notified_at=None)
                )
                await session.execute(stmt)

    async def set_value_to_next_remind_at(
        self, message_id: int, next_remind_at: datetime
    ) -> None:
        """次回リマインド予定時刻をセットする関数

        Args:
            message_id (int): メッセージID
            next_remind_at (datetime): 次回リマインド予定時刻
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = (
                    update(ReactionAggregation)
                    .where(ReactionAggregation.message_id == message_id)
                    .values(next_remind_at=next_remind_at)
                )
                await session.execute(stmt)

    async def get_notified_aggregation(self) -> list[ReactionParameter] | None:
        """通知済みのリアクション集計を取得する関数

        Returns:
            Union[None, list[ReactionParameter]]: なければNone、あったらリスト
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(ReactionAggregation).where(
                    ReactionAggregation.notified_at.isnot(None)
                )
                result = await session.execute(stmt)
                result = result.fetchall()
                result = [self.return_dataclass(reaction) for reaction in result]

        if len(result) == 0:
            return None
        else:
            return result

    async def get_unfinished_aggregation_by_guild(
        self, guild_id: int
    ) -> list[ReactionParameter] | None:
        """ギルドの未達成リアクション集計を取得する関数

        Args:
            guild_id (int): サーバーID

        Returns:
            Union[None, List[ReactionParameter]]: なければNone、あったらリスト
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(ReactionAggregation).where(
                    (ReactionAggregation.guild_id == guild_id)
                    & (ReactionAggregation.sum < ReactionAggregation.target_value)
                )
                result = await session.execute(stmt)
                result = result.fetchall()
                result = [self.return_dataclass(reaction) for reaction in result]

        if len(result) == 0:
            return None
        else:
            return result

    async def reschedule_unfinished_by_new_hour(
        self, guild_id: int, new_hour: int, now: datetime
    ) -> None:
        """ギルドのリマインド時刻設定変更に合わせ、初回送信済みの未完了集計を再スケジュールする

        初回未送信(next_remind_at is None)の集計は対象外にする。
        巻き込むと remind() が「送信済み」と誤判定し初回通知が遅延するため。

        Args:
            guild_id (int): サーバーID
            new_hour (int): 新しいリマインド時刻(0-23)
            now (datetime): 現在時刻
        """
        unfinished = await self.get_unfinished_aggregation_by_guild(guild_id)
        if unfinished is None:
            return

        for reaction in unfinished:
            if reaction.next_remind_at is None:
                continue
            new_next_remind_at = reschedule_with_new_hour(
                reaction.next_remind_at, new_hour, now
            )
            await self.set_value_to_next_remind_at(
                reaction.message_id, new_next_remind_at
            )

    async def get_all_aggregation(self) -> list[ReactionParameter] | None:
        """すべてのリアクション集計ギルドID順で取得する関数

        Returns:
            Union[None, List[ReactionParameter]]: なければNone、あったらリスト
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(ReactionAggregation).order_by(
                    ReactionAggregation.guild_id
                )
                result = await session.execute(stmt)
                result = result.fetchall()
                result = [self.return_dataclass(reaction) for reaction in result]

        if len(result) == 0:
            return None
        else:
            return result


if __name__ == "__main__":
    reaction_mng = AggregationManager()
    result = asyncio.run(reaction_mng.get_all_aggregation())

    if result is not None:
        for i in result:
            print(i)

    # asyncio.run(guild_mng.register_setting())

    # asyncio.run(reaction_mng.all_guild_id())
