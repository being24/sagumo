from datetime import datetime

from cogs.utils.remind_schedule import (
    JST,
    UTC,
    calc_next_remind_at,
    reschedule_with_new_hour,
)


def test_calc_next_remind_at_returns_same_day_before_hour():
    got = calc_next_remind_at(datetime(2026, 9, 20, 8, 59, tzinfo=JST), 21)
    assert got == datetime(2026, 9, 20, 21, 0, tzinfo=JST).astimezone(UTC)


def test_calc_next_remind_at_at_exact_hour_snaps_to_next_day():
    """Round1 AR-1の再発防止: ちょうどhour:00は「過ぎている」扱いで翌日にする"""
    got = calc_next_remind_at(datetime(2026, 9, 20, 21, 0, tzinfo=JST), 21)
    assert got == datetime(2026, 9, 21, 21, 0, tzinfo=JST).astimezone(UTC)


def test_calc_next_remind_at_after_hour_snaps_to_next_day():
    got = calc_next_remind_at(datetime(2026, 9, 20, 22, 0, tzinfo=JST), 21)
    assert got == datetime(2026, 9, 21, 21, 0, tzinfo=JST).astimezone(UTC)


def test_reschedule_with_new_hour_keeps_date_on_earlier_time():
    """Round2 AR-5の再発防止: 前倒し変更（21時->20時）で通知日がずれない"""
    current = datetime(2026, 9, 27, 21, 0, tzinfo=JST).astimezone(UTC)
    now = datetime(2026, 9, 20, 10, 0, tzinfo=JST).astimezone(UTC)
    got = reschedule_with_new_hour(current, 20, now)
    assert got == datetime(2026, 9, 27, 20, 0, tzinfo=JST).astimezone(UTC)


def test_reschedule_with_new_hour_pushes_a_week_if_already_past():
    current = datetime(2026, 9, 20, 21, 0, tzinfo=JST).astimezone(UTC)
    now = datetime(2026, 9, 20, 20, 30, tzinfo=JST).astimezone(UTC)
    got = reschedule_with_new_hour(current, 20, now)
    assert got == datetime(2026, 9, 27, 20, 0, tzinfo=JST).astimezone(UTC)
