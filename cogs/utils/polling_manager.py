# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import dataclasses
from dataclasses import dataclass
from datetime import datetime
from typing import List, Union

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Column
from sqlalchemy.sql.sqltypes import DATETIME
from sqlalchemy.types import VARCHAR, BigInteger

from .db import engine

Base = declarative_base()


@dataclass
class PollingParameter:
    message_id: int
    channel_id: int
    author_id: int
    created_at: datetime = dataclasses.field(
        default_factory=datetime.now, init=False)
    allow_list: list


class PollingObj(Base):
    __tablename__ = 'pollingaggregation'

    message_id = Column(BigInteger, primary_key=True)  # メッセージID
    channel_id = Column(BigInteger, nullable=False)  # チャンネルID
    author_id = Column(BigInteger, nullable=False)  # 集めてる人のID
    created_at = Column(DATETIME, nullable=False)  # 集計開始時間
    allow_list = Column(VARCHAR, default='')  # メンション先のID


class PollingManager():

    @staticmethod
    def return_dataclass(db_data) -> PollingParameter:
        """DBからの情報をデータクラスに変換する関数、もうちょっとなんとかならんか？？？

        Args:
            db_data (sqlalchemyの): DBから取り出したデータ

        Returns:
            PollingParameter: データクラス
        """

        '''
        ping_id_list = []
        guild_id_list_str = guild[0].ping_id.split(',')
        for guild_id_str in guild_id_list_str:
            if guild_id_str != '':
                id = int(guild_id_str)
                ping_id_list.append(id)
        '''
        allow_list = [
            int(id) for id in db_data[0].allow_list.split(',') if id != '']
        db_data_raw = PollingParameter(
            message_id=db_data[0].message_id,
            author_id=db_data[0].author_id,
            channel_id=db_data[0].channel_id,
            allow_list=allow_list)
        return db_data_raw

    async def create_table(self):
        async with engine.begin() as conn:
            await conn.run_sync(PollingObj.metadata.create_all)

    async def register_polling(self, data: PollingParameter) -> None:
        """投票の情報を登録するコマンド

        Args:
            data (PollingParameter): 投票のデータ
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                allow_list = ",".join([str(id) for id in data.allow_list])
                new_aggregation = PollingObj(
                    message_id=data.message_id,
                    author_id=data.author_id,
                    channel_id=data.channel_id,
                    created_at=data.created_at,
                    allow_list=allow_list)

                session.add(new_aggregation)

    async def get_aggregation(self, message_id: int) -> Union[None, PollingParameter]:
        """メッセージIDから集計中の情報を返す関数

        Args:
            message_id (int): 対象のメッセージID

        Returns:
            Union[None, PollingParameter]: あれば情報、なければNone
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(PollingObj).where(
                    PollingObj.message_id == message_id)
                result = await session.execute(stmt)
                result = result.fetchone()
                if result is None:
                    return None
                else:
                    return self.return_dataclass(result)

    async def remove_aggregation(self, message_id: int) -> None:
        """リアクション集計を削除するコマンド

        Args:
            message_id (int): メッセージID
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = delete(PollingObj).where(
                    PollingObj.message_id == message_id)
                await session.execute(stmt)

    async def get_all_aggregation(self) -> Union[None, List[PollingParameter]]:
        """すべてのリアクション集計ギルドID順で取得する関数

        Returns:
            Union[None, List[ReactionParameter]]: なければNone、あったらリスト
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(PollingObj)
                result = await session.execute(stmt)
                result = result.fetchall()
                result = [self.return_dataclass(poll)
                          for poll in result]

        if len(result) == 0:
            return None
        else:
            return result

    async def is_exist(self, message_id: int) -> bool:
        """引数のメッセージIDが待機中かを判定する関数

        Args:
            guild_id (int): サーバーID

        Returns:
            bool: あったらTrue、なかったらFalse
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(PollingObj).where(
                    PollingObj.message_id == message_id)
                result = await session.execute(stmt)
                result = result.fetchone()
                if result is not None:
                    return True
                else:
                    return False


if __name__ == "__main__":
    polling_mng = PollingManager()
    result = asyncio.run(polling_mng.create_table())

    now = datetime.now()

    test = PollingParameter(message_id=124, author_id=123, created_at=now)
    print(asyncio.run(polling_mng.get_aggregation(123)))

    # for i in result:
    #    print(i)

    # asyncio.run(guild_mng.register_setting())

    # asyncio.run(reaction_mng.all_guild_id())
