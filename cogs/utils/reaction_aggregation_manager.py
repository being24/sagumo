# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import pathlib
from dataclasses import dataclass
from datetime import datetime
from typing import List, Union

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Column
from sqlalchemy.sql.sqltypes import BOOLEAN, DATETIME
from sqlalchemy.types import VARCHAR, BigInteger, Integer

Base = declarative_base()


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
    notified_at: datetime
    remind: bool
    ping_id: list


class ReactionAggregation(Base):
    __tablename__ = 'reactionaggregation'

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
    remind = Column(BOOLEAN, default=False)  # リマインドしたかどうか？
    ping_id = Column(VARCHAR, default='')  # メンション先のID


class AggregationManager():
    def __init__(self):
        data_path = pathlib.Path(__file__).parents[1]
        data_path /= '../data'
        data_path = data_path.resolve()
        db_path = data_path
        db_path /= './data.sqlite3'
        self.engine = create_async_engine(
            f'sqlite:///{db_path}', echo=True)

    @staticmethod
    def return_dataclass(db_data) -> ReactionParameter:
        """DBからの情報をデータクラスに変換する関数、もうちょっとなんとかならんか？？？


        Args:
            db_data (sqlalchemyの): DBから取り出したデータ

        Returns:
            ReactionParameter: データクラス
        """

        '''
        ping_id_list = []
        guild_id_list_str = guild[0].ping_id.split(',')
        for guild_id_str in guild_id_list_str:
            if guild_id_str != '':
                id = int(guild_id_str)
                ping_id_list.append(id)
        '''
        ping_id_list = [
            int(id) for id in db_data[0].ping_id.split(',') if id != '']
        db_data_raw = ReactionParameter(
            message_id=db_data[0].message_id,
            command_id=db_data[0].command_id,
            guild_id=db_data[0].guild_id,
            channel_id=db_data[0].channel_id,
            target_value=db_data[0].target_value,
            sum=db_data[0].sum,
            matte=db_data[0].matte,
            author_id=db_data[0].author_id,
            created_at=db_data[0].created_at,
            notified_at=db_data[0].notified_at,
            remind=db_data[0].remind,
            ping_id=ping_id_list)
        return db_data_raw

    async def create_table(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(ReactionAggregation.metadata.create_all)

    async def register_aggregation(self, message_id: int, command_id: int, guild_id: int, channel_id: int, target_value: int, author_id: int, created_at: datetime, ping_id: str) -> None:
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
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                new_aggregation = ReactionAggregation(
                    message_id=message_id,
                    command_id=command_id,
                    guild_id=guild_id,
                    channel_id=channel_id,
                    target_value=target_value,
                    author_id=author_id,
                    created_at=created_at,
                    ping_id=ping_id)

                session.add(new_aggregation)

    async def get_guild_list(self, guild_id: int) -> Union[List[ReactionParameter], None]:
        """ギルドごとのリアクションのデータオブジェクトをリストで返す関数

        Args:
            guild_id (int): サーバーID

        Returns:
            list: ReactionParameterのリスト
        """
        guild_list = []

        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = select(ReactionAggregation).where(
                    ReactionAggregation.guild_id == guild_id)
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
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = select(ReactionAggregation).where(
                    ReactionAggregation.message_id == message_id)
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
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = delete(ReactionAggregation).where(
                    ReactionAggregation.message_id == message_id)
                await session.execute(stmt)

    async def get_aggregation(self, message_id: int) -> Union[None, ReactionParameter]:
        """メッセージIDから集計中の情報を返す関数

        Args:
            message_id (int): 対象のメッセージID

        Returns:
            Union[None, ReactionParameter]: あれば情報、なければNone
        """
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = select(ReactionAggregation).where(
                    ReactionAggregation.message_id == message_id)
                result = await session.execute(stmt)
                result = result.fetchone()
                if result is None:
                    return None
                else:
                    return self.return_dataclass(result)

    async def set_value_to_sum(self, message_id: int, val: int) -> None:
        """sumカラムに値をセットする関数

        Args:
            message_id (int): メッセージID
            val (int): 値
        """
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(ReactionAggregation).where(
                    ReactionAggregation.message_id == message_id).values(
                    sum=val)
                await session.execute(stmt)

    async def set_value_to_matte(self, message_id: int, val: int) -> None:
        """matteカラムに値をセットする関数

        Args:
            message_id (int): メッセージID
            val (int): 値
        """
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(ReactionAggregation).where(
                    ReactionAggregation.message_id == message_id).values(
                    matte=val)
                await session.execute(stmt)

    async def set_value_to_notified(self, message_id: int, notified_time: datetime) -> None:
        """通知時刻をセットする関数

        Args:
            message_id (int): メッセージID
            notified_time (datetime): 値
        """
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(ReactionAggregation).where(
                    ReactionAggregation.message_id == message_id).values(
                    notified_at=notified_time)
                await session.execute(stmt)

    async def unset_value_to_notified(self, message_id: int) -> None:
        """通知時刻をアンセットする関数

        Args:
            message_id (int): メッセージID
            notified_time (datetime): 値
        """
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(ReactionAggregation).where(
                    ReactionAggregation.message_id == message_id).values(
                    notified_at=None)
                await session.execute(stmt)

    async def set_value_to_remind(self, message_id: int, value: bool) -> None:
        """リマインドされたかをセットする関数

        Args:
            message_id (int): メッセージID
            value (bool): 値
        """
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(ReactionAggregation).where(
                    ReactionAggregation.message_id == message_id).values(
                    remind=value)
                await session.execute(stmt)

    async def get_notified_aggregation(self) -> Union[None, List[ReactionParameter]]:
        """通知済みのリアクション集計を取得する関数

        Returns:
            Union[None, list[ReactionParameter]]: なければNone、あったらリスト
        """
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = select(ReactionAggregation).where(
                    ReactionAggregation.notified_at.isnot(None))
                result = await session.execute(stmt)
                result = result.fetchall()
                result = [self.return_dataclass(reaction)
                          for reaction in result]

        if len(result) == 0:
            return None
        else:
            return result

    async def get_all_not_reminded_aggregation(self) -> Union[None, List[ReactionParameter]]:
        """リマインドされてないリアクション集計をギルドID順で取得する関数

        Returns:
            Union[None, List[ReactionParameter]]: なければNone、あったらリスト
        """
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = select(ReactionAggregation).where(
                    ReactionAggregation.remind.is_(False)).order_by(
                    ReactionAggregation.guild_id)
                result = await session.execute(stmt)
                result = result.fetchall()
                result = [self.return_dataclass(reaction)
                          for reaction in result]

        if len(result) == 0:
            return None
        else:
            return result

    async def get_all_aggregation(self) -> Union[None, List[ReactionParameter]]:
        """すべてのリアクション集計ギルドID順で取得する関数

        Returns:
            Union[None, List[ReactionParameter]]: なければNone、あったらリスト
        """
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = select(ReactionAggregation).order_by(
                    ReactionAggregation.guild_id)
                result = await session.execute(stmt)
                result = result.fetchall()
                result = [self.return_dataclass(reaction)
                          for reaction in result]

        if len(result) == 0:
            return None
        else:
            return result


if __name__ == "__main__":
    reaction_mng = AggregationManager()
    result = asyncio.run(reaction_mng.get_all_not_reminded_aggregation())

    for i in result:
        print(i)

    # asyncio.run(guild_mng.register_setting())

    # asyncio.run(reaction_mng.all_guild_id())
