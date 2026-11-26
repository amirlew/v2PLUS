
from database import get_connection


def is_admin(user_id):
    """بررسی فعال بودن دسترسی مدیریتی."""
    if user_id is None:
        return False

    with get_connection() as db:
        admin = db.execute(
            """
            SELECT 1
            FROM admins
            WHERE telegram_id = ?
              AND is_active = 1
            LIMIT 1
            """,
            (user_id,)
        ).fetchone()

    return admin is not None


def get_admin_role(user_id):
    """دریافت نقش مدیر فعال."""
    if user_id is None:
        return None

    with get_connection() as db:
        admin = db.execute(
            """
            SELECT role
            FROM admins
            WHERE telegram_id = ?
              AND is_active = 1
            LIMIT 1
            """,
            (user_id,)
        ).fetchone()

    return admin["role"] if admin else None


def has_permission(user_id, allowed_roles):
    """بررسی دسترسی مدیر بر اساس نقش."""
    role = get_admin_role(user_id)

    if role is None:
        return False

    if isinstance(allowed_roles, str):
        allowed_roles = (allowed_roles,)

    if not allowed_roles:
        return False

    return role in allowed_roles


def get_active_admins():
    """دریافت فهرست مدیران فعال."""
    with get_connection() as db:
        return db.execute(
            """
            SELECT telegram_id, role
            FROM admins
            WHERE is_active = 1
            ORDER BY telegram_id
            """
        ).fetchall()


def deactivate_admin(user_id):
    """غیرفعال کردن دسترسی یک مدیر."""
    if user_id is None:
        return False

    with get_connection() as db:
        cursor = db.execute(
            """
            UPDATE admins
            SET is_active = 0
            WHERE telegram_id = ?
              AND is_active = 1
            """,
            (user_id,)
        )

    return cursor.rowcount == 1
