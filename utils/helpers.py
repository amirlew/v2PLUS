from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from database import get_connection


def is_admin(user_id):
    with get_connection() as db:
        result = db.execute("""
            SELECT 1 FROM admins
            WHERE telegram_id = ? AND is_active = 1
        """, (user_id,)).fetchone()

    return result is not None


def get_admin_role(user_id):
    with get_connection() as db:
        result = db.execute("""
            SELECT role FROM admins
            WHERE telegram_id = ? AND is_active = 1
        """, (user_id,)).fetchone()

    return result["role"] if result else None


def register_user(user):
    with get_connection() as db:
        db.execute("""
            INSERT OR IGNORE INTO users
            (telegram_id, username, first_name)
            VALUES (?, ?, ?)
        """, (
            user.id,
            user.username,
            user.first_name
        ))

        db.execute("""
            UPDATE users
            SET username = ?, first_name = ?
            WHERE telegram_id = ?
        """, (
            user.username,
            user.first_name,
            user.id
        ))


def audit(admin_id, action, details=""):
    with get_connection() as db:
        db.execute("""
            INSERT INTO audit_logs
            (admin_id, action, details)
            VALUES (?, ?, ?)
        """, (admin_id, action, details))


def back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main")]
    ])


def admin_back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت به پنل مدیریت", callback_data="admin")]
    ])


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