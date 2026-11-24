import os
import logging
import sqlite3

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# -------------------- تنظیمات اولیه --------------------

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_NAME = "vitoplus.db"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# -------------------- پایگاه داده --------------------

def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    with get_connection() as db:

        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            wallet_balance INTEGER NOT NULL DEFAULT 0,
            is_banned INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            volume_gb INTEGER NOT NULL,
            price INTEGER NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            product_id INTEGER,
            volume_gb INTEGER NOT NULL,
            price INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        );

        CREATE TABLE IF NOT EXISTS discount_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            discount_type TEXT NOT NULL,
            discount_value INTEGER NOT NULL,
            max_uses INTEGER,
            expires_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS discount_usages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discount_id INTEGER NOT NULL,
            telegram_id INTEGER NOT NULL,
            order_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(discount_id, telegram_id),
            FOREIGN KEY (discount_id) REFERENCES discount_codes(id),
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        );

        CREATE TABLE IF NOT EXISTS payment_receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            image_file_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            admin_id INTEGER,
            admin_note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        );

        CREATE TABLE IF NOT EXISTS support_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            message_text TEXT,
            message_type TEXT,
            file_id TEXT,
            is_from_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        );

        CREATE TABLE IF NOT EXISTS required_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL UNIQUE,
            channel_name TEXT,
            is_permanent INTEGER NOT NULL DEFAULT 0,
            expires_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS admins (
            telegram_id INTEGER PRIMARY KEY,
            role TEXT NOT NULL DEFAULT 'owner',
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_orders_user
        ON orders(telegram_id);

        CREATE INDEX IF NOT EXISTS idx_transactions_user
        ON transactions(telegram_id);

        CREATE INDEX IF NOT EXISTS idx_receipts_status
        ON payment_receipts(status);

        CREATE INDEX IF NOT EXISTS idx_support_user
        ON support_messages(telegram_id);

        """)

        # پرداخت تومانی در شروع غیرفعال است.
        db.execute("""
            INSERT OR IGNORE INTO settings (setting_key, setting_value)
            VALUES ('toman_payment_enabled', '0')
        """)

        # حداکثر حجم خرید دلخواه در شروع 100 گیگابایت است.
        db.execute("""
            INSERT OR IGNORE INTO settings (setting_key, setting_value)
            VALUES ('custom_volume_max', '100')
        """)

        # اعتبار همه کانفیگ‌ها 30 روز است.
        db.execute("""
            INSERT OR IGNORE INTO settings (setting_key, setting_value)
            VALUES ('config_validity_days', '30')
        """)

    logger.info("Database initialized successfully.")


# -------------------- ثبت کاربران --------------------

def register_user(user):
    with get_connection() as db:
        db.execute("""
            INSERT INTO users (telegram_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
        """, (
            user.id,
            user.username,
            user.first_name
        ))


# -------------------- منوی اصلی --------------------

def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("🛒 خرید کانفیگ", callback_data="buy"),
            InlineKeyboardButton("💳 شارژ کیف پول", callback_data="wallet_charge"),
        ],
        [
            InlineKeyboardButton("👛 حساب من", callback_data="account"),
            InlineKeyboardButton("📦 خریدهای من", callback_data="orders"),
        ],
        [
            InlineKeyboardButton("🧾 تراکنش‌ها", callback_data="transactions"),
            InlineKeyboardButton("👥 دعوت دوستان", callback_data="referrals"),
        ],
        [
            InlineKeyboardButton("💬 پشتیبانی", callback_data="support"),
            InlineKeyboardButton("ℹ️ راهنمای خرید", callback_data="guide"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)

    text = (
        f"سلام {user.first_name} عزیز! ❤️\n\n"
        "به ربات VitoPlus خوش اومدی.\n"
        "از منوی زیر می‌تونی خدمات موردنظرت رو انتخاب کنی."
    )

    await update.message.reply_text(
        text,
        reply_markup=main_menu()
    )


# -------------------- مدیریت دکمه‌ها --------------------

async def handle_buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "home":
        await query.edit_message_text(
            "به منوی اصلی VitoPlus خوش اومدی ❤️",
            reply_markup=main_menu()
        )

    elif data == "buy":
        await show_products(query)

    elif data == "account":
        with get_connection() as db:
            user = db.execute(
                "SELECT wallet_balance FROM users WHERE telegram_id = ?",
                (user_id,)
            ).fetchone()

        balance = user["wallet_balance"] if user else 0

        keyboard = [
            [InlineKeyboardButton("💳 شارژ کیف پول", callback_data="wallet_charge")],
            [InlineKeyboardButton("🧾 لیست تراکنش‌ها", callback_data="transactions")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="home")],
        ]

        await query.edit_message_text(
            f"👛 حساب کاربری شما\n\n"
            f"💰 موجودی کیف پول: {balance:,} تومان",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "wallet_charge":
        await query.edit_message_text(
            "💳 بخش شارژ کیف پول\n\n"
            "این بخش در مرحله بعدی تکمیل می‌شه.",
            reply_markup=back_menu()
        )

    elif data == "orders":
        await query.edit_message_text(
            "📦 خریدهای شما\n\n"
            "هنوز سفارشی برای نمایش وجود نداره.",
            reply_markup=back_menu()
        )

    elif data == "transactions":
        await query.edit_message_text(
            "🧾 تراکنش‌های شما\n\n"
            "هنوز تراکنشی ثبت نشده.",
            reply_markup=back_menu()
        )

    elif data == "referrals":
        await query.edit_message_text(
            "👥 دعوت دوستان\n\n"
            "بخش دعوت دوستان در مرحله بعدی تکمیل می‌شه.",
            reply_markup=back_menu()
        )

    elif data == "support":
        await query.edit_message_text(
            "💬 پشتیبانی\n\n"
            "بخش پشتیبانی در مرحله بعدی تکمیل می‌شه.",
            reply_markup=back_menu()
        )

    elif data == "guide":
        await query.edit_message_text(
            "ℹ️ راهنمای خرید\n\n"
            "از بخش خرید کانفیگ، محصول موردنظرت رو انتخاب کن.\n"
            "قبل از هر خرید، جزئیات سفارش و مبلغ نهایی بهت نمایش داده می‌شه.",
            reply_markup=back_menu()
        )

    elif data.startswith("product_"):
        product_id = int(data.split("_")[1])

        with get_connection() as db:
            product = db.execute(
                "SELECT * FROM products WHERE id = ? AND is_active = 1",
                (product_id,)
            ).fetchone()

        if product is None:
            await query.edit_message_text(
                "این محصول در دسترس نیست.",
                reply_markup=back_menu()
            )
            return

        if product["stock"] <= 0:
            await query.edit_message_text(
                "❌ این محصول موقتاً ناموجوده.\n\n"
                "لطفاً محصول دیگری انتخاب کنید یا از گزینه حجم دلخواه استفاده کنید. ❤️",
                reply_markup=back_menu()
            )
            return

        await query.edit_message_text(
            f"محصول: {product['name']}\n"
            f"حجم: {product['volume_gb']} گیگابایت\n"
            f"قیمت: {product['price']:,} تومان\n"
            f"اعتبار: ۳۰ روز\n\n"
            "بخش تأیید سفارش در مرحله بعدی تکمیل می‌شه.",
            reply_markup=back_menu()
        )

    elif data == "custom_volume":
        await query.edit_message_text(
            "📦 خرید حجم دلخواه\n\n"
            "این بخش در مرحله بعدی تکمیل می‌شه.",
            reply_markup=back_menu()
        )


# -------------------- نمایش محصولات --------------------

async def show_products(query):
    with get_connection() as db:
        products = db.execute("""
            SELECT id, name, volume_gb, price, stock
            FROM products
            WHERE is_active = 1
            ORDER BY volume_gb ASC
        """).fetchall()

    keyboard = []

    for product in products:
        keyboard.append([
            InlineKeyboardButton(
                f"{product['name']} | {product['volume_gb']}GB",
                callback_data=f"product_{product['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "📦 خرید حجم دلخواه",
            callback_data="custom_volume"
        )
    ])

    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت", callback_data="home")
    ])

    if not products:
        text = (
            "🛒 در حال حاضر محصول آماده‌ای برای فروش وجود نداره.\n\n"
            "می‌تونی از گزینه خرید حجم دلخواه استفاده کنی."
        )
    else:
        text = "🛒 محصولات موجود\n\nمحصول موردنظرت رو انتخاب کن:"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="home")]
    ])


# -------------------- اجرای ربات --------------------

def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN در فایل .env تنظیم نشده است."
        )

    initialize_database()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        CallbackQueryHandler(handle_buttons)
    )

    logger.info("VitoPlus bot is starting...")

    application.run_polling()


if __name__ == "__main__":
    main()