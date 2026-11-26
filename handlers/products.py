
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_connection
from keyboards.user import (
    product_list_keyboard,
    product_details_keyboard,
)


def _stars_payment_enabled(db):
    setting = db.execute(
        """
        SELECT setting_value
        FROM settings
        WHERE setting_key = 'stars_payment_enabled'
        """
    ).fetchone()

    # اگر تنظیم وجود نداشت، پرداخت Stars غیرفعال در نظر گرفته می‌شود.
    return bool(setting and str(setting["setting_value"]) == "1")


async def show_products(query):
    """
    نمایش محصولات دیجیتال فعال که حداقل یک کانفیگ آماده دارند.
    موجودی از config_inventory محاسبه می‌شود.
    """

    with get_connection() as db:
        stars_enabled = _stars_payment_enabled(db)

        products = db.execute(
            """
            SELECT
                p.id,
                p.name,
                p.volume_gb,
                p.price,
                p.product_type,
                p.stars_price,
                (
                    SELECT COUNT(*)
                    FROM config_inventory ci
                    WHERE ci.product_id = p.id
                      AND ci.status = 'available'
                ) AS stock
            FROM products p
            WHERE p.is_active = 1
              AND p.product_type = 'digital'
              AND EXISTS (
                  SELECT 1
                  FROM config_inventory ci
                  WHERE ci.product_id = p.id
                    AND ci.status = 'available'
              )
            ORDER BY p.id DESC
            """
        ).fetchall()

    if not products:
        await query.edit_message_text(
            "📦 در حال حاضر هیچ کانفیگ آماده‌ای برای فروش موجود نیست.\n\n"
            "لطفاً کمی بعد دوباره بررسی کن.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت به منوی اصلی",
                        callback_data="main"
                    )
                ]
            ])
        )
        return

    # اگر پرداخت Stars خاموش باشد، قیمت Stars در فهرست نمایش داده نمی‌شود.
    display_products = []

    for product in products:
        item = dict(product)

        if not stars_enabled:
            item["stars_price"] = 0

        display_products.append(item)

    await query.edit_message_text(
        "🛒 محصولات آماده خرید\n\n"
        "یکی از سرویس‌های زیر رو انتخاب کن:\n\n"
        "⭐ پرداخت با Telegram Stars برای محصولاتی فعاله "
        "که قیمت Stars دارن.",
        reply_markup=product_list_keyboard(display_products)
    )


async def show_product(query, product_id):
    """
    نمایش جزئیات یک محصول دیجیتال و دکمه خرید Stars در صورت فعال بودن.
    """

    try:
        product_id = int(product_id)
    except (TypeError, ValueError):
        await query.edit_message_text(
            "❌ شناسه محصول معتبر نیست.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت به محصولات",
                        callback_data="buy"
                    )
                ]
            ])
        )
        return

    with get_connection() as db:
        product = db.execute(
            """
            SELECT
                p.id,
                p.name,
                p.volume_gb,
                p.price,
                p.product_type,
                p.stars_price,
                p.is_active,
                (
                    SELECT COUNT(*)
                    FROM config_inventory ci
                    WHERE ci.product_id = p.id
                      AND ci.status = 'available'
                ) AS stock
            FROM products p
            WHERE p.id = ?
            """,
            (product_id,)
        ).fetchone()

        stars_enabled = _stars_payment_enabled(db)

    if product is None or not product["is_active"]:
        await query.edit_message_text(
            "❌ محصول موردنظر پیدا نشد یا غیرفعال شده است.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت به محصولات",
                        callback_data="buy"
                    )
                ]
            ])
        )
        return

    if product["product_type"] != "digital":
        await query.edit_message_text(
            "📦 این محصول هنوز برای خرید آنلاین فعال نشده است.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت به محصولات",
                        callback_data="buy"
                    )
                ]
            ])
        )
        return

    if product["stock"] <= 0:
        await query.edit_message_text(
            "😕 موجودی این سرویس تمام شده است.\n"
            "لطفاً محصول دیگری انتخاب کن.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت به محصولات",
                        callback_data="buy"
                    )
                ]
            ])
        )
        return

    stars_price = int(product["stars_price"] or 0)

    if not stars_enabled:
        stars_price = 0

    payment_description = (
        "⭐ پرداخت با Telegram Stars فعال است."
        if stars_price > 0
        else "⚠️ پرداخت Stars برای این محصول در حال حاضر فعال نیست."
    )

    text = (
        f"📦 **{product['name']}**\n\n"
        f"📊 حجم سرویس: {product['volume_gb']} گیگابایت\n"
        f"💰 قیمت تومانی: {product['price']:,} تومان\n"
        f"📦 موجودی آماده: {product['stock']} عدد\n"
    )

    if stars_price > 0:
        text += f"⭐ قیمت با Stars: {stars_price}\n"

    text += (
        f"\n{payment_description}\n\n"
        "برای ادامه، روش خرید فعال رو انتخاب کن."
    )

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=product_details_keyboard(
            product_id=product["id"],
            stars_price=stars_price,
            stars_enabled=stars_enabled
        )
    )
