
from telegram import Update
from telegram.ext import ContextTypes

from services.inventory import get_product
from services.settings import get_boolean_setting
from services.payments import (
    create_stars_payload,
    create_stars_invoice,
    is_valid_pre_checkout,
)
from services.purchases import create_stars_order


async def send_stars_invoice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    product_id: int
):
    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await query.answer()

    if not get_boolean_setting("stars_payment_enabled"):
        await query.message.reply_text(
            "پرداخت با Stars در حال حاضر غیرفعال است."
        )
        return

    product = get_product(product_id)

    if (
        not product
        or not product["is_active"]
        or product["product_type"] != "digital"
    ):
        await query.message.reply_text("❌ محصول معتبر نیست.")
        return

    if product["stock"] <= 0:
        await query.message.reply_text(
            "😕 موجودی این محصول تمام شده است."
        )
        return

    stars_price = product["stars_price"]

    if not stars_price or stars_price <= 0:
        await query.message.reply_text(
            "قیمت Stars این محصول هنوز تنظیم نشده است."
        )
        return

    payload = create_stars_payload(user.id, product_id)

    invoice = create_stars_invoice(
        title=product["name"],
        description=(
            f"خرید کانفیگ {product['volume_gb']} گیگابایتی "
            "با اعتبار ۳۰ روزه"
        ),
        payload=payload,
        stars_amount=stars_price,
    )

    await context.bot.send_invoice(
        chat_id=user.id,
        **invoice
    )


async def precheckout_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.pre_checkout_query

    if not query:
        return

    try:
        parts = query.invoice_payload.split(":")
        if len(parts) != 4 or parts[0] != "vitoplus" or parts[1] != "stars":
            raise ValueError()

        user_id = int(parts[2])
        product_id = int(parts[3])

        if user_id != query.from_user.id:
            raise ValueError()

        product = get_product(product_id)

        if (
            not product
            or not product["is_active"]
            or product["product_type"] != "digital"
            or product["stock"] <= 0
            or not get_boolean_setting("stars_payment_enabled")
        ):
            raise ValueError()

        if not is_valid_pre_checkout(
            query,
            query.invoice_payload,
            product["stars_price"]
        ):
            raise ValueError()

    except (ValueError, TypeError, AttributeError):
        await query.answer(
            ok=False,
            error_message="اطلاعات پرداخت معتبر نیست یا موجودی تمام شده است."
        )
        return

    await query.answer(ok=True)


async def successful_payment_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.effective_message
    user = update.effective_user

    if not message or not user or not message.successful_payment:
        return

    payment = message.successful_payment

    try:
        parts = payment.invoice_payload.split(":")
        if len(parts) != 4 or parts[0] != "vitoplus" or parts[1] != "stars":
            return

        expected_user_id = int(parts[2])
        product_id = int(parts[3])

        if expected_user_id != user.id:
            return

    except (ValueError, TypeError, AttributeError):
        return

    success, result_text, config_text = create_stars_order(
        user.id,
        product_id,
        payment
    )

    if not success:
        try:
            await context.bot.refund_star_payment(
                user_id=user.id,
                telegram_payment_charge_id=(
                    payment.telegram_payment_charge_id
                )
            )
            await message.reply_text(
                "❌ سفارش ثبت نشد و مبلغ Stars به حسابت برگشت داده شد.\n"
                f"دلیل: {result_text}"
            )
        except Exception:
            await message.reply_text(
                "⚠️ پرداخت دریافت شد اما ثبت سفارش ناموفق بود.\n"
                "لطفاً با پشتیبانی تماس بگیر و این پیام را نگه دار.\n\n"
                f"شناسه پرداخت:\n"
                f"{payment.telegram_payment_charge_id}"
            )
        return

    await message.reply_text(
        "🎉 خریدت با موفقیت انجام شد!\n\n"
        f"{result_text}\n\n"
        "🔐 کانفیگ شما:\n"
        f"<code>{config_text}</code>",
        parse_mode="HTML"
    )
