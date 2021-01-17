# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import pathlib

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Column
from sqlalchemy.sql.base import ColumnCollection
from sqlalchemy.sql.sqltypes import BOOLEAN, DATETIME, TIMESTAMP
from sqlalchemy.types import BigInteger, Integer, String, VARCHAR

Base = declarative_base()


class ReactionAggregation(Base):
    __tablename__ = 'reactionaggregation'

    msg_id = Column(BigInteger, primary_key=True) # メッセージID
    guild_id = Column(BigInteger, default=0) # ギルドID
    channel_id = Column(BigInteger, default=0) # チャンネルID
    target_value = Column(Integer, default=0) # 目標値
    sum = Column(Integer, default=0) # 現在の合計値
    matte = Column(BOOLEAN, default=False) # 待ってが付いてるかどうか
    author_id = Column(BigInteger, default=0) # 集めてる人のID
    created_at = Column(DATETIME, default=0) # 集計開始時間
    notified_at = Column(DATETIME, default=0) # 集計完了時間
    remind_at = Column(BOOLEAN, default=False) # リマインドしたかどうか？
    pinged_id = Column(VARCHAR, default='') # メンション先のID

    # メモ：dataclassにで扱うべし


class AggregationManager():
    def __init__(self):
        data_path = pathlib.Path(__file__).parents[1]
        data_path /= '../data'
        data_path = data_path.resolve()
        db_path = data_path
        db_path /= './data.sqlite3'
        self.engine = create_async_engine(
            f'sqlite:///{db_path}', echo=True)

    async def create_table(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(ReactionAggregation.metadata.create_all)

    '''
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
    asyncio.run(reaction_mng.create_table())

    # asyncio.run(guild_mng.register_setting())

    # asyncio.run(reaction_mng.all_guild_id())
