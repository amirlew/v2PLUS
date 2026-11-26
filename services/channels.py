
from datetime import datetime

from database import get_connection


def _is_expired(expires_at):
    """بررسی انقضای تاریخ با پشتیبانی از تاریخ‌های دارای timezone."""
    if not expires_at:
        return False

    try:
        expiration = datetime.fromisoformat(str(expires_at))

        if expiration.tzinfo is not None:
            now = datetime.now(expiration.tzinfo)
        else:
            now = datetime.now()

        return expiration <= now

    except (ValueError, TypeError, OverflowError):
        return True


def add_channel(
    channel_id,
    channel_name=None,
    is_permanent=False,
    expires_at=None
):
    """افزودن کانال اجباری."""
    if channel_id is None:
        return False, "شناسه کانال معتبر نیست."

    channel_id = str(channel_id).strip()

    if not channel_id:
        return False, "شناسه کانال معتبر نیست."

    if expires_at:
        try:
            datetime.fromisoformat(str(expires_at))
        except (ValueError, TypeError):
            return False, "فرمت تاریخ انقضا معتبر نیست."

    if not is_permanent and not expires_at:
        return False, "برای کانال موقت باید تاریخ انقضا مشخص شود."

    try:
        with get_connection() as db:
            cursor = db.execute(
                """
                INSERT INTO required_channels
                (
                    channel_id,
                    channel_name,
                    is_permanent,
                    expires_at,
                    is_active
                )
                VALUES (?, ?, ?, ?, 1)
                """,
                (
                    channel_id,
                    channel_name,
                    int(bool(is_permanent)),
                    str(expires_at) if expires_at else None
                )
            )

            return True, cursor.lastrowid

    except Exception:
        return False, "این کانال قبلاً ثبت شده یا اطلاعات آن نامعتبر است."


def get_active_channels():
    """دریافت کانال‌های فعال و منقضی‌نشده."""
    with get_connection() as db:
        channels = db.execute(
            """
            SELECT *
            FROM required_channels
            WHERE is_active = 1
            ORDER BY id DESC
            """
        ).fetchall()

    result = []

    for channel in channels:
        if channel["is_permanent"]:
            result.append(channel)
            continue

        if not channel["expires_at"]:
            continue

        if not _is_expired(channel["expires_at"]):
            result.append(channel)

    return result


def get_all_channels():
    """دریافت تمام کانال‌ها."""
    with get_connection() as db:
        return db.execute(
            """
            SELECT *
            FROM required_channels
            ORDER BY id DESC
            """
        ).fetchall()


def deactivate_channel(channel_id):
    """غیرفعال کردن کانال."""
    if channel_id is None:
        return False

    with get_connection() as db:
        cursor = db.execute(
            """
            UPDATE required_channels
            SET is_active = 0
            WHERE id = ?
              AND is_active = 1
            """,
            (channel_id,)
        )

    return cursor.rowcount == 1


def delete_channel(channel_id):
    """حذف کانال."""
    if channel_id is None:
        return False

    with get_connection() as db:
        cursor = db.execute(
            """
            DELETE FROM required_channels
            WHERE id = ?
            """,
            (channel_id,)
        )

    return cursor.rowcount == 1
