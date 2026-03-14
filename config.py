import os

TOKEN = os.getenv("DISCORD_TOKEN")

DB_CONFIG = {
    "host": os.getenv("MYSQLHOST"),
    "user": os.getenv("MYSQLUSER"),
    "password": os.getenv("MYSQLPASSWORD"),
    "database": os.getenv("MYSQLDATABASE"),
    "port": int(os.getenv("MYSQLPORT")),
}

EMOJI_STORAGE_GUILD_ID = int(os.getenv("EMOJI_STORAGE_GUILD_ID"))
CHEST_EMOJI_NAME = "raya_chest"

PREFIXES = ("h! ", "H! ", "h!", "H!")
