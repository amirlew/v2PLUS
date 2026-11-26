from database import get_connection


# ==========================================
# PRODUCT INVENTORY
# ==========================================

def get_product(product_id):
    """دریافت محصول همراه با موجودی واقعی و قیمت Telegram Stars."""

    with get_connection() as db:
        return db.execute(
            """
            SELECT
                p.id,
                p.name,
                p.volume_gb,
                p.price,
                p.stars_price,
                CASE
                    WHEN p.product_type = 'digital' THEN (
                        SELECT COUNT(*)
                        FROM config_inventory ci
                        WHERE ci.product_id = p.id
                          AND ci.status = 'available'
                    )
                    ELSE p.stock
                END AS stock,
                p.is_active,
                p.created_at,
                p.product_type
            FROM products p
            WHERE p.id = ?
            """,
            (product_id,)
        ).fetchone()


def get_available_products():
    """دریافت محصولات فعال دارای موجودی واقعی."""

    with get_connection() as db:
        return db.execute(
            """
            SELECT
                p.id,
                p.name,
                p.volume_gb,
                p.price,
                p.stars_price,
                CASE
                    WHEN p.product_type = 'digital' THEN (
                        SELECT COUNT(*)
                        FROM config_inventory ci
                        WHERE ci.product_id = p.id
                          AND ci.status = 'available'
                    )
                    ELSE p.stock
                END AS stock,
                p.is_active,
                p.created_at,
                p.product_type
            FROM products p
            WHERE p.is_active = 1
              AND (
                  (
                      p.product_type = 'digital'
                      AND EXISTS (
                          SELECT 1
                          FROM config_inventory ci
                          WHERE ci.product_id = p.id
                            AND ci.status = 'available'
                      )
                  )
                  OR
                  (
                      p.product_type = 'physical'
                      AND p.stock > 0
                  )
              )
            ORDER BY p.id DESC
            """
        ).fetchall()


def get_inventory_count(product_id):
    """تعداد کانفیگ‌های آماده یک محصول دیجیتال."""

    with get_connection() as db:
        result = db.execute(
            """
            SELECT COUNT(*)
            FROM config_inventory
            WHERE product_id = ?
              AND status = 'available'
            """,
            (product_id,)
        ).fetchone()

    return result[0]


def set_product_stars_price(product_id, stars_price):
    """تنظیم قیمت Stars؛ صفر یعنی خرید Stars برای محصول غیرفعال."""

    if (
        not isinstance(stars_price, int)
        or isinstance(stars_price, bool)
        or stars_price < 0
    ):
        return False, "قیمت Stars باید عدد صحیح صفر یا بیشتر باشد."

    with get_connection() as db:
        product = db.execute(
            """
            SELECT id, product_type
            FROM products
            WHERE id = ?
            """,
            (product_id,)
        ).fetchone()

        if not product:
            return False, "محصول پیدا نشد."

        if product["product_type"] != "digital":
            return False, "پرداخت Stars فقط برای محصولات دیجیتال است."

        db.execute(
            """
            UPDATE products
            SET stars_price = ?
            WHERE id = ?
            """,
            (stars_price, product_id)
        )

    return True, "قیمت Stars با موفقیت ذخیره شد."


# ==========================================
# ADD CONFIG
# ==========================================

def add_config(product_id, config_text):
    """افزودن کانفیگ جدید به انبار دیجیتال."""

    if not isinstance(config_text, str):
        return False, "متن کانفیگ معتبر نیست."

    config_text = config_text.strip()

    if not config_text:
        return False, "متن کانفیگ خالی است."

    with get_connection() as db:
        product = db.execute(
            """
            SELECT id, product_type
            FROM products
            WHERE id = ?
            """,
            (product_id,)
        ).fetchone()

        if not product:
            return False, "محصول پیدا نشد."

        if product["product_type"] != "digital":
            return False, "امکان افزودن کانفیگ به محصول فیزیکی وجود ندارد."

        try:
            db.execute(
                """
                INSERT INTO config_inventory (
                    product_id,
                    config_text,
                    status
                )
                VALUES (?, ?, 'available')
                """,
                (product_id, config_text)
            )
        except Exception as error:
            if "UNIQUE constraint failed" in str(error):
                return False, "این کانفیگ قبلاً ثبت شده است."
            raise

        count = db.execute(
            """
            SELECT COUNT(*)
            FROM config_inventory
            WHERE product_id = ?
              AND status = 'available'
            """,
            (product_id,)
        ).fetchone()[0]

        db.execute(
            """
            UPDATE products
            SET stock = ?
            WHERE id = ?
            """,
            (count, product_id)
        )

    return True, "کانفیگ با موفقیت به انبار اضافه شد."


# ==========================================
# REMOVE CONFIG
# ==========================================

def remove_config(config_id):
    """حذف کانفیگ آماده از انبار."""

    with get_connection() as db:
        config = db.execute(
            """
            SELECT product_id
            FROM config_inventory
            WHERE id = ?
              AND status = 'available'
            """,
            (config_id,)
        ).fetchone()

        if not config:
            return False, "کانفیگ آماده پیدا نشد."

        product_id = config["product_id"]

        db.execute(
            """
            DELETE FROM config_inventory
            WHERE id = ?
            """,
            (config_id,)
        )

        count = db.execute(
            """
            SELECT COUNT(*)
            FROM config_inventory
            WHERE product_id = ?
              AND status = 'available'
            """,
            (product_id,)
        ).fetchone()[0]

        db.execute(
            """
            UPDATE products
            SET stock = ?
            WHERE id = ?
            """,
            (count, product_id)
        )

    return True, "کانفیگ از انبار حذف شد."


# ==========================================
# VIEW INVENTORY
# ==========================================

def get_product_configs(product_id, status=None):
    """دریافت کانفیگ‌های یک محصول."""

    with get_connection() as db:
        if status:
            return db.execute(
                """
                SELECT *
                FROM config_inventory
                WHERE product_id = ?
                  AND status = ?
                ORDER BY id DESC
                """,
                (product_id, status)
            ).fetchall()

        return db.execute(
            """
            SELECT *
            FROM config_inventory
            WHERE product_id = ?
            ORDER BY id DESC
            """,
            (product_id,)
        ).fetchall()


def get_config_by_order(order_id):
    """دریافت کانفیگ تحویل‌شده برای یک سفارش."""

    with get_connection() as db:
        return db.execute(
            """
            SELECT *
            FROM config_inventory
            WHERE order_id = ?
              AND status = 'sold'
            """,
            (order_id,)
        ).fetchone()


# ==========================================
# CONFIG DELIVERY
# ==========================================

def get_available_config(product_id):
    """پیدا کردن یک کانفیگ آماده."""

    with get_connection() as db:
        return db.execute(
            """
            SELECT *
            FROM config_inventory
            WHERE product_id = ?
              AND status = 'available'
            ORDER BY id ASC
            LIMIT 1
            """,
            (product_id,)
        ).fetchone()


def mark_config_sold(config_id, order_id):
    """ثبت فروش کانفیگ و اتصال آن به سفارش."""

    with get_connection() as db:
        config = db.execute(
            """
            SELECT product_id
            FROM config_inventory
            WHERE id = ?
              AND status = 'available'
            """,
            (config_id,)
        ).fetchone()

        if not config:
            return False

        product_id = config["product_id"]

        cursor = db.execute(
            """
            UPDATE config_inventory
            SET status = 'sold',
                order_id = ?,
                sold_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND status = 'available'
            """,
            (order_id, config_id)
        )

        if cursor.rowcount != 1:
            return False

        count = db.execute(
            """
            SELECT COUNT(*)
            FROM config_inventory
            WHERE product_id = ?
              AND status = 'available'
            """,
            (product_id,)
        ).fetchone()[0]

        db.execute(
            """
            UPDATE products
            SET stock = ?
            WHERE id = ?
            """,
            (count, product_id)
        )

    return True


# ==========================================
# LEGACY STOCK FUNCTIONS
# ==========================================

def decrease_stock(product_id, quantity=1):
    """کاهش موجودی عددی محصولات فیزیکی."""

    if (
        not isinstance(quantity, int)
        or isinstance(quantity, bool)
        or quantity <= 0
    ):
        return False

    with get_connection() as db:
        product = db.execute(
            """
            SELECT product_type
            FROM products
            WHERE id = ?
            """,
            (product_id,)
        ).fetchone()

        if not product or product["product_type"] != "physical":
            return False

        cursor = db.execute(
            """
            UPDATE products
            SET stock = stock - ?
            WHERE id = ?
              AND stock >= ?
            """,
            (quantity, product_id, quantity)
        )

    return cursor.rowcount == 1


def increase_stock(product_id, quantity=1):
    """افزایش موجودی عددی محصولات فیزیکی."""

    if (
        not isinstance(quantity, int)
        or isinstance(quantity, bool)
        or quantity <= 0
    ):
        return False

    with get_connection() as db:
        product = db.execute(
            """
            SELECT product_type
            FROM products
            WHERE id = ?
            """,
            (product_id,)
        ).fetchone()

        if not product or product["product_type"] != "physical":
            return False

        cursor = db.execute(
            """
            UPDATE products
            SET stock = stock + ?
            WHERE id = ?
            """,
            (quantity, product_id)
        )

    return cursor.rowcount == 1


def set_stock(product_id, quantity):
    """تنظیم موجودی عددی محصولات فیزیکی."""

    if (
        not isinstance(quantity, int)
        or isinstance(quantity, bool)
        or quantity < 0
    ):
        return False

    with get_connection() as db:
        product = db.execute(
            """
            SELECT product_type
            FROM products
            WHERE id = ?
            """,
            (product_id,)
        ).fetchone()

        if not product or product["product_type"] != "physical":
            return False

        cursor = db.execute(
            """
            UPDATE products
            SET stock = ?
            WHERE id = ?
            """,
            (quantity, product_id)
        )

    return cursor.rowcount == 1


def has_stock(product_id, quantity=1):
    """بررسی موجودی واقعی محصول دیجیتال یا فیزیکی."""

    if (
        not isinstance(quantity, int)
        or isinstance(quantity, bool)
        or quantity <= 0
    ):
        return False

    product = get_product(product_id)

    if product is None or not product["is_active"]:
        return False

    if product["product_type"] == "digital":
        return get_inventory_count(product_id) >= quantity

    return product["stock"] >= quantity
