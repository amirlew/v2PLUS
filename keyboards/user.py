
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu():
    keyboard = [
        [InlineKeyboardButton("🛒 خرید سرویس", callback_data="buy")],
        [InlineKeyboardButton("💰 کیف پول", callback_data="wallet")],
        [InlineKeyboardButton("👤 حساب کاربری", callback_data="account")],
        [InlineKeyboardButton("📦 سفارش‌های من", callback_data="orders")],
        [InlineKeyboardButton("💳 تراکنش‌ها", callback_data="transactions")],
        [InlineKeyboardButton("🎁 زیرمجموعه‌گیری", callback_data="referrals")],
        [InlineKeyboardButton("🎧 پشتیبانی", callback_data="support")],
        [InlineKeyboardButton("📖 راهنما", callback_data="guide")],
    ]

    return InlineKeyboardMarkup(keyboard)


def back_to_main():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 بازگشت به منوی اصلی",
                callback_data="main"
            )
        ]
    ])


def cancel_button():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "❌ لغو عملیات",
                callback_data="cancel"
            )
        ]
    ])


def confirm_purchase(product_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ تأیید خرید",
                callback_data=f"confirm_purchase_{product_id}"
            ),
            InlineKeyboardButton(
                "❌ انصراف",
                callback_data="buy"
            ),
        ]
    ])


def product_details_keyboard(
    product_id,
    stars_price=0,
    stars_enabled=True
):
    keyboard = []

    if stars_enabled and stars_price > 0:
        keyboard.append([
            InlineKeyboardButton(
                f"⭐ خرید با {stars_price} استارز",
                callback_data=f"buy_stars_{product_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 بازگشت به محصولات",
            callback_data="buy"
        )
    ])

    return InlineKeyboardMarkup(keyboard)


def product_list_keyboard(products):
    keyboard = []

    for product in products:
        product_id = product["id"]
        name = product["name"]
        volume = product["volume_gb"]
        price = product["price"]
        stars_price = product["stars_price"]

        label = f"📦 {name} | {volume}GB | {price:,} تومان"

        if stars_price and stars_price > 0:
            label += f" | ⭐ {stars_price}"

        keyboard.append([
            InlineKeyboardButton(
                label,
                callback_data=f"product_{product_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 بازگشت به منوی اصلی",
            callback_data="main"
        )
    ])

    return InlineKeyboardMarkup(keyboard)
