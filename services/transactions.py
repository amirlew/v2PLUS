
from database import get_connection


def _normalize_limit(limit, default=10):
    try:
        return max(1, min(int(limit), 500))
    except (TypeError, ValueError):
        return default


def add_transaction(user_id, amount, transaction_type, description=""):
    """ثبت تراکنش کاربر."""

    if user_id is None or not transaction_type:
        return False

    if isinstance(amount, bool) or not isinstance(amount, int):
        return False

    if amount == 0:
        return False

    with get_connection() as db:
        user = db.execute(
            """
            SELECT telegram_id
            FROM users
            WHERE telegram_id = ?
            """,
            (user_id,)
        ).fetchone()

        if user is None:
            return False

        db.execute(
            """
            INSERT INTO transactions
            (telegram_id, amount, transaction_type, description)
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                amount,
                str(transaction_type),
                str(description or "")
            )
        )

    return True


def get_user_transactions(user_id, limit=10):
    """دریافت تراکنش‌های یک کاربر."""

    if user_id is None:
        return []

    limit = _normalize_limit(limit)

    with get_connection() as db:
        return db.execute(
            """
            SELECT *
            FROM transactions
            WHERE telegram_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit)
        ).fetchall()


def get_all_transactions(limit=50):
    """دریافت تراکنش‌های همه کاربران."""

    limit = _normalize_limit(limit, 50)

    with get_connection() as db:
        return db.execute(
            """
            SELECT *
            FROM transactions
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()


def get_transaction_summary():
    """خلاصه تراکنش‌های مالی تومانی."""

    with get_connection() as db:
        return db.execute(
            """
            SELECT
                COUNT(*) AS total_transactions,
                COALESCE(
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END),
                    0
                ) AS total_income,
                COALESCE(
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END),
                    0
                ) AS total_expenses
            FROM transactions
            """
        ).fetchone()
