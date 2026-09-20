import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from cogs.utils import reaction_aggregation_manager as ram

UTC = ZoneInfo("UTC")
JST = ZoneInfo("Asia/Tokyo")


@pytest.fixture
async def test_engine(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    monkeypatch.setattr(ram, "engine", engine)
    yield engine
    await engine.dispose()


async def _create_legacy_schema(engine) -> None:
    """next_remind_atカラムを持たない旧スキーマのテーブルを作る"""
    async with engine.begin() as conn:
        await conn.exec_driver_sql(
            """
            CREATE TABLE reactionaggregation (
                message_id BIGINT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                command_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                target_value INTEGER NOT NULL,
                sum INTEGER,
                matte INTEGER,
                author_id BIGINT NOT NULL,
                created_at DATETIME NOT NULL,
                notified_at DATETIME,
                remind INTEGER,
                ping_id VARCHAR
            )
            """
        )
        await conn.exec_driver_sql(
            "INSERT INTO reactionaggregation "
            "(message_id, guild_id, command_id, channel_id, target_value, sum, matte, "
            "author_id, created_at, notified_at, remind, ping_id) VALUES "
            "(1, 100, 1, 1, 5, 2, 0, 1, '2026-09-01 00:00:00', NULL, 3, ''), "
            "(2, 100, 1, 1, 5, 2, 0, 1, '2026-09-10 00:00:00', NULL, NULL, '')"
        )


@pytest.mark.asyncio
async def test_create_table_backfills_next_remind_at_for_already_reminded_rows(
    test_engine,
):
    """Round2 AR-3の再発防止: remind IS NOT NULLの既存行はバックフィルされ、
    next_remind_atがNULLではなくなる（未送信扱いでの再通知を防ぐ）"""
    await _create_legacy_schema(test_engine)

    mng = ram.AggregationManager()
    await mng.create_table()

    row1 = await mng.get_aggregation(1)
    row2 = await mng.get_aggregation(2)

    assert row1 is not None and row1.next_remind_at is not None
    assert row2 is not None and row2.next_remind_at is None


@pytest.mark.asyncio
async def test_create_table_is_idempotent(test_engine):
    """同じALTER TABLEが2回実行されてduplicate column nameにならないこと"""
    await _create_legacy_schema(test_engine)

    mng = ram.AggregationManager()
    await mng.create_table()
    await mng.create_table()  # 2回目もエラーにならない


@pytest.mark.asyncio
async def test_create_table_concurrent_calls_do_not_conflict(test_engine):
    """Round2 AR-2の再発防止: 複数cogから並行してcreate_tableが呼ばれても
    ALTER TABLEの競合でduplicate column nameエラーにならないこと"""
    await _create_legacy_schema(test_engine)

    mng1 = ram.AggregationManager()
    mng2 = ram.AggregationManager()
    await asyncio.gather(mng1.create_table(), mng2.create_table())


@pytest.mark.asyncio
async def test_set_value_to_next_remind_at(test_engine):
    mng = ram.AggregationManager()
    await mng.create_table()
    await mng.register_aggregation(
        message_id=10,
        command_id=1,
        guild_id=100,
        channel_id=1,
        target_value=5,
        author_id=1,
        created_at=datetime.now(tz=UTC),
        ping_id="",
    )

    target = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)
    await mng.set_value_to_next_remind_at(10, target)

    row = await mng.get_aggregation(10)
    assert row is not None
    assert row.next_remind_at == target


@pytest.mark.asyncio
async def test_get_unfinished_aggregation_by_guild_excludes_completed(test_engine):
    mng = ram.AggregationManager()
    await mng.create_table()
    now = datetime.now(tz=UTC)
    await mng.register_aggregation(
        message_id=20,
        command_id=1,
        guild_id=200,
        channel_id=1,
        target_value=5,
        author_id=1,
        created_at=now,
        ping_id="",
    )
    await mng.register_aggregation(
        message_id=21,
        command_id=1,
        guild_id=200,
        channel_id=1,
        target_value=5,
        author_id=1,
        created_at=now,
        ping_id="",
    )
    await mng.set_value_to_sum(21, 5)  # 達成済み

    result = await mng.get_unfinished_aggregation_by_guild(200)

    assert result is not None
    assert [r.message_id for r in result] == [20]


@pytest.mark.asyncio
async def test_reschedule_unfinished_by_new_hour(test_engine):
    """Round2 R2-R1対応:
    - next_remind_at=None（初回未送信）はoffset変更後もNoneのまま
    - 初回送信済みの行は新しい時刻に更新される
    - 完了済み（sum>=target_value）の行は対象外
    """
    mng = ram.AggregationManager()
    await mng.create_table()
    now = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)

    # 初回未送信
    await mng.register_aggregation(
        message_id=30,
        command_id=1,
        guild_id=300,
        channel_id=1,
        target_value=5,
        author_id=1,
        created_at=now,
        ping_id="",
    )
    # 初回送信済み（次回21時予定）
    await mng.register_aggregation(
        message_id=31,
        command_id=1,
        guild_id=300,
        channel_id=1,
        target_value=5,
        author_id=1,
        created_at=now,
        ping_id="",
    )
    next_remind_at_jst_21 = datetime(2026, 9, 27, 21, 0, tzinfo=JST).astimezone(UTC)
    await mng.set_value_to_next_remind_at(31, next_remind_at_jst_21)
    # 完了済み
    await mng.register_aggregation(
        message_id=32,
        command_id=1,
        guild_id=300,
        channel_id=1,
        target_value=5,
        author_id=1,
        created_at=now,
        ping_id="",
    )
    await mng.set_value_to_sum(32, 5)
    await mng.set_value_to_next_remind_at(32, next_remind_at_jst_21)

    await mng.reschedule_unfinished_by_new_hour(300, 20, now)

    row30 = await mng.get_aggregation(30)
    row31 = await mng.get_aggregation(31)
    row32 = await mng.get_aggregation(32)

    assert row30 is not None and row30.next_remind_at is None
    assert row31 is not None
    assert row31.next_remind_at == datetime(2026, 9, 27, 20, 0, tzinfo=JST).astimezone(
        UTC
    )
    assert row32 is not None
    assert row32.next_remind_at == next_remind_at_jst_21  # 完了済みは対象外で不変
