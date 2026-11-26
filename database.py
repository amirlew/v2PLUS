
import sqlite3

from config import DATABASE_NAME, INITIAL_ADMINS, logger


def get_connection():
    db = sqlite3.connect(
        DATABASE_NAME,
        timeout=30
    )
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def add_column_if_missing(db, table, column, definition):
    columns = db.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    existing_columns = [row["name"] for row in columns]

    if column not in existing_columns:
        db.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


def initialize_database():

    with get_connection() as db:

        # ==========================================
        # USERS
        # ==========================================

        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                wallet_balance INTEGER NOT NULL DEFAULT 0,
                is_banned INTEGER NOT NULL DEFAULT 0,
                referred_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ==========================================
        # PRODUCTS
        # ==========================================

        db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                volume_gb INTEGER NOT NULL DEFAULT 0,
                price INTEGER NOT NULL DEFAULT 0,
                stock INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Existing products are digital by default.
        add_column_if_missing(
            db,
            "products",
            "product_type",
            "TEXT NOT NULL DEFAULT 'digital'"
        )

        # Telegram Stars price for each product.
        add_column_if_missing(
            db,
            "products",
            "stars_price",
            "INTEGER NOT NULL DEFAULT 0"
        )

        # ==========================================
        # ORDERS
        # ==========================================

        db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                product_id INTEGER,
                volume_gb INTEGER NOT NULL DEFAULT 0,
                price INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)

        add_column_if_missing(
            db,
            "orders",
            "expires_at",
            "TIMESTAMP"
        )

        add_column_if_missing(
            db,
            "orders",
            "payment_method",
            "TEXT"
        )

        add_column_if_missing(
            db,
            "orders",
            "payment_charge_id",
            "TEXT"
        )

        # ==========================================
        # CONFIG INVENTORY
        # ==========================================

        db.execute("""
            CREATE TABLE IF NOT EXISTS config_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                config_text TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'available',
                order_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sold_at TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        """)

        # ==========================================
        # TRANSACTIONS
        # ==========================================

        db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        """)

        # ==========================================
        # DISCOUNT CODES
        # ==========================================

        db.execute("""
            CREATE TABLE IF NOT EXISTS discount_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                discount_type TEXT NOT NULL,
                discount_value INTEGER NOT NULL,
                max_uses INTEGER,
                expires_at TIMESTAMP,
                is_active INTEGER NOT NULL DEFAULT 1
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS discount_usages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discount_id INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL,
                order_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(discount_id, telegram_id),
                FOREIGN KEY (discount_id) REFERENCES discount_codes(id),
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id),
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        """)

        # ==========================================
        # PAYMENT RECEIPTS
        # ==========================================

        db.execute("""
            CREATE TABLE IF NOT EXISTS payment_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                image_file_id TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                admin_id INTEGER,
                admin_note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        """)

        # ==========================================
        # SUPPORT
        # ==========================================

        db.execute("""
            CREATE TABLE IF NOT EXISTS support_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                message_text TEXT,
                message_type TEXT,
                file_id TEXT,
                is_from_admin INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        """)

        # ==========================================
        # REQUIRED CHANNELS
        # ==========================================

        db.execute("""
            CREATE TABLE IF NOT EXISTS required_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL UNIQUE,
                channel_name TEXT,
                is_permanent INTEGER NOT NULL DEFAULT 1,
                expires_at TIMESTAMP,
                is_active INTEGER NOT NULL DEFAULT 1
            )
        """)

        # ==========================================
        # SETTINGS
        # ==========================================

        db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            )
        """)

        # ==========================================
        # ADMINS
        # ==========================================

        db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                telegram_id INTEGER PRIMARY KEY,
                role TEXT NOT NULL DEFAULT 'admin',
                is_active INTEGER NOT NULL DEFAULT 1
            )
        """)

        # ==========================================
        # AUDIT LOGS
        # ==========================================

        db.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ==========================================
        # MIGRATIONS
        # ==========================================

        add_column_if_missing(
            db,
            "users",
            "referred_by",
            "INTEGER"
        )

        # ==========================================
        # INDEXES
        # ==========================================

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_telegram_id
            ON orders(telegram_id)
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_telegram_id
            ON transactions(telegram_id)
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_receipts_status
            ON payment_receipts(status)
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_support_telegram_id
            ON support_messages(telegram_id)
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_referred_by
            ON users(referred_by)
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_inventory_product_status
            ON config_inventory(product_id, status)
        """)

        # ==========================================
        # DEFAULT SETTINGS
        # ==========================================

        default_settings = {
            "toman_payment_enabled": "0",
            "stars_payment_enabled": "1",
            "custom_volume_max": "100",
            "config_validity_days": "30",
            "referral_reward": "0",
        }

        for key, value in default_settings.items():
            db.execute("""
                INSERT OR IGNORE INTO settings
                (setting_key, setting_value)
                VALUES (?, ?)
            """, (key, value))

        # ==========================================
        # INITIAL ADMINS
        # ==========================================

        for admin_id, role in INITIAL_ADMINS:
            db.execute("""
                INSERT OR IGNORE INTO admins
                (telegram_id, role, is_active)
                VALUES (?, ?, 1)
            """, (admin_id, role))

    logger.info("Database initialized successfully.")
