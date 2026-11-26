
from database import get_connection


def get_user(user_id):
    """دریافت اطلاعات یک کاربر."""

    if user_id is None:
        return None

    with get_connection() as db:
        return db.execute(
            """
            SELECT *
            FROM users
            WHERE telegram_id = ?
            """,
            (user_id,)
        ).fetchone()


def get_all_users(limit=50, offset=0):
    """دریافت فهرست کاربران با صفحه‌بندی."""

    try:
        limit = max(1, min(int(limit), 500))
    except (TypeError, ValueError):
        limit = 50

    try:
        offset = max(0, int(offset))
    except (TypeError, ValueError):
        offset = 0

    with get_connection() as db:
        return db.execute(
            """
            SELECT *
            FROM users
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        ).fetchall()


def set_user_ban(user_id, banned=True):
    """مسدود یا آزاد کردن کاربر."""

    if user_id is None:
        return False

    if banned not in (True, False, 0, 1):
        return False

    with get_connection() as db:
        cursor = db.execute(
            """
            UPDATE users
            SET is_banned = ?
            WHERE telegram_id = ?
            """,
            (int(bool(banned)), user_id)
        )

    return cursor.rowcount == 1


def adjust_wallet(
    user_id,
    amount,
    description="تغییر موجودی توسط مدیر"
):
    """
    افزایش یا کاهش موجودی کیف پول.
    مبلغ مثبت = افزایش
    مبلغ منفی = کاهش
    """

    if user_id is None:
        return False, "شناسه کاربر معتبر نیست."

    if isinstance(amount, bool) or not isinstance(amount, int):
        return False, "مبلغ واردشده معتبر نیست."

    if amount == 0:
        return False, "مبلغ واردشده معتبر نیست."

    with get_connection() as db:
        cursor = db.execute(
            """
            UPDATE users
            SET wallet_balance = wallet_balance + ?
            WHERE telegram_id = ?
              AND wallet_balance + ? >= 0
            """,
            (amount, user_id, amount)
        )

        if cursor.rowcount != 1:
            return False, "کاربر پیدا نشد یا موجودی کافی نیست."

        db.execute(
            """
            INSERT INTO transactions
            (
                telegram_id,
                amount,
                transaction_type,
                description
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                amount,
                "admin_adjustment",
                str(description or "")
            )
        )

        balance = db.execute(
            """
            SELECT wallet_balance
            FROM users
            WHERE telegram_id = ?
            """,
            (user_id,)
        ).fetchone()["wallet_balance"]

    return True, balance


def get_user_count():
    """تعداد کل کاربران."""

    with get_connection() as db:
        result = db.execute(
            "SELECT COUNT(*) AS total FROM users"
        ).fetchone()

    return result["total"]


def get_banned_users():
    """دریافت فهرست کاربران مسدودشده."""

    with get_connection() as db:
        return db.execute(
            """
            SELECT *
            FROM users
            WHERE is_banned = 1
            ORDER BY created_at DESC
            """
        ).fetchall()
