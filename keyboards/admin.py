from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def admin_menu():
    keyboard = [
        [InlineKeyboardButton("📦 مدیریت محصولات", callback_data="admin_products")],
        [InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users")],
        [InlineKeyboardButton("🛍 مدیریت سفارش‌ها", callback_data="admin_orders")],
        [InlineKeyboardButton("📊 آمار ربات", callback_data="admin_stats")],
        [InlineKeyboardButton("📜 گزارش فعالیت‌ها", callback_data="admin_logs")],
        [InlineKeyboardButton("👮 مدیریت مدیران", callback_data="admin_manage")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main")],
    ]

    return InlineKeyboardMarkup(keyboard)


def admin_back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت به پنل مدیریت", callback_data="admin")]
    ])


def product_management(product_id):
    keyboard = [
        [
            InlineKeyboardButton(
                "✏️ ویرایش قیمت",
                callback_data=f"edit_price_{product_id}"
            ),
            InlineKeyboardButton(
                "📦 ویرایش موجودی",
                callback_data=f"edit_stock_{product_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "🗑 حذف محصول",
                callback_data=f"delete_product_{product_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="admin_products"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def user_management(user_id):
    keyboard = [
        [
            InlineKeyboardButton(
                "🚫 مسدود کردن",
                callback_data=f"ban_{user_id}"
            ),
            InlineKeyboardButton(
                "✅ رفع مسدودیت",
                callback_data=f"unban_{user_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="admin_users"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)