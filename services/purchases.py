from datetime import datetime, timedelta, timezone

from database import get_connection
from services.payments import (
    create_stars_payload,
    is_valid_stars_payment,
)


def get_user_orders(user_id, limit=10):
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 10

    limit = max(1, min(limit, 50))

    with get_connection() as db:
        return db.execute("""
            SELECT *
            FROM orders
            WHERE telegram_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (user_id, limit)).fetchall()


def create_stars_order(user_id, product_id, payment):
    """
    ثبت سفارش دیجیتال پس از پرداخت موفق Telegram Stars.

    ورودی سوم باید شیء successful_payment تلگرام باشد.

    خروجی موفق:
    (True, message, config_text)

    خروجی ناموفق:
    (False, message, None)
    """

    if payment is None:
        return False, "اطلاعات پرداخت دریافت نشد.", None

    with get_connection() as db:
        db.execute("BEGIN IMMEDIATE")

        product = db.execute("""
            SELECT *
            FROM products
            WHERE id = ?
              AND is_active = 1
        """, (product_id,)).fetchone()

        if not product:
            return False, "محصول پیدا نشد یا غیرفعال است.", None

        if product["product_type"] != "digital":
            return False, "این محصول برای خرید استارزی نیست.", None

        stars_setting = db.execute("""
            SELECT setting_value
            FROM settings
            WHERE setting_key = 'stars_payment_enabled'
        """).fetchone()

        if not stars_setting or stars_setting["setting_value"] != "1":
            return False, "پرداخت با Stars در حال حاضر غیرفعال است.", None

        stars_price = product["stars_price"]

        if (
            not isinstance(stars_price, int)
            or isinstance(stars_price, bool)
            or stars_price <= 0
        ):
            return False, "قیمت استارزی این محصول تنظیم نشده است.", None

        expected_payload = create_stars_payload(
            user_id,
            product_id
        )

        if not is_valid_stars_payment(
            payment,
            expected_payload=expected_payload,
            expected_amount=stars_price
        ):
            return False, "اطلاعات پرداخت Stars معتبر نیست.", None

        charge_id = payment.telegram_payment_charge_id

        duplicate = db.execute("""
            SELECT id
            FROM orders
            WHERE payment_charge_id = ?
        """, (charge_id,)).fetchone()

        if duplicate:
            return False, "این پرداخت قبلاً ثبت شده است.", None

        user = db.execute("""
            SELECT telegram_id
            FROM users
            WHERE telegram_id = ?
              AND is_banned = 0
        """, (user_id,)).fetchone()

        if not user:
            return False, "حساب کاربری پیدا نشد یا مسدود است.", None

        config = db.execute("""
            SELECT id, config_text
            FROM config_inventory
            WHERE product_id = ?
              AND status = 'available'
            ORDER BY id ASC
            LIMIT 1
        """, (product_id,)).fetchone()

        if not config:
            return False, "متأسفانه موجودی این محصول تمام شده است.", None

        validity = db.execute("""
            SELECT setting_value
            FROM settings
            WHERE setting_key = 'config_validity_days'
        """).fetchone()

        try:
            days = int(validity["setting_value"]) if validity else 30
        except (TypeError, ValueError):
            days = 30

        if days <= 0:
            days = 30

        expires_at = (
            datetime.now(timezone.utc) + timedelta(days=days)
        ).isoformat()

        order_cursor = db.execute("""
            INSERT INTO orders (
                telegram_id,
                product_id,
                volume_gb,
                price,
                status,
                expires_at,
                payment_method,
                payment_charge_id
            )
            VALUES (?, ?, ?, ?, 'completed', ?, 'stars', ?)
        """, (
            user_id,
            product_id,
            product["volume_gb"],
            product["price"],
            expires_at,
            charge_id
        ))

        order_id = order_cursor.lastrowid

        inventory_cursor = db.execute("""
            UPDATE config_inventory
            SET status = 'sold',
                order_id = ?,
                sold_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND status = 'available'
        """, (order_id, config["id"]))

        if inventory_cursor.rowcount != 1:
            raise RuntimeError(
                "Config inventory changed during purchase."
            )

        remaining = db.execute("""
            SELECT COUNT(*)
            FROM config_inventory
            WHERE product_id = ?
              AND status = 'available'
        """, (product_id,)).fetchone()[0]

        db.execute("""
            UPDATE products
            SET stock = ?
            WHERE id = ?
        """, (remaining, product_id))

        db.execute("""
            INSERT INTO transactions (
                telegram_id,
                amount,
                transaction_type,
                description
            )
            VALUES (?, 0, 'stars_purchase', ?)
        """, (
            user_id,
            (
                f"خرید با {stars_price} استارز "
                f"- محصول {product_id} "
                f"- سفارش {order_id}"
            )
        ))

        return (
            True,
            f"خرید با موفقیت ثبت شد. شماره سفارش: {order_id}",
            config["config_text"]
        )


def create_order(user_id, product_id):
    """
    خرید محصول فیزیکی با موجودی کیف پول.

    پرداخت تومانی باید از تنظیمات فعال شده باشد.
    """

    with get_connection() as db:
        db.execute("BEGIN IMMEDIATE")

        product = db.execute("""
            SELECT *
            FROM products
            WHERE id = ?
              AND is_active = 1
        """, (product_id,)).fetchone()

        if not product:
            return False, "محصول پیدا نشد یا غیرفعال است."

        if product["product_type"] != "physical":
            return False, "خرید محصولات دیجیتال باید با Telegram Stars انجام شود."

        setting = db.execute("""
            SELECT setting_value
            FROM settings
            WHERE setting_key = 'toman_payment_enabled'
        """).fetchone()

        if not setting or setting["setting_value"] != "1":
            return False, "پرداخت تومانی در حال حاضر غیرفعال است."

        user = db.execute("""
            SELECT wallet_balance
            FROM users
            WHERE telegram_id = ?
              AND is_banned = 0
        """, (user_id,)).fetchone()

        if not user:
            return False, "حساب کاربری پیدا نشد یا مسدود است."

        if product["stock"] <= 0:
            return False, "موجودی محصول تمام شده است."

        if user["wallet_balance"] < product["price"]:
            return False, "موجودی کیف پول کافی نیست."

        stock_cursor = db.execute("""
            UPDATE products
            SET stock = stock - 1
            WHERE id = ?
              AND stock > 0
        """, (product_id,))

        if stock_cursor.rowcount != 1:
            return False, "موجودی محصول تغییر کرده است."

        db.execute("""
            UPDATE users
            SET wallet_balance = wallet_balance - ?
            WHERE telegram_id = ?
        """, (product["price"], user_id))

        order_cursor = db.execute("""
            INSERT INTO orders (
                telegram_id,
                product_id,
                volume_gb,
                price,
                status,
                payment_method
            )
            VALUES (?, ?, ?, ?, 'pending', 'toman_wallet')
        """, (
            user_id,
            product_id,
            product["volume_gb"],
            product["price"]
        ))

        order_id = order_cursor.lastrowid

        db.execute("""
            INSERT INTO transactions (
                telegram_id,
                amount,
                transaction_type,
                description
            )
            VALUES (?, ?, 'purchase', ?)
        """, (
            user_id,
            -product["price"],
            f"خرید محصول فیزیکی {product_id} - سفارش {order_id}"
        ))

        return True, f"سفارش ثبت شد. شماره سفارش: {order_id}"