import os
import logging

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_NAME = "vitoplus.db"

# Main admin
PRIMARY_ADMIN_ID = 7464096219

# Initial admins
INITIAL_ADMINS = [
    (7464096219, "owner"),
    (8306148346, "owner"),
]

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)