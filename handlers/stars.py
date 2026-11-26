import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

from services.inventory import get_product
from services.settings import get_boolean_setting
from services.payments import (
    create_stars_invoice,
    create_stars_payload,
    is_valid_pre_checkout,
)
from services.purchases import create_stars_order


logger = logging.getLogger(__name__)


def _get_product_id_from_payload(payload):
    """استخراج شناسه کاربر و محصول از payload معتبر VitoPlus."""

    if not isinstance(payload, str):
        return None

    match = re.fullmatch(r"vitoplus:stars:(\d+):(\d+)", payload)
    if not match:
        return None

    return int(match.group(1)), int(match.group(2))


async def buy_with_stars(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """ساخت و ارسال فاکتور Telegram Stars برای محصول دیجیتال."""

    query = update.callback_query
    if not query:
        return

    await query.answer()

    user = query.from_user
    data = query.data or ""

    try:
        product_id = int(data.rsplit("_", 1)[1])
    except (ValueError, IndexError):
        await query.edit_message_text("❌ شناسه محصول معتبر نیست.")
        return

    if not get_boolean_setting("stars_payment_enabled", default=True):
        await query.edit_message_text(
            "پرداخت با Telegram Stars در حال حاضر غیرفعال است."
        )
        return

    product = get_product(product_id)

    if not product or not product["is_active"]:
        await query.edit_message_text("❌ این محصول در دسترس نیست.")
        return

    if product["product_type"] != "digital":
        await query.edit_message_text(
            "پرداخت با Stars فقط برای محصولات دیجیتال فعال است."
        )
        return

    if product["stock"] <= 0:
        await query.edit_message_text(
            "😕 موجودی این محصول تمام شده است."
        )
        return

    try:
        stars_price = int(product["stars_price"] or 0)
    except (TypeError, ValueError):
        stars_price = 0

    if stars_price <= 0:
        await query.edit_message_text(
            "قیمت Stars این محصول هنوز توسط مدیر تنظیم نشده است."
        )
        return

    payload = create_stars_payload(user.id, product_id)

    try:
        invoice = create_stars_invoice(
            title=product["name"],
            description=(
                f"خرید کانفیگ {product['volume_gb']} گیگابایتی "
                "با اعتبار ۳۰ روز"
            ),
            payload=payload,
            stars_amount=stars_price,
        )
    except (TypeError, ValueError) as error:
        logger.exception("Could not create Stars invoice: %s", error)
        await query.edit_message_text(
            "❌ ساخت فاکتور پرداخت ناموفق بود. لطفاً بعداً تلاش کن."
        )
        return

    await context.bot.send_invoice(
        chat_id=user.id,
        **invoice
    )


async def pre_checkout(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """اعتبارسنجی پرداخت قبل از تأیید تلگرام."""

    query = update.pre_checkout_query
    if not query:
        return

    parsed = _get_product_id_from_payload(query.invoice_payload)

    if not parsed:
        await query.answer(
            ok=False,
            error_message="اطلاعات فاکتور معتبر نیست."
        )
        return

    payload_user_id, product_id = parsed

    if payload_user_id != query.from_user.id:
        await query.answer(
            ok=False,
            error_message="این فاکتور متعلق به حساب شما نیست."
        )
        return

    if not get_boolean_setting("stars_payment_enabled", default=True):
        await query.answer(
            ok=False,
            error_message="پرداخت Stars در حال حاضر غیرفعال است."
        )
        return

    product = get_product(product_id)

    if (
        not product
        or not product["is_active"]
        or product["product_type"] != "digital"
    ):
        await query.answer(
            ok=False,
            error_message="این محصول دیگر قابل خرید نیست."
        )
        return

    if product["stock"] <= 0:
        await query.answer(
            ok=False,
            error_message="موجودی این محصول تمام شده است."
        )
        return

    try:
        stars_price = int(product["stars_price"] or 0)
    except (TypeError, ValueError):
        stars_price = 0

    expected_payload = create_stars_payload(
        query.from_user.id,
        product_id
    )

    if stars_price <= 0 or not is_valid_pre_checkout(
        query,
        expected_payload,
        stars_price
    ):
        await query.answer(
            ok=False,
            error_message="مبلغ یا اطلاعات فاکتور معتبر نیست."
        )
        return

    await query.answer(ok=True)


async def successful_payment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """ثبت سفارش و تحویل کانفیگ بعد از پرداخت موفق Stars."""

    message = update.effective_message
    user = update.effective_user

    if not message or not user or not message.successful_payment:
        return

    payment = message.successful_payment
    parsed = _get_product_id_from_payload(payment.invoice_payload)

    if not parsed:
        await message.reply_text(
            "❌ اطلاعات پرداخت قابل شناسایی نیست. "
            "لطفاً با پشتیبانی تماس بگیر."
        )
        return

    payload_user_id, product_id = parsed

    if payload_user_id != user.id:
        await message.reply_text(
            "❌ این پرداخت با حساب کاربری شما مطابقت ندارد. "
            "لطفاً با پشتیبانی تماس بگیر."
        )
        return

    success, result_message, config_text = create_stars_order(
        user.id,
        product_id,
        payment
    )

    if not success:
        logger.error(
            "Stars payment received but order creation failed. "
            "user_id=%s product_id=%s charge_id=%s reason=%s",
            user.id,
            product_id,
            payment.telegram_payment_charge_id,
            result_message,
        )

        try:
            await context.bot.refund_star_payment(
                user_id=user.id,
                telegram_payment_charge_id=payment.telegram_payment_charge_id,
            )
        except Exception:
            logger.exception(
                "Automatic Stars refund failed for user %s",
                user.id
            )
            await message.reply_text(
                "پرداخت دریافت شد اما ثبت سفارش ناموفق بود و بازپرداخت "
                "خودکار هم انجام نشد. لطفاً فوراً با پشتیبانی تماس بگیر "
                "و کد پرداخت را ارسال کن."
            )
            return

        await message.reply_text(
            "ثبت سفارش ناموفق بود؛ مبلغ پرداختی به صورت Stars "
            "به حساب شما بازگردانده شد.\n\n"
            f"دلیل: {result_message}"
        )
        return

    await message.reply_text(
        "🎉 پرداخت با موفقیت انجام شد!\n\n"
        f"{result_message}\n\n"
        "🔐 کانفیگ اختصاصی شما:\n"
        f"<code>{config_text}</code>\n\n"
        "⏳ اعتبار کانفیگ: ۳۰ روز",
        parse_mode="HTML",
    )
