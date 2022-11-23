import asyncio
import dataclasses
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Union

from dateutil.relativedelta import relativedelta
from sqlalchemy import delete, or_, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Column
from sqlalchemy.types import BOOLEAN, DATETIME, VARCHAR, BigInteger

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
    active: bool
    notified: bool


class InactiveDetectorDB(Base):
    __tablename__ = "inactive"

    user_id = Column(BigInteger, primary_key=True)  # ユーザーID
    last_posted = Column(DATETIME, nullable=False)  # 最終ポスト
    last_react = Column(DATETIME, nullable=False)  # 最終リアクション
    active = Column(BOOLEAN, default=True)  # アクティブか？
    notified = Column(BOOLEAN, default=False)  # 通知済みか


class InactiveManager:
    @staticmethod
    def return_dataclass(db_data) -> InactiveDetector:
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
            active=db_data.active,
            notified=db_data.notified,
        )
        return db_data_raw

    @staticmethod
    def return_DBClass(data: InactiveDetector) -> InactiveDetectorDB:
        """dataclassからDBのデータを返す関数

        Args:
            data (InactiveDetector): データクラス

        Returns:
            InactiveDetectorDB: DBのデータ
        """
        db_data = data
        processed_data = InactiveDetectorDB(
            user_id=db_data.user_id,
            last_posted=db_data.last_posted,
            last_react=db_data.last_react,
            active=db_data.active,
            notified=db_data.notified,
        )

        return processed_data

    async def create_table(self):
        async with engine.begin() as conn:
            await conn.run_sync(InactiveDetectorDB.metadata.create_all)

    async def register_members(self, members: List[int]) -> None:
        """メンバーを登録する関数

        Args:
            members (List[int]): リスト化されたメンバーID

        Returns:
            None
        """
        now = datetime.utcnow()

        for member in members:
            stmt = insert(InactiveDetectorDB).values(
                user_id=member,
                last_posted=now,
                last_react=now,
            )
            do_nothing_stmt = stmt.on_conflict_do_nothing(index_elements=["user_id"])

            async with AsyncSession(engine) as session:
                async with session.begin():
                    await session.execute(do_nothing_stmt)

    async def get_active_members(self) -> Optional[List[int]]:
        """有効なメンバーを返す関数

        Returns:
            Optional[List[int]]: 有効なメンバーID
        """
        stmt = select([InactiveDetectorDB.user_id]).where(InactiveDetectorDB.active)
        async with AsyncSession(engine) as session:
            async with session.begin():
                result = await session.execute(stmt)
                result = result.fetchall()
                result = [member.user_id for member in result]

        if len(result) == 0:
            return None
        else:
            return result

    async def get_inactive_members(self) -> Optional[List[int]]:
        """非アクティブメンバーを返す関数

        Returns:
            Optional[List[int]]: 非アクティブなメンバーID
        """
        stmt = select([InactiveDetectorDB.user_id]).where(InactiveDetectorDB.active == False)

        async with AsyncSession(engine) as session:
            async with session.begin():
                result = await session.execute(stmt)
                result = result.fetchall()
                result = [member.user_id for member in result]

        if len(result) == 0:
            return None
        else:
            return result

    async def get_all_members(self) -> Optional[List[int]]:
        """全メンバーを返す関数

        Returns:
            Optional[List[int]]: 全メンバーID
        """

        stmt = select([InactiveDetectorDB.user_id])
        async with AsyncSession(engine) as session:
            async with session.begin():
                result = await session.execute(stmt)
                result = result.fetchall()
                result = [member.user_id for member in result]

        if len(result) == 0:
            return None
        else:
            return result

    async def check_member(self, member_id: int) -> bool:
        """監視対象であるかを確認する関数

        Args:
            member_id (int): user_id

        Returns:
            bool: 対象であればTrue
        """
        stmt = select([InactiveDetectorDB.user_id]).where(InactiveDetectorDB.user_id == member_id)
        async with AsyncSession(engine) as session:
            async with session.begin():
                result = await session.execute(stmt)
                result = result.fetchone()

        if result is None:
            return False
        else:
            return True

    async def remove_member(self, member_id: int) -> None:
        """メンバーを削除する関数

        Args:
            member_id (int): メンバーID
        """

        stmt = delete(InactiveDetectorDB).where(InactiveDetectorDB.user_id == member_id)
        async with AsyncSession(engine) as session:
            async with session.begin():
                await session.execute(stmt)

    async def update_last_posted(self, member_id: int) -> None:
        """最終投稿時間を更新する関数

        Args:
            member_id (int): メンバーID
        """
        stmt = (
            update(InactiveDetectorDB)
            .where(InactiveDetectorDB.user_id == member_id)
            .values(last_posted=datetime.utcnow())
        )

        async with AsyncSession(engine) as session:
            async with session.begin():
                await session.execute(stmt)

    async def update_last_react(self, member_id: int) -> None:
        """最終リアクション時間を更新する関数

        Args:
            member_id (int): メンバーID
        """
        stmt = (
            update(InactiveDetectorDB)
            .where(InactiveDetectorDB.user_id == member_id)
            .values(last_react=datetime.utcnow())
        )

        async with AsyncSession(engine) as session:
            async with session.begin():
                await session.execute(stmt)

    async def check_period_no_work(self, month: int = 3) -> Optional[List[int]]:
        """一定期間連続で投稿しなかったメンバーを返す関数

        Args:
            month (int, optional): 閾値期間. Defaults to 3.

        Returns:
            Optional[List[int]]: 一定期間連続で投稿しなかったメンバーIDのリスト
        """
        now = datetime.utcnow()
        month_ago = now - relativedelta(months=month)
        stmt = (
            select([InactiveDetectorDB.user_id])
            .where(InactiveDetectorDB.notified == False)
            .filter(or_(InactiveDetectorDB.last_posted < month_ago, InactiveDetectorDB.last_react < month_ago))
        )
        async with AsyncSession(engine) as session:
            async with session.begin():
                result = await session.execute(stmt)
                result = result.fetchall()
                result = [member.user_id for member in result]

        if len(result) == 0:
            return None
        else:
            return result

    async def set_notified(self, member_list: List[int]) -> None:
        """通知済み、非アクティブに設定する関数

        Args:
            member_list (List[int]): 一定期間連続で投稿しなかったメンバーIDのリスト
        """
        for member in member_list:
            stmt = (
                update(InactiveDetectorDB)
                .where(InactiveDetectorDB.user_id == member)
                .values(active=False, notified=True)
            )
            async with AsyncSession(engine) as session:
                async with session.begin():
                    await session.execute(stmt)

    async def set_active(self, member_id: int) -> None:
        """メンバーをアクティブに設定する関数

        Args:
            member_id (int): アクティブにするメンバーID
        """
        now = datetime.utcnow()
        stmt = (
            update(InactiveDetectorDB)
            .where(InactiveDetectorDB.user_id == member_id)
            .values(last_posted=now, last_react=now, active=True, notified=False)
        )
        async with AsyncSession(engine) as session:
            async with session.begin():
                await session.execute(stmt)

    async def set_inactive(self, member_id: int) -> None:
        """メンバーを非アクティブに設定する関数

        Args:
            member_id (int): 非アクティブにするメンバーID
        """
        stmt = (
            update(InactiveDetectorDB)
            .where(InactiveDetectorDB.user_id == member_id)
            .values(active=False, notified=True)
        )
        async with AsyncSession(engine) as session:
            async with session.begin():
                await session.execute(stmt)


if __name__ == "__main__":
    invite_mng = InactiveManager()
    # result = asyncio.run(invite_mng.create_table())

    now = datetime.now()

    # test = InactiveDetector(message_id=124, author_id=123, created_at=now)
    result = asyncio.run(invite_mng.check_period_no_work())
    print(result)

    # for i in result:
    #    print(i)

    # asyncio.run(guild_mng.register_setting())

    # asyncio.run(reaction_mng.all_guild_id())
