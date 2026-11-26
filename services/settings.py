
from database import get_connection


def get_setting(key, default=None):
    """خواندن مقدار یک تنظیم."""
    if not key:
        return default

    with get_connection() as db:
        row = db.execute(
            """
            SELECT setting_value
            FROM settings
            WHERE setting_key = ?
            """,
            (str(key),)
        ).fetchone()

    return row["setting_value"] if row else default


def set_setting(key, value):
    """ثبت یا تغییر مقدار یک تنظیم."""
    if key is None or not str(key).strip() or value is None:
        return False

    with get_connection() as db:
        db.execute(
            """
            INSERT INTO settings
            (setting_key, setting_value)
            VALUES (?, ?)
            ON CONFLICT(setting_key)
            DO UPDATE SET setting_value = excluded.setting_value
            """,
            (
                str(key).strip(),
                str(value)
            )
        )

    return True


def get_all_settings():
    """دریافت تمام تنظیمات."""
    with get_connection() as db:
        return db.execute(
            """
            SELECT setting_key, setting_value
            FROM settings
            ORDER BY setting_key
            """
        ).fetchall()


def get_integer_setting(key, default=0):
    """خواندن تنظیم عددی."""
    value = get_setting(key)

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_boolean_setting(key, default=False):
    """خواندن تنظیم روشن یا خاموش."""
    value = get_setting(key)

    if value is None:
        return bool(default)

    return str(value).strip().lower() in (
        "1",
        "true",
        "yes",
        "on"
    )
