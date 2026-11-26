
from database import get_connection


VALID_PRODUCT_TYPES = ("digital", "physical")


def create_product(
    name,
    volume_gb,
    price,
    stock=0,
    product_type="digital",
    stars_price=0
):
    """ساخت محصول دیجیتال یا فیزیکی"""

    name = str(name).strip()
    product_type = str(product_type).strip().lower()

    if not name:
        return False, "نام محصول نمی‌تواند خالی باشد."

    if product_type not in VALID_PRODUCT_TYPES:
        return False, "نوع محصول معتبر نیست."

    if (
        not isinstance(volume_gb, int)
        or isinstance(volume_gb, bool)
        or volume_gb < 0
    ):
        return False, "حجم محصول باید عدد صحیح غیرمنفی باشد."

    if product_type == "digital" and volume_gb <= 0:
        return False, "حجم محصول دیجیتال باید بیشتر از صفر باشد."

    if (
        not isinstance(price, int)
        or isinstance(price, bool)
        or price <= 0
    ):
        return False, "قیمت محصول باید عدد صحیح مثبت باشد."

    if (
        not isinstance(stock, int)
        or isinstance(stock, bool)
        or stock < 0
    ):
        return False, "موجودی نمی‌تواند منفی باشد."

    if (
        not isinstance(stars_price, int)
        or isinstance(stars_price, bool)
        or stars_price < 0
    ):
        return False, "قیمت Stars باید عدد صحیح غیرمنفی باشد."

    if product_type == "digital":
        stock = 0

    with get_connection() as db:
        cursor = db.execute(
            """
            INSERT INTO products (
                name,
                volume_gb,
                price,
                stock,
                is_active,
                product_type,
                stars_price
            )
            VALUES (?, ?, ?, ?, 1, ?, ?)
            """,
            (
                name,
                volume_gb,
                price,
                stock,
                product_type,
                stars_price
            )
        )

        product_id = cursor.lastrowid

    return True, product_id


def get_product_details(product_id):
    """دریافت اطلاعات محصول همراه با موجودی واقعی"""

    with get_connection() as db:
        return db.execute(
            """
            SELECT
                p.id,
                p.name,
                p.volume_gb,
                p.price,
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
                p.product_type,
                p.stars_price
            FROM products p
            WHERE p.id = ?
            """,
            (product_id,)
        ).fetchone()


def get_all_products():
    """دریافت تمام محصولات همراه با موجودی واقعی"""

    with get_connection() as db:
        return db.execute(
            """
            SELECT
                p.id,
                p.name,
                p.volume_gb,
                p.price,
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
                p.product_type,
                p.stars_price
            FROM products p
            ORDER BY p.id DESC
            """
        ).fetchall()


def update_product(
    product_id,
    name=None,
    volume_gb=None,
    price=None,
    stars_price=None
):
    """ویرایش اطلاعات محصول"""

    fields = []
    values = []

    if name is not None:
        name = str(name).strip()

        if not name:
            return False, "نام محصول نمی‌تواند خالی باشد."

        fields.append("name = ?")
        values.append(name)

    if volume_gb is not None:
        if (
            not isinstance(volume_gb, int)
            or isinstance(volume_gb, bool)
            or volume_gb < 0
        ):
            return False, "حجم باید عدد صحیح غیرمنفی باشد."

        fields.append("volume_gb = ?")
        values.append(volume_gb)

    if price is not None:
        if (
            not isinstance(price, int)
            or isinstance(price, bool)
            or price <= 0
        ):
            return False, "قیمت باید عدد صحیح مثبت باشد."

        fields.append("price = ?")
        values.append(price)

    if stars_price is not None:
        if (
            not isinstance(stars_price, int)
            or isinstance(stars_price, bool)
            or stars_price < 0
        ):
            return False, "قیمت Stars باید عدد صحیح غیرمنفی باشد."

        fields.append("stars_price = ?")
        values.append(stars_price)

    if not fields:
        return False, "هیچ تغییری برای ذخیره وارد نشده است."

    values.append(product_id)

    with get_connection() as db:
        product = db.execute(
            """
            SELECT product_type
            FROM products
            WHERE id = ?
            """,
            (product_id,)
        ).fetchone()

        if product is None:
            return False, "محصول پیدا نشد."

        if (
            product["product_type"] == "digital"
            and volume_gb is not None
            and volume_gb <= 0
        ):
            return False, "حجم محصول دیجیتال باید بیشتر از صفر باشد."

        cursor = db.execute(
            f"""
            UPDATE products
            SET {", ".join(fields)}
            WHERE id = ?
            """,
            values
        )

    if cursor.rowcount == 0:
        return False, "محصول پیدا نشد."

    return True, "اطلاعات محصول با موفقیت ویرایش شد."


def set_product_active(product_id, active):
    """فعال یا غیرفعال کردن محصول"""

    if active not in (0, 1, False, True):
        return False

    with get_connection() as db:
        cursor = db.execute(
            """
            UPDATE products
            SET is_active = ?
            WHERE id = ?
            """,
            (int(active), product_id)
        )

    return cursor.rowcount == 1


def set_product_stock(product_id, stock):
    """
    تنظیم موجودی عددی محصولات فیزیکی.
    موجودی محصولات دیجیتال باید با افزودن یا حذف کانفیگ تغییر کند.
    """

    if (
        not isinstance(stock, int)
        or isinstance(stock, bool)
        or stock < 0
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

        if product is None:
            return False

        if product["product_type"] == "digital":
            return False

        cursor = db.execute(
            """
            UPDATE products
            SET stock = ?
            WHERE id = ?
            """,
            (stock, product_id)
        )

    return cursor.rowcount == 1
