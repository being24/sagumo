from dataclasses import dataclass

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Column
from sqlalchemy.sql.sqltypes import BOOLEAN
from sqlalchemy.types import BigInteger

try:
    from .db import engine
except BaseException:
    import sys

    sys.path.append("../utils")
    from db import engine

Base = declarative_base()


@dataclass
class DMNotificationRoleParameter:
    guild_id: int
    role_id: int
    enable_dm: bool


class DMNotificationRole(Base):
    __tablename__ = "dm_notification_roles"

    guild_id = Column(BigInteger, primary_key=True, nullable=False)  # ギルドID
    role_id = Column(BigInteger, primary_key=True, nullable=False)  # ロールID
    enable_dm = Column(BOOLEAN, default=False)  # DM送信フラグ


class DMNotificationRoleManager:
    async def create_table(self):
        async with engine.begin() as conn:
            await conn.run_sync(DMNotificationRole.metadata.create_all)

    async def register_dm_notification_role(
        self, guild_id: int, role_id: int, enable_dm: bool = False
    ) -> None:
        """DM通知対象ロールを登録する関数

        Args:
            guild_id (int): ギルドID
            role_id (int): ロールID
            enable_dm (bool): DM送信フラグ. Defaults to False.
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                new_role = DMNotificationRole(
                    guild_id=guild_id,
                    role_id=role_id,
                    enable_dm=enable_dm,
                )
                session.add(new_role)

    async def get_dm_notification_roles(
        self, guild_id: int
    ) -> list[DMNotificationRoleParameter] | None:
        """ギルドのDM通知対象ロール一覧を取得する関数

        Args:
            guild_id (int): ギルドID

        Returns:
            list[DMNotificationRoleParameter] | None: ロール一覧、なければNone
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(DMNotificationRole).where(
                    DMNotificationRole.guild_id == guild_id
                )
                result = await session.execute(stmt)
                result = result.fetchall()

                if not result:
                    return None

                return [
                    DMNotificationRoleParameter(
                        guild_id=row[0].guild_id,
                        role_id=row[0].role_id,
                        enable_dm=row[0].enable_dm,
                    )
                    for row in result
                ]

    async def update_dm_notification_role(
        self, guild_id: int, role_id: int, enable_dm: bool
    ) -> None:
        """DM通知ロール設定を更新する関数

        Args:
            guild_id (int): ギルドID
            role_id (int): ロールID
            enable_dm (bool): DM送信フラグ
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = (
                    update(DMNotificationRole)
                    .where(
                        (DMNotificationRole.guild_id == guild_id)
                        & (DMNotificationRole.role_id == role_id)
                    )
                    .values(enable_dm=enable_dm)
                )
                await session.execute(stmt)

    async def delete_dm_notification_role(self, guild_id: int, role_id: int) -> None:
        """DM通知ロール設定を削除する関数

        Args:
            guild_id (int): ギルドID
            role_id (int): ロールID
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = delete(DMNotificationRole).where(
                    (DMNotificationRole.guild_id == guild_id)
                    & (DMNotificationRole.role_id == role_id)
                )
                await session.execute(stmt)

    async def get_enabled_dm_notification_roles(
        self, guild_id: int
    ) -> list[int] | None:
        """ギルドのDM送信有効なロールIDリストを取得する関数

        Args:
            guild_id (int): ギルドID

        Returns:
            list[int] | None: 有効なロールIDリスト、なければNone
        """
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(DMNotificationRole).where(
                    (DMNotificationRole.guild_id == guild_id)
                    & (DMNotificationRole.enable_dm.is_(True))
                )
                result = await session.execute(stmt)
                result = result.fetchall()

                if not result:
                    return None

                return [row[0].role_id for row in result]
