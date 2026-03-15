from datetime import datetime, timedelta
import random
import mysql.connector
from mysql.connector import pooling
from discord.utils import get

from config import DB_CONFIG, EMOJI_STORAGE_GUILD_ID, CHEST_EMOJI_NAME

db_pool = pooling.MySQLConnectionPool(
    pool_name="hiraya_pool",
    pool_size=10,
    **DB_CONFIG
)

FISH_NAMES = {
    "common fish",
    "uncommon fish",
    "rare fish",
    "epic fish",
    "legendary fish",
    "mythical fish"
}

FISH_SELL_PRICES = {
    "common fish": 8,
    "uncommon fish": 18,
    "rare fish": 45,
    "epic fish": 120,
    "legendary fish": 400,
    "mythical fish": 2500
}

FISH_EMOJI_NAMES = {
    "common fish": "commonfish",
    "uncommon fish": "uncommonfish",
    "rare fish": "rarefish",
    "epic fish": "epicfish",
    "legendary fish": "legendaryfish",
    "mythical fish": "mythicalfish"
}


def get_conn():
    return db_pool.get_connection()


def utc_now():
    return datetime.utcnow()


def format_remaining(td: timedelta):
    total_seconds = int(td.total_seconds())
    if total_seconds < 0:
        total_seconds = 0

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def get_storage_guild(bot):
    return bot.get_guild(EMOJI_STORAGE_GUILD_ID)


def get_chest_thumbnail_url(bot):
    storage_guild = get_storage_guild(bot)
    if not storage_guild:
        return None

    chest_emoji = get(storage_guild.emojis, name=CHEST_EMOJI_NAME)
    if chest_emoji:
        return str(chest_emoji.url)

    return None


def get_item_display(bot, item_name: str) -> str:
    lower_name = item_name.lower()

    if lower_name in FISH_EMOJI_NAMES:
        storage_guild = get_storage_guild(bot)
        if storage_guild:
            emoji_obj = get(storage_guild.emojis, name=FISH_EMOJI_NAMES[lower_name])
            if emoji_obj:
                return str(emoji_obj)

    fish_fallbacks = {
        "common fish": "🐟",
        "uncommon fish": "🐠",
        "rare fish": "🦈",
        "epic fish": "🐡",
        "legendary fish": "🐉",
        "mythical fish": "✨"
    }

    return fish_fallbacks.get(lower_name, "📦")


def ensure_user(user_id: int):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """
            INSERT INTO users (user_id, coins, last_daily, last_work, last_fish)
            VALUES (%s, 0, NULL, NULL, NULL)
            ON DUPLICATE KEY UPDATE user_id = user_id
            """,
            (str(user_id),)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_balance(user_id: int) -> int:
    ensure_user(user_id)
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT coins FROM users WHERE user_id = %s", (str(user_id),))
        row = cur.fetchone()
        return row["coins"] if row else 0
    finally:
        cur.close()
        conn.close()


def set_balance(user_id: int, amount: int):
    ensure_user(user_id)
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET coins = %s WHERE user_id = %s", (amount, str(user_id)))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def add_balance(user_id: int, amount: int):
    ensure_user(user_id)
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET coins = coins + %s WHERE user_id = %s", (amount, str(user_id)))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def remove_balance(user_id: int, amount: int):
    ensure_user(user_id)
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET coins = coins - %s WHERE user_id = %s", (amount, str(user_id)))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_last_daily(user_id: int):
    ensure_user(user_id)
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT last_daily FROM users WHERE user_id = %s", (str(user_id),))
        row = cur.fetchone()
        return row["last_daily"] if row else None
    finally:
        cur.close()
        conn.close()


def set_last_daily(user_id: int, value):
    ensure_user(user_id)
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET last_daily = %s WHERE user_id = %s", (value, str(user_id)))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_last_work(user_id: int):
    ensure_user(user_id)
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT last_work FROM users WHERE user_id = %s", (str(user_id),))
        row = cur.fetchone()
        return row["last_work"] if row else None
    finally:
        cur.close()
        conn.close()


def set_last_work(user_id: int, value):
    ensure_user(user_id)
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET last_work = %s WHERE user_id = %s", (value, str(user_id)))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_last_fish(user_id: int):
    ensure_user(user_id)
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT last_fish FROM users WHERE user_id = %s", (str(user_id),))
        row = cur.fetchone()
        return row["last_fish"] if row else None
    finally:
        cur.close()
        conn.close()


def set_last_fish(user_id: int, value):
    ensure_user(user_id)
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET last_fish = %s WHERE user_id = %s", (value, str(user_id)))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def add_item(user_id: int, item_name: str, amount: int):
    ensure_user(user_id)
    item_name = item_name.lower()

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO inventory (user_id, item_name, amount)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE amount = amount + VALUES(amount)
            """,
            (str(user_id), item_name, amount)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def remove_item(user_id: int, item_name: str, amount: int):
    item_name = item_name.lower()

    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT amount FROM inventory WHERE user_id = %s AND item_name = %s",
            (str(user_id), item_name)
        )
        row = cur.fetchone()

        if not row:
            return False

        current_amount = row["amount"]
        if current_amount < amount:
            return False

        new_amount = current_amount - amount

        if new_amount <= 0:
            cur.execute(
                "DELETE FROM inventory WHERE user_id = %s AND item_name = %s",
                (str(user_id), item_name)
            )
        else:
            cur.execute(
                "UPDATE inventory SET amount = %s WHERE user_id = %s AND item_name = %s",
                (new_amount, str(user_id), item_name)
            )

        conn.commit()
        return True
    finally:
        cur.close()
        conn.close()


def get_item_amount(user_id: int, item_name: str) -> int:
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT amount FROM inventory WHERE user_id = %s AND item_name = %s",
            (str(user_id), item_name.lower())
        )
        row = cur.fetchone()
        return row["amount"] if row else 0
    finally:
        cur.close()
        conn.close()


def get_inventory(user_id: int):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT item_name, amount
            FROM inventory
            WHERE user_id = %s AND amount > 0
            ORDER BY item_name ASC
            """,
            (str(user_id),)
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def get_inventory_item_rows(user_id: int, item_names: set[str]):
    if not item_names:
        return []

    placeholders = ", ".join(["%s"] * len(item_names))
    params = [str(user_id)] + list(item_names)

    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            f"""
            SELECT item_name, amount
            FROM inventory
            WHERE user_id = %s AND LOWER(item_name) IN ({placeholders}) AND amount > 0
            ORDER BY item_name ASC
            """,
            params
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def get_shop_items():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT item_name, price, description, stock FROM shop ORDER BY price ASC, item_name ASC"
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def get_shop_item(item_name: str):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT item_name, price, description, stock FROM shop WHERE item_name = %s",
            (item_name.lower(),)
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def add_shop_item(item_name: str, price: int, description: str):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO shop (item_name, price, description, stock)
            VALUES (%s, %s, %s, 0)
            ON DUPLICATE KEY UPDATE
                price = VALUES(price),
                description = VALUES(description)
            """,
            (item_name.lower(), price, description)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def remove_shop_item(item_name: str):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM shop WHERE item_name = %s", (item_name.lower(),))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def update_shop_stock(item_name: str, new_stock: int):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE shop SET stock = %s WHERE item_name = %s",
            (new_stock, item_name.lower())
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def reduce_shop_stock(item_name: str, amount: int):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE shop
            SET stock = stock - %s
            WHERE item_name = %s AND stock >= %s
            """,
            (amount, item_name.lower(), amount)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        cur.close()
        conn.close()


def get_meta(meta_key: str):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT meta_value FROM bot_meta WHERE meta_key = %s",
            (meta_key,)
        )
        row = cur.fetchone()
        return row["meta_value"] if row else None
    finally:
        cur.close()
        conn.close()


def set_meta(meta_key: str, meta_value: str):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO bot_meta (meta_key, meta_value)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE meta_value = VALUES(meta_value)
            """,
            (meta_key, meta_value)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def refresh_shop_stock_if_needed():
    last_restock_raw = get_meta("last_shop_restock")
    now = utc_now()
    should_refresh = False

    if not last_restock_raw:
        should_refresh = True
    else:
        try:
            last_restock = datetime.fromisoformat(last_restock_raw)
            if now >= last_restock + timedelta(minutes=30):
                should_refresh = True
        except ValueError:
            should_refresh = True

    if not should_refresh:
        return False

    shop_items = get_shop_items()
    for item in shop_items:
        random_stock = random.randint(1, 5)
        update_shop_stock(item["item_name"], random_stock)

    set_meta("last_shop_restock", now.isoformat())
    return True


def get_sell_price(item_name: str):
    item_name = item_name.lower()

    if item_name in FISH_SELL_PRICES:
        return FISH_SELL_PRICES[item_name]

    shop_item = get_shop_item(item_name)
    if shop_item:
        return max(1, shop_item["price"] // 2)

    return None


def get_top_coin_users(limit=10):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT user_id, coins FROM users ORDER BY coins DESC, user_id ASC LIMIT %s", (limit,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def get_top_fish_users(limit=10):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT user_id, COALESCE(SUM(amount), 0) AS total_fish
            FROM inventory
            WHERE LOWER(item_name) IN (
                'common fish',
                'uncommon fish',
                'rare fish',
                'epic fish',
                'legendary fish',
                'mythical fish'
            )
            GROUP BY user_id
            ORDER BY total_fish DESC, user_id ASC
            LIMIT %s
            """,
            (limit,)
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()
