
from datetime import datetime

from database import get_connection


def _valid_expiration(value):
    if not value:
        return True

    try:
        expiration = datetime.fromisoformat(str(value))
        now = (
            datetime.now(expiration.tzinfo)
            if expiration.tzinfo
            else datetime.now()
        )
        return expiration > now
    except (ValueError, TypeError, OverflowError):
        return False


def create_discount(
    code,
    discount_type,
    discount_value,
    max_uses=None,
    expires_at=None
):
    """ساخت کد تخفیف."""

    code = str(code or "").strip().upper()

    if not code:
        return False, "کد تخفیف نمی‌تواند خالی باشد."

    if discount_type not in ("percent", "fixed"):
        return False, "نوع تخفیف معتبر نیست."

    if isinstance(discount_value, bool):
        return False, "مقدار تخفیف معتبر نیست."

    try:
        discount_value = int(discount_value)
    except (TypeError, ValueError):
        return False, "مقدار تخفیف معتبر نیست."

    if discount_value <= 0:
        return False, "مقدار تخفیف باید مثبت باشد."

    if discount_type == "percent" and discount_value > 100:
        return False, "درصد تخفیف نمی‌تواند بیشتر از ۱۰۰ باشد."

    if max_uses is not None:
        try:
            max_uses = int(max_uses)
        except (TypeError, ValueError):
            return False, "تعداد استفاده معتبر نیست."

        if max_uses <= 0:
            return False, "تعداد استفاده باید مثبت باشد."

    if expires_at and not _valid_expiration(expires_at):
        return False, "تاریخ انقضا معتبر نیست یا گذشته است."

    try:
        with get_connection() as db:
            cursor = db.execute(
                """
                INSERT INTO discount_codes
                (
                    code,
                    discount_type,
                    discount_value,
                    max_uses,
                    expires_at,
                    is_active
                )
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (
                    code,
                    discount_type,
                    discount_value,
                    max_uses,
                    expires_at
                )
            )

            return True, cursor.lastrowid

    except Exception:
        return False, "این کد قبلاً ثبت شده یا اطلاعات آن نامعتبر است."


def get_discount(code):
    """دریافت اطلاعات کد تخفیف."""

    if not code:
        return None

    with get_connection() as db:
        return db.execute(
            """
            SELECT *
            FROM discount_codes
            WHERE code = ?
            """,
            (str(code).strip().upper(),)
        ).fetchone()


def validate_discount(code, user_id):
    """بررسی اعتبار کد برای یک کاربر."""

    if user_id is None:
        return False, "شناسه کاربر معتبر نیست."

    discount = get_discount(code)

    if discount is None:
        return False, "کد تخفیف پیدا نشد."

    if not discount["is_active"]:
        return False, "این کد تخفیف غیرفعال است."

    if discount["expires_at"] and not _valid_expiration(
        discount["expires_at"]
    ):
        return False, "مهلت استفاده از این کد تمام شده است."

    with get_connection() as db:
        used = db.execute(
            """
            SELECT 1
            FROM discount_usages
            WHERE discount_id = ?
              AND telegram_id = ?
            LIMIT 1
            """,
            (discount["id"], user_id)
        ).fetchone()

        if used:
            return False, "شما قبلاً از این کد استفاده کرده‌اید."

        if discount["max_uses"] is not None:
            count = db.execute(
                """
                SELECT COUNT(*) AS total
                FROM discount_usages
                WHERE discount_id = ?
                """,
                (discount["id"],)
            ).fetchone()["total"]

            if count >= discount["max_uses"]:
                return False, "ظرفیت استفاده از این کد تمام شده است."

    return True, discount


def calculate_discount(price, discount):
    """محاسبه مقدار تخفیف."""

    try:
        price = int(price)
    except (TypeError, ValueError):
        return 0

    if price <= 0 or discount is None:
        return 0

    if discount["discount_type"] == "percent":
        amount = price * discount["discount_value"] // 100
    elif discount["discount_type"] == "fixed":
        amount = discount["discount_value"]
    else:
        return 0

    return min(price, max(0, amount))


def record_discount_usage(discount_id, user_id, order_id=None):
    """ثبت استفاده از کد تخفیف."""

    if discount_id is None or user_id is None:
        return False

    try:
        with get_connection() as db:
            db.execute("BEGIN IMMEDIATE")

            discount = db.execute(
                """
                SELECT *
                FROM discount_codes
                WHERE id = ?
                  AND is_active = 1
                """,
                (discount_id,)
            ).fetchone()

            if discount is None:
                return False

            if discount["expires_at"] and not _valid_expiration(
                discount["expires_at"]
            ):
                return False

            used = db.execute(
                """
                SELECT 1
                FROM discount_usages
                WHERE discount_id = ?
                  AND telegram_id = ?
                """,
                (discount_id, user_id)
            ).fetchone()

            if used:
                return False

            if discount["max_uses"] is not None:
                count = db.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM discount_usages
                    WHERE discount_id = ?
                    """,
                    (discount_id,)
                ).fetchone()["total"]

                if count >= discount["max_uses"]:
                    return False

            db.execute(
                """
                INSERT INTO discount_usages
                (discount_id, telegram_id, order_id)
                VALUES (?, ?, ?)
                """,
                (discount_id, user_id, order_id)
            )

        return True

    except Exception:
        return False


def deactivate_discount(discount_id):
    """غیرفعال کردن کد تخفیف."""

    if discount_id is None:
        return False

    with get_connection() as db:
        cursor = db.execute(
            """
            UPDATE discount_codes
            SET is_active = 0
            WHERE id = ?
              AND is_active = 1
            """,
            (discount_id,)
        )

    return cursor.rowcount == 1
