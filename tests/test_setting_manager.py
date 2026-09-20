import asyncio

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from cogs.utils import setting_manager as sm


@pytest.fixture
async def test_engine(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    monkeypatch.setattr(sm, "engine", engine)
    yield engine
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_table_concurrent_calls_do_not_conflict(test_engine):
    """Round2 AR-2の再発防止: 複数cogから並行してcreate_tableが呼ばれても
    ALTER TABLEの競合でduplicate column nameエラーにならないこと"""
    mng1 = sm.SettingManager()
    mng2 = sm.SettingManager()
    await asyncio.gather(mng1.create_table(), mng2.create_table())


@pytest.mark.asyncio
async def test_get_remind_hour_offset_defaults_to_zero_for_unregistered_guild(
    test_engine,
):
    mng = sm.SettingManager()
    await mng.create_table()

    offset = await mng.get_remind_hour_offset(999)

    assert offset == 0


@pytest.mark.asyncio
async def test_set_and_get_remind_hour_offset(test_engine):
    mng = sm.SettingManager()
    await mng.create_table()
    await mng.register_guild(guild_id=100, bot_manager_id=1, bot_user_id=2)

    await mng.set_remind_hour_offset(100, -1)

    assert await mng.get_remind_hour_offset(100) == -1


@pytest.mark.asyncio
async def test_set_remind_hour_offset_rejects_out_of_range_value(test_engine):
    mng = sm.SettingManager()
    await mng.create_table()
    await mng.register_guild(guild_id=100, bot_manager_id=1, bot_user_id=2)

    with pytest.raises(ValueError):
        await mng.set_remind_hour_offset(100, 2)
