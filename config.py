import os

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing.")

MYSQLHOST = os.getenv("MYSQLHOST")
MYSQLUSER = os.getenv("MYSQLUSER")
MYSQLPASSWORD = os.getenv("MYSQLPASSWORD")
MYSQLDATABASE = os.getenv("MYSQLDATABASE")
MYSQLPORT = os.getenv("MYSQLPORT", "3306")
EMOJI_STORAGE_GUILD_ID_RAW = os.getenv("EMOJI_STORAGE_GUILD_ID", "1145734578363961455")

missing = []
if not MYSQLHOST:
    missing.append("MYSQLHOST")
if not MYSQLUSER:
    missing.append("MYSQLUSER")
if not MYSQLPASSWORD:
    missing.append("MYSQLPASSWORD")
if not MYSQLDATABASE:
    missing.append("MYSQLDATABASE")

if missing:
    raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

DB_CONFIG = {
    "host": MYSQLHOST,
    "user": MYSQLUSER,
    "password": MYSQLPASSWORD,
    "database": MYSQLDATABASE,
    "port": int(MYSQLPORT),
}

EMOJI_STORAGE_GUILD_ID = int(EMOJI_STORAGE_GUILD_ID_RAW)
CHEST_EMOJI_NAME = "raya_chest"

PREFIXES = ("h! ", "H! ", "h!", "H!")
