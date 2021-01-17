# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import pathlib

from sqlalchemy import delete, exc, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Column
from sqlalchemy.types import BigInteger, Integer, String, DateTime

from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = 'inviteuserinfo'

    id = Column(BigInteger, primary_key=True)
    welcome_msg_id = Column(BigInteger)
    # wikidot_id = Column(BigInteger)
    last_got_time = Column(DateTime)


class UserManager():
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
            await conn.run_sync(Base.metadata.create_all)

    async def register_user(self, user_id, welcome_id) -> None:
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            async with session.begin():
                new_user = User(
                    id=user_id,
                    welcome_msg_id=welcome_id,
                    last_got_time=datetime.fromtimestamp(0))
                session.add(new_user)

    async def update_user(self, user_id, welcome_id) -> None:
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            async with session.begin():
                stmt = update(User).where(
                    User.id == user_id).values(
                    welcome_msg_id=welcome_id)
                await session.execute(stmt)

    async def update_got_time(self, user_id) -> None:
        now = datetime.now()
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            async with session.begin():
                stmt = update(User).where(
                    User.id == user_id).values(
                    last_got_time=now)
                await session.execute(stmt)

    async def is_msg_id_exist(self, reaction) -> bool:
        '''
        msg_idが存在するか？
        '''
        user_id = reaction.user_id
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            async with session.begin():
                stmt = select(User.welcome_msg_id).where(User.id == user_id)
                result = await session.execute(stmt)
                result = result.fetchone()
                if result is not None:
                    return True
                else:
                    return False

    '''
    async def is_msg_id_in_DB2(self, user_id, msg_id) -> bool:
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            async with session.begin():
                stmt = select(User.welcome_msg_id).where(User.id == user_id)
                result = await session.execute(stmt)
                result = result.fetchone()
                if result is not None:
                    return True
                else:
                    return False
    '''

    async def is_exist(self, user_id) -> bool:
        '''
        主キーが存在するか？
        '''
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            async with session.begin():
                stmt = select(User).where(User.id == user_id)
                result = await session.execute(stmt)
                result = result.fetchone()
                if result is not None:
                    return True
                else:
                    return False

    async def remove_user(self, id) -> None:
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = delete(User).where(User.id == id)
                await session.execute(stmt)

    async def get_user(self, id):
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            async with session.begin():
                stmt = select(User).where(User.id == id)
                result = await session.execute(stmt)
                result = result.fetchone()

        if result is None:
            return None

        return result[0]


if __name__ == "__main__":
    user_mng = UserManager()
    id = 537461600743981067
    msg_id = 782638396761178172
    # asyncio.run(user_mng.register_user(id=id, welcome_id=msg_id))

    user_id = 537461600743981067
    user_id = 5374616007439810673
    msg_id = 782638396761178172
    asyncio.run(user_mng.is_exist(user_id))
