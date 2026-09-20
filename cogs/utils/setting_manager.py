import asyncio
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Column
from sqlalchemy.types import BigInteger, Integer

try:
    from .db import engine
except ImportError:
    from db import engine

Base = declarative_base()

# create_tableは複数cogのon_ready/before_loopから並行して呼ばれうるため、
# DDL(ALTER TABLE)の競合を避けてプロセス内で直列化する
_create_table_lock = asyncio.Lock()


@dataclass
class GuildSetting:
    guild_id: int
    bot_manager_id: int
    bot_user_id: int
    remind_hour_offset: int


class GuildSettingDB(Base):
    __tablename__ = "setting"

    guild_id = Column(BigInteger, primary_key=True)  # サーバーID
    bot_manager_id = Column(BigInteger, default=0)  # ボット管理者のロールID
    bot_user_id = Column(BigInteger, default=0)  # ボット使用者のロールID
    remind_hour_offset = Column(
        Integer, default=0
    )  # リマインド時刻の21時からのオフセット(-1/0/+1)

    # メモ：dataclassにで扱うべし


class SettingManager:
    async def create_table(self) -> None:
        """テーブルを作成する関数"""
        async with _create_table_lock:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

                result = await conn.exec_driver_sql("PRAGMA table_info(setting)")
                columns = {row[1] for row in result.fetchall()}
                if "remind_hour_offset" not in columns:
                    await conn.exec_driver_sql(
                        "ALTER TABLE setting ADD COLUMN remind_hour_offset INTEGER DEFAULT 0"
                    )

            try:
                await self._init_setting()
            except BaseException:
                pass

    async def _init_setting(self) -> None:
        async with AsyncSession(engine, expire_on_commit=True) as session:
            async with session.begin():
                new_setting = GuildSettingDB(index=True)
                session.add(new_setting)

    async def register_guild(
        self, guild_id: int, bot_manager_id: int, bot_user_id: int
    ) -> None:
        """ギルドの設定を登録する関数

        Args:
            guild_id (int): サーバーID
            bot_manager_id (int): BOT管理者役職のID
            bot_user_id (int): BOT使用者役職のID
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                new_guild = GuildSettingDB(
                    guild_id=guild_id,
                    bot_manager_id=bot_manager_id,
                    bot_user_id=bot_user_id,
                )

                session.add(new_guild)

    async def update_guild(
        self, guild_id: int, bot_manager_id: int, bot_user_id: int
    ) -> None:
        """ギルドの設定を更新する関数

        Args:
            guild_id (int): サーバーID
            bot_manager_id (int): bot管理者のID
            bot_user_id (int): bot操作者のID
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = (
                    update(GuildSettingDB)
                    .where(GuildSettingDB.guild_id == guild_id)
                    .values(bot_manager_id=bot_manager_id, bot_user_id=bot_user_id)
                )
                await session.execute(stmt)

    async def is_exist(self, guild_id: int) -> bool:
        """主キーであるギルドIDが存在するかを判定する関数

        Args:
            guild_id (int): サーバーID

        Returns:
            bool: あったらTrue、なかったらFalse
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(GuildSettingDB).where(GuildSettingDB.guild_id == guild_id)
                result = await session.execute(stmt)
                result = result.fetchone()
                if result is not None:
                    return True
                else:
                    return False

    async def get_guild(self, guild_id: int) -> Optional[GuildSetting]:
        """ギルドの情報をGuildSettingで返す関数

        Args:
            guild_id (int): サーバーID

        Returns:
            GuildSetting: サーバの設定のデータクラス
        """
        async with AsyncSession(engine, expire_on_commit=True) as session:
            async with session.begin():
                stmt = select(GuildSettingDB).where(GuildSettingDB.guild_id == guild_id)
                result = await session.execute(stmt)
                result = result.fetchone()

                if result is None:
                    return None

                guildsetting = GuildSetting(
                    result[0].guild_id,
                    result[0].bot_manager_id,
                    result[0].bot_user_id,
                    result[0].remind_hour_offset or 0,
                )

        return guildsetting

    async def get_remind_hour_offset(self, guild_id: int) -> int:
        """ギルドのリマインド時刻オフセットを返す関数（未登録なら0）

        Args:
            guild_id (int): サーバーID

        Returns:
            int: 21時からのオフセット(-1/0/+1)
        """
        guild = await self.get_guild(guild_id)
        if guild is None:
            return 0
        return guild.remind_hour_offset

    async def set_remind_hour_offset(self, guild_id: int, offset: int) -> None:
        """ギルドのリマインド時刻オフセットを設定する関数

        Args:
            guild_id (int): サーバーID
            offset (int): 21時からのオフセット(-1/0/+1)
        """
        if offset not in (-1, 0, 1):
            raise ValueError(
                f"offsetは-1/0/1のいずれかである必要があります。offset={offset}"
            )

        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = (
                    update(GuildSettingDB)
                    .where(GuildSettingDB.guild_id == guild_id)
                    .values(remind_hour_offset=offset)
                )
                await session.execute(stmt)

    async def get_guild_ids(self) -> Optional[List[int]]:
        """沙雲が設定されているサーバーのid一覧を返す関数

        Returns:
            Optional[List[int]]: あればINTのリスト、なければNone
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(GuildSettingDB)
                result = await session.execute(stmt)
                result = result.fetchall()

                if len(result) == 0:
                    return None

                guild_ids = [id_[0].guild_id for id_ in result]
        return guild_ids


if __name__ == "__main__":
    setting_mng = SettingManager()
    asyncio.run(setting_mng.create_table())

    # asyncio.run(setting_mng.register_setting())

    result = asyncio.run(setting_mng.get_guild(410454762522411009))
    print((result))
