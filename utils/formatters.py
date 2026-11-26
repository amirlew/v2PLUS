from datetime import datetime


def format_toman(amount):
    """نمایش مبلغ به تومان با جداکننده سه‌رقمی"""

    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return "نامشخص"

    return f"{amount:,} تومان"


def format_volume(volume):
    """نمایش حجم بر حسب گیگابایت"""

    try:
        volume = int(volume)
    except (TypeError, ValueError):
        return "نامشخص"

    return f"{volume} گیگابایت"


def format_datetime(value):
    """تبدیل تاریخ دیتابیس به نمایش خوانا"""

    if not value:
        return "نامشخص"

    try:
        date = datetime.fromisoformat(str(value))
        return date.strftime("%Y-%m-%d  %H:%M")
    except (ValueError, TypeError):
        return str(value)


def format_status(status):
    """تبدیل وضعیت سفارش به متن فارسی"""

    statuses = {
        "pending": "در انتظار",
        "completed": "تکمیل‌شده",
        "cancelled": "لغوشده",
        "failed": "ناموفق",
        "refunded": "بازپرداخت‌شده",
    }

    return statuses.get(str(status).lower(), "نامشخص")


def format_boolean(value):
    """نمایش وضعیت فعال یا غیرفعال"""

    return "فعال ✅" if value else "غیرفعال ❌"


def format_user_id(user_id):
    """نمایش شناسه کاربر"""

    return f"`{user_id}`"


def format_order(order):
    """ساخت خلاصه متنی سفارش"""

    if not order:
        return "سفارشی پیدا نشد."

    return (
        f"🧾 سفارش شماره: {order['id']}\n"
        f"📦 حجم: {format_volume(order['volume_gb'])}\n"
        f"💰 مبلغ: {format_toman(order['price'])}\n"
        f"📌 وضعیت: {format_status(order['status'])}\n"
        f"🕒 تاریخ: {format_datetime(order['created_at'])}"
    )