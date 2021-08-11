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
from sqlalchemy.sql.sqltypes import BOOLEAN, DATETIME
from sqlalchemy.types import VARCHAR, BigInteger

try:
    from .db import engine
except BaseException:
    import sys
    sys.path.append("../utils")
    from db import engine


Base = declarative_base()


@dataclass
class InactiveDetector:
    user_id: int
    last_posted: datetime
    last_react: datetime
    notified: bool


class InactiveDetectorDB(Base):
    __tablename__ = 'inactive'

    user_id = Column(BigInteger, primary_key=True)  # ユーザーID
    last_posted = Column(DATETIME, nullable=False)  # 最終ポスト
    last_react = Column(DATETIME, nullable=False)  # 最終リアクション
    notified = Column(BOOLEAN, default=False)  # 通知済みか


class InactiveManager():
    @staticmethod
    def return_dataclass(db_data: InactiveDetectorDB) -> InactiveDetector:
        """DBからのデータをdataclassに変換する関数

        Args:
            db_data (InactiveDetectorDB): DBのデータ

        Returns:
            InactiveDetector: データクラス
        """

        db_data_raw = InactiveDetector(
            user_id=db_data.user_id,
            last_posted=db_data.last_posted,
            last_react=db_data.last_react,
            notified=db_data.notified)
        return db_data_raw

    async def create_table(self):
        async with engine.begin() as conn:
            await conn.run_sync(InactiveDetectorDB.metadata.create_all)


if __name__ == "__main__":
    polling_mng = InactiveManager()
    result = asyncio.run(polling_mng.create_table())

    now = datetime.now()

    # test = InactiveDetector(message_id=124, author_id=123, created_at=now)
    print(asyncio.run(polling_mng.get_aggregation(814348307827523585)))

    # for i in result:
    #    print(i)

    # asyncio.run(guild_mng.register_setting())

    # asyncio.run(reaction_mng.all_guild_id())
