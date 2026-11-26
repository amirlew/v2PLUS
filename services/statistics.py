
from database import get_connection


def _normalize_limit(limit, default=10):
    try:
        return max(1, min(int(limit), 500))
    except (TypeError, ValueError):
        return default


def get_dashboard_statistics():
    """دریافت آمار کلی ربات."""

    with get_connection() as db:
        users = db.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(is_banned), 0) AS banned
            FROM users
            """
        ).fetchone()

        products = db.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(is_active), 0) AS active,
                COALESCE(
                    SUM(
                        CASE
                            WHEN product_type = 'digital' THEN (
                                SELECT COUNT(*)
                                FROM config_inventory ci
                                WHERE ci.product_id = products.id
                                  AND ci.status = 'available'
                            )
                            ELSE stock
                        END
                    ),
                    0
                ) AS total_stock
            FROM products
            """
        ).fetchone()

        orders = db.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(
                    CASE WHEN status = 'completed' THEN 1 ELSE 0 END
                ), 0) AS completed,
                COALESCE(SUM(
                    CASE WHEN status = 'pending' THEN 1 ELSE 0 END
                ), 0) AS pending
            FROM orders
            """
        ).fetchone()

        transactions = db.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(
                    CASE WHEN amount > 0 THEN amount ELSE 0 END
                ), 0) AS positive_amount,
                COALESCE(SUM(
                    CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END
                ), 0) AS negative_amount
            FROM transactions
            """
        ).fetchone()

        stars = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM orders
            WHERE payment_method = 'stars'
              AND status = 'completed'
            """
        ).fetchone()

    return {
        "users": dict(users),
        "products": dict(products),
        "orders": dict(orders),
        "transactions": dict(transactions),
        "stars": dict(stars),
    }


def get_recent_orders(limit=10):
    """دریافت سفارش‌های اخیر."""

    limit = _normalize_limit(limit)

    with get_connection() as db:
        return db.execute(
            """
            SELECT *
            FROM orders
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()


def get_recent_users(limit=10):
    """دریافت کاربران تازه‌وارد."""

    limit = _normalize_limit(limit)

    with get_connection() as db:
        return db.execute(
            """
            SELECT *
            FROM users
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
