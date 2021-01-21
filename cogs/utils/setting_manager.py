# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import pathlib
from dataclasses import dataclass
from datetime import datetime
from typing import Union

from sqlalchemy import delete, exc, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Column
from sqlalchemy.types import (VARCHAR, BigInteger, Boolean, DateTime, Integer,
                              String)

Base = declarative_base()


@dataclass
class GuildSetting:
    guild_id: int
    bot_manager_id: int
    bot_user_id: int


class GuildSettingDB(Base):
    __tablename__ = 'setting'

    guild_id = Column(BigInteger, primary_key=True)  # サーバーID
    bot_manager_id = Column(BigInteger, default=0)  # ボット管理者のロールID
    bot_user_id = Column(BigInteger, default=0)  # ボット使用者のロールID

    # メモ：dataclassにで扱うべし


class SettingManager():
    def __init__(self):
        data_path = pathlib.Path(__file__).parents[1]
        data_path /= '../data'
        data_path = data_path.resolve()
        db_path = data_path
        db_path /= './data.sqlite3'
        self.engine = create_async_engine(
            f'sqlite:///{db_path}', echo=True)

    async def create_table(self) -> None:
        """テーブルを作成する関数
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            try:
                await self._init_setting()
            except BaseException:
                pass

    async def _init_setting(self) -> None:
        async with AsyncSession(self.engine, expire_on_commit=True) as session:
            async with session.begin():
                new_setting = GuildSettingDB(index=True)
                session.add(new_setting)

    async def register_guild(self, guild_id: int, bot_manager_id: int, bot_user_id: int) -> None:
        """ギルドの設定を登録する関数

        Args:
            guild_id (int): サーバーID
            bot_manager_id (int): BOT管理者役職のID
            bot_user_id (int): BOT使用者役職のID
        """
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                new_guild = GuildSettingDB(
                    guild_id=guild_id,
                    bot_manager_id=bot_manager_id,
                    bot_user_id=bot_user_id)

                session.add(new_guild)

    async def get_guild(self, guild_id: int) -> Union[GuildSetting, None]:
        """ギルドの情報をGuildSettingで返す関数

        Args:
            guild_id (int): サーバーID

        Returns:
            GuildSetting: サーバの設定のデータクラス
        """
        async with AsyncSession(self.engine, expire_on_commit=True) as session:
            async with session.begin():
                stmt = select(GuildSettingDB).where(
                    GuildSettingDB.guild_id == guild_id)
                result = await session.execute(stmt)
                result = result.fetchone()

                if result is None:
                    return None

                guildsetting = GuildSetting(
                    result[0].guild_id,
                    result[0].bot_manager_id,
                    result[0].bot_user_id)

        return guildsetting

    '''
    async def is_alert(self):
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            async with session.begin():
                stmt = select(Setting.invitealert)
                result = await session.execute(stmt)
                result = result.fetchone()[0]

        return result

    async def get_setting(self):
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            async with session.begin():
                stmt = select(Setting)
                result = await session.execute(stmt)
                result = result.fetchone()

        return result[0]

    async def set_ageingtime(self, hours: int):
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(Setting).values(ageingtime=hours)
                await session.execute(stmt)

    async def set_cooltile(self, hours: int):
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(Setting).values(cooltile=hours)
                await session.execute(stmt)

    async def set_alert(self, tf: bool):
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(Setting).values(invitealert=tf)
                await session.execute(stmt)

    async def set_maxemoji(self, num: int):
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(Setting).values(limit=num)
                await session.execute(stmt)

    async def set_ban_words(self, words: list):
        words_list = ','.join(map(str, words))
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(Setting).values(ban_words=words_list)
                await session.execute(stmt)

    async def set_server_list(self, servers: list):
        server_list = ','.join(map(str, servers))
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(Setting).values(watchingserver=server_list)
                await session.execute(stmt)

    async def set_banned_id(self, banned_id: list):
        banned_id_list = ','.join(map(str, banned_id))
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(Setting).values(bannedid=banned_id_list)
                await session.execute(stmt)

    async def all_on(self):
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(Setting).values(
                    inviteurl=True,
                    ngword=True,
                    everyone=True,
                    policelamp=True,
                    invitealert=True)
                await session.execute(stmt)

    async def all_off(self):
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(Setting).values(
                    inviteurl=False,
                    ngword=False,
                    everyone=False,
                    policelamp=False,
                    invitealert=False)
                await session.execute(stmt)

    async def set_inviteurl(self, tf: bool):
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(Setting).values(inviteurl=tf)
                await session.execute(stmt)

    async def set_ngword(self, tf: bool):
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(Setting).values(ngword=tf)
                await session.execute(stmt)

    async def set_everyone(self, tf: bool):
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(Setting).values(everyone=tf)
                await session.execute(stmt)

    async def set_policelamp(self, tf: bool):
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = update(Setting).values(policelamp=tf)
                await session.execute(stmt)
    '''


if __name__ == "__main__":
    setting_mng = SettingManager()
    asyncio.run(setting_mng.create_table())

    # asyncio.run(setting_mng.register_setting())

    result = asyncio.run(setting_mng.get_guild(1))
    print((result))
