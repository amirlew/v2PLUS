
from database import get_connection


def save_message(
    user_id,
    message_text=None,
    message_type="text",
    file_id=None,
    is_from_admin=False
):
    """ذخیره پیام کاربر یا پاسخ مدیر."""

    if user_id is None:
        return None

    try:
        with get_connection() as db:
            cursor = db.execute(
                """
                INSERT INTO support_messages
                (
                    telegram_id,
                    message_text,
                    message_type,
                    file_id,
                    is_from_admin
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    message_text,
                    message_type or "text",
                    file_id,
                    int(bool(is_from_admin))
                )
            )

            return cursor.lastrowid

    except Exception:
        return None


def get_user_messages(user_id, limit=20):
    """دریافت پیام‌های یک کاربر."""

    if user_id is None:
        return []

    try:
        limit = max(1, min(int(limit), 100))
    except (TypeError, ValueError):
        limit = 20

    with get_connection() as db:
        return db.execute(
            """
            SELECT *
            FROM support_messages
            WHERE telegram_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit)
        ).fetchall()


def get_pending_support_messages(limit=30):
    """دریافت پیام‌های کاربران برای بررسی مدیر."""

    try:
        limit = max(1, min(int(limit), 100))
    except (TypeError, ValueError):
        limit = 30

    with get_connection() as db:
        return db.execute(
            """
            SELECT *
            FROM support_messages
            WHERE is_from_admin = 0
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()


def get_support_message(message_id):
    """دریافت یک پیام پشتیبانی."""

    if message_id is None:
        return None

    with get_connection() as db:
        return db.execute(
            """
            SELECT *
            FROM support_messages
            WHERE id = ?
            """,
            (message_id,)
        ).fetchone()
