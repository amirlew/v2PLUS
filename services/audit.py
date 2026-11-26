
from database import get_connection


def _normalize_limit(limit, default=30):
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        return default

    return max(1, min(limit, 500))


def log_admin_action(admin_id, action, details=""):
    """ثبت فعالیت مدیر در گزارش مدیریتی."""
    if admin_id is None or not action:
        return False

    with get_connection() as db:
        db.execute(
            """
            INSERT INTO audit_logs
            (admin_id, action, details)
            VALUES (?, ?, ?)
            """,
            (
                int(admin_id),
                str(action).strip(),
                str(details or "")
            )
        )

    return True


def get_admin_logs(limit=30):
    """دریافت آخرین فعالیت‌های مدیران."""
    limit = _normalize_limit(limit)

    with get_connection() as db:
        return db.execute(
            """
            SELECT id, admin_id, action, details, created_at
            FROM audit_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()


def get_admin_logs_by_user(admin_id, limit=30):
    """دریافت فعالیت‌های یک مدیر مشخص."""
    if admin_id is None:
        return []

    limit = _normalize_limit(limit)

    with get_connection() as db:
        return db.execute(
            """
            SELECT id, admin_id, action, details, created_at
            FROM audit_logs
            WHERE admin_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(admin_id), limit)
        ).fetchall()
