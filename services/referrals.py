
from database import get_connection


def register_referral(new_user_id, referrer_id):
    """ثبت معرف برای کاربر جدید."""

    if (
        new_user_id is None
        or referrer_id is None
        or new_user_id == referrer_id
    ):
        return False

    with get_connection() as db:
        new_user = db.execute(
            """
            SELECT referred_by
            FROM users
            WHERE telegram_id = ?
            """,
            (new_user_id,)
        ).fetchone()

        referrer = db.execute(
            """
            SELECT telegram_id
            FROM users
            WHERE telegram_id = ?
              AND is_banned = 0
            """,
            (referrer_id,)
        ).fetchone()

        if new_user is None or referrer is None:
            return False

        if new_user["referred_by"] is not None:
            return False

        cursor = db.execute(
            """
            UPDATE users
            SET referred_by = ?
            WHERE telegram_id = ?
              AND referred_by IS NULL
            """,
            (referrer_id, new_user_id)
        )

    return cursor.rowcount == 1


def get_referral_count(user_id):
    """تعداد زیرمجموعه‌های مستقیم."""

    with get_connection() as db:
        result = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM users
            WHERE referred_by = ?
            """,
            (user_id,)
        ).fetchone()

    return result["total"]


def get_referrals(user_id, limit=50):
    """فهرست زیرمجموعه‌های کاربر."""

    try:
        limit = max(1, min(int(limit), 100))
    except (TypeError, ValueError):
        limit = 50

    with get_connection() as db:
        return db.execute(
            """
            SELECT telegram_id, username, first_name, created_at
            FROM users
            WHERE referred_by = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit)
        ).fetchall()


def get_referral_reward():
    """دریافت پاداش معرف از تنظیمات."""

    with get_connection() as db:
        result = db.execute(
            """
            SELECT setting_value
            FROM settings
            WHERE setting_key = 'referral_reward'
            """
        ).fetchone()

    try:
        return max(0, int(result["setting_value"])) if result else 0
    except (ValueError, TypeError):
        return 0


def get_referral_summary(user_id):
    """خلاصه اطلاعات زیرمجموعه‌ها."""

    with get_connection() as db:
        result = db.execute(
            """
            SELECT COUNT(*) AS total_referrals
            FROM users
            WHERE referred_by = ?
            """,
            (user_id,)
        ).fetchone()

    return {
        "total_referrals": result["total_referrals"],
        "reward_per_referral": get_referral_reward()
    }
