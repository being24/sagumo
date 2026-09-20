from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
UTC = ZoneInfo("UTC")


def calc_next_remind_at(base: datetime, hour: int) -> datetime:
    """baseをJSTに変換し、直近のhour:00を返す（baseがhour:00以降なら翌日）。戻り値はUTC-aware。"""
    base_jst = base.astimezone(JST)
    candidate = base_jst.replace(hour=hour, minute=0, second=0, microsecond=0)
    if candidate <= base_jst:
        candidate += timedelta(days=1)
    return candidate.astimezone(UTC)


def reschedule_with_new_hour(
    current_next_remind_at: datetime, new_hour: int, now: datetime
) -> datetime:
    """current_next_remind_atのJST日付を維持し、時刻のみnew_hourへ置き換える。

    置き換え後の時刻がnowを過ぎていれば7日後にする（設定変更直後に即時送信されるのを防ぐ）。
    """
    current_jst = current_next_remind_at.astimezone(JST)
    candidate = current_jst.replace(hour=new_hour, minute=0, second=0, microsecond=0)
    candidate_utc = candidate.astimezone(UTC)
    if candidate_utc <= now:
        candidate_utc += timedelta(days=7)
    return candidate_utc
