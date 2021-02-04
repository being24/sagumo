# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import pathlib
from dataclasses import dataclass
from datetime import datetime
from typing import Union

from sqlalchemy import delete, exc, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Column
from sqlalchemy.sql.base import ColumnCollection
from sqlalchemy.sql.elements import Null
from sqlalchemy.sql.sqltypes import BOOLEAN, DATETIME, TIMESTAMP
from sqlalchemy.types import VARCHAR, BigInteger, Integer, String

Base = declarative_base()


@dataclass
class ReactionParameter:
    msg_id: int
    guild_id: int
    channel_id: int
    target_value: int
    sum: int
    matte: bool
    author_id: int
    created_at: datetime
    notified_at: datetime
    remind: bool
    ping_id: list


class ReactionAggregation(Base):
    __tablename__ = 'reactionaggregation'

    msg_id = Column(BigInteger, primary_key=True)  # メッセージID
    guild_id = Column(BigInteger, nullable=False)  # ギルドID
    channel_id = Column(BigInteger, nullable=False)  # チャンネルID
    target_value = Column(Integer, nullable=False)  # 目標値
    sum = Column(Integer, default=0)  # 現在の合計値
    matte = Column(BOOLEAN, default=False)  # 待ってが付いてるかどうか
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
        ping_id_list = [
            int(id) for id in db_data[0].ping_id.split(',') if id != '']
        db_data_raw = ReactionParameter(
            msg_id=db_data[0].msg_id,
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

    async def register_aggregation(self, msg_id: int, guild_id: int, channel_id: int, target_value: int, author_id: int, created_at: datetime, ping_id: str) -> None:
        """リアクション集計のパラメータを登録する関数

        Args:
            msg_id (int): メッセージID
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
                    msg_id=msg_id,
                    guild_id=guild_id,
                    channel_id=channel_id,
                    target_value=target_value,
                    author_id=author_id,
                    created_at=created_at,
                    ping_id=ping_id)

                session.add(new_aggregation)

    async def get_guild_list(self, guild_id: int) -> Union[list, None]:
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
                    '''
                    ping_id_list = []
                    guild_id_list_str = guild[0].ping_id.split(',')
                    for guild_id_str in guild_id_list_str:
                        if guild_id_str != '':
                            id = int(guild_id_str)
                            ping_id_list.append(id)
                    '''
                    guild_raw = self.return_dataclass(guild)
                    guild_list.append(guild_raw)

        if len(guild_list) == 0:
            return None
        else:
            return guild_list

    async def is_exist(self, msg_id: int) -> bool:
        """引数のメッセージIDが集計中かを判定する関数

        Args:
            guild_id (int): サーバーID

        Returns:
            bool: あったらTrue、なかったらFalse
        """
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = select(ReactionAggregation).where(
                    ReactionAggregation.msg_id == msg_id)
                result = await session.execute(stmt)
                result = result.fetchone()
                if result is not None:
                    return True
                else:
                    return False

    async def remove_aggregation(self, msg_id: int) -> None:
        """リアクション集計を削除するコマンド

        Args:
            msg_id (int): メッセージID
        """
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = delete(ReactionAggregation).where(
                    ReactionAggregation.msg_id == msg_id)
                await session.execute(stmt)

    async def get_aggregation(self, msg_id: int) -> Union[None, ReactionParameter]:
        """メッセージIDから集計中の情報を返す関数

        Args:
            msg_id (int): 対象のメッセージID

        Returns:
            Union[None, ReactionParameter]: あれば情報、なければNone
        """
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = select(ReactionAggregation).where(
                    ReactionAggregation.msg_id == msg_id)
                result = await session.execute(stmt)
                result = result.fetchone()
                if result is None:
                    return None
                else:
                    return self.return_dataclass(result)

    async def set_value_to_sum(self, msg_id: int, val: int) -> None:
        """sumカラムに値を代入する関数

        Args:
            msg_id (int): メッセージID
            val (int): 値
        """
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(ReactionAggregation).where(
                    ReactionAggregation.msg_id == msg_id).values(sum=val)
                await session.execute(stmt)

    async def set_value_to_matte(self, msg_id: int, tf: bool) -> None:
        """matteカラムに値を代入する関数

        Args:
            msg_id (int): メッセージID
            tf (bool): 値
        """
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(ReactionAggregation).where(
                    ReactionAggregation.msg_id == msg_id).values(matte=tf)
                await session.execute(stmt)

    '''
    async def get_guild(self, guild_id: int) -> Union[ReactionAggregation, None]:
        """ギルドの情報をGuildSettingで返す関数

        Args:
            guild_id (int): サーバーID

        Returns:
            GuildSetting: サーバの設定のデータクラス
        """
        async with AsyncSession(self.engine, expire_on_commit=True) as session:
            async with session.begin():
                stmt = select(ReactionAggregation).where(
                    ReactionAggregation.guild_id == guild_id)
                result = await session.execute(stmt)
                result = result.fetchone()

                if result is None:
                    return None

                guildsetting = ReactionParameter(
                    result[0].guild_id,
                    result[0].bot_manager_id,
                    result[0].bot_user_id)

        return guildsetting


    async def register_guild(self, id, invite_channel, anti_spam, statusmessage_id, emoji_id):
        '''
    # サーバーをDBに追加するコマンド（新規登録）
    '''
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            async with session.begin():
                new_guild = Guild(
                    id=id,
                    invite_channel=invite_channel,
                    anti_spam=anti_spam,
                    statusmessage_id=statusmessage_id,
                    emoji_id=emoji_id)

                session.add(new_guild)

    async def update_guild(self, id, invite_channel, anti_spam, statusmessage_id, emoji_id):
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            async with session.begin():
                stmt = select(Guild).where(Guild.id == id)
                result = await session.execute(stmt)
                result = result.fetchone()[0]
                result.invite_channel = invite_channel
                result.anti_spam = anti_spam
                result.statusmessage_id = statusmessage_id
                result.emoji_id = emoji_id

    async def remove_guild(self, id):
        '''
    # 全ギルドのオブジェクトを返す
    '''
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = delete(Guild).where(Guild.id == id)
                await session.execute(stmt)

    async def get_guild(self, id):
        '''
    # ギルドオブジェクトを返す
    '''
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            async with session.begin():
                stmt = select(Guild).where(Guild.id == id)
                result = await session.execute(stmt)
                result = result.fetchone()

        if result is None:
            return None

        return result[0]

    async def all_guilds(self):
        '''
    # 全ギルドのオブジェクトを返す
    '''
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            async with session.begin():
                stmt = select(Guild)
                guilds = await session.execute(stmt)
                guilds = [guild[0] for guild in guilds.all()]

        return guilds

    def is_exist(self) -> bool:
        '''
    # 主キーが存在するか？
    '''
        with self.sc_factory.create() as session:
            guild = session.query(Guild).filter(Guild.id == id).first()
            if guild is not None:
                return True
            else:
                return False

    async def all_guild_id(self) -> list:
        '''
    # ギルドIDのリストを返す
    '''
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            async with session.begin():
                stmt = select(Guild)
                guilds = await session.execute(stmt)
                guild_ids = [guild[0].id for guild in guilds.all()]

        return guild_ids
        '''


if __name__ == "__main__":
    reaction_mng = AggregationManager()
    result = asyncio.run(reaction_mng.set_value_to_sum(806872577574043721, 9))

    print(result)

    # asyncio.run(guild_mng.register_setting())

    # asyncio.run(reaction_mng.all_guild_id())
