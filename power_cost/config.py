# External Python modules (download required)
import dotenv
# Built-in Python Modules
import os, sys
from pathlib import Path

dotenv.load_dotenv(Path(__file__).parent / ".env")

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

if WEBHOOK_URL is None:
    print("DISCORD_WEBHOOK is not configured in .env")
    sys.exit(os.EX_NOINPUT)

# Input your CPU's Idle Power (ex: Intel N150)
IDLE = 2.2

#  Input your CPU's Maximum Load Power (100% sustained) (ex: Intel N150)
LOAD = 6.1

# directory path
DIR_PATH = Path(__file__).parent / "power_cost_logs"

# Use the actual average unit price
# from your most recent electricity bill.
# based on Korean standards
RATE_PER_KWH = 250
