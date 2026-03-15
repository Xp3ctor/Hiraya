from datetime import datetime, timedelta
import random
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
    "common fish": 2,
    "uncommon fish": 5,
    "rare fish": 10,
    "epic fish": 30,
    "legendary fish": 150,
    "mythical fish": 1000
}

FISH_XP = {
    "common fish": 1,
    "uncommon fish": 2,
    "rare fish": 5,
    "epic fish": 10,
    "legendary fish": 20,
    "mythical fish": 50
}

FISH_EMOJI_NAMES = {
    "common fish": "commonfish",
    "uncommon fish": "uncommonfish",
    "rare fish": "rarefish",
    "epic fish": "epicfish",
    "legendary fish": "legendaryfish",
    "mythical fish": "mythicalfish"
}

ITEM_EMOJIS = {
    "apple": "🍎",
    "bread": "🍞",
    "small luck potion": "🧪",
    "medium luck potion": "🧪",
    "large luck potion": "🧪",
    "old rod": "🎣",
    "iron rod": "🎣",
    "gold rod": "🎣",
    "crystal rod": "🎣",
    "mythic rod": "🎣",
    "old shovel": "⛏️",
    "iron shovel": "⛏️",
    "gold shovel": "⛏️",
    "crystal shovel": "⛏️",
    "ancient shovel": "⛏️",
    "trash": "🗑️"
}

ROD_LUCK = {
    "old rod": 0,
    "iron rod": 5,
    "gold rod": 10,
    "crystal rod": 18,
    "mythic rod": 30
}

SHOVEL_LUCK = {
    "old shovel": 0,
    "iron shovel": 5,
    "gold shovel": 10,
    "crystal shovel": 18,
    "ancient shovel": 30
}

PLACES = {
    1: {
        "name": "Fishing Village",
        "required_level": 1,
        "required_coins": 0,
        "required_rod": "old rod",
        "story": "A quiet seaside village where every journey begins.",
        "luck_bonus": 0
    },
    2: {
        "name": "Pebble Shore",
        "required_level": 5,
        "required_coins": 5000,
        "required_rod": "iron rod",
        "story": "The waves are rougher here, but better catches await.",
        "luck_bonus": 5
    },
    3: {
        "name": "Coral Bay",
        "required_level": 15,
        "required_coins": 8000,
        "required_rod": "gold rod",
        "story": "Bright coral reefs hide richer fish and deeper secrets.",
        "luck_bonus": 10
    },
    4: {
        "name": "Sunken Cavern",
        "required_level": 20,
        "required_coins": 15000,
        "required_rod": "crystal rod",
        "story": "Dark waters and broken ruins challenge even skilled anglers.",
        "luck_bonus": 18
    },
    5: {
        "name": "Mythic Depths",
        "required_level": 30,
        "required_coins": 20000,
        "required_rod": "mythic rod",
        "story": "Only legends return from these waters with proof of what lives below.",
        "luck_bonus": 30
    }
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


def xp_needed_for_level(level: int) -> int:
    return 100 + ((level - 1) * 50)


def get_storage_guild(bot):
    return bot.get_guild(EMOJI_STORAGE_GUILD_ID)


def get_chest_thumbnail_url(bot):
    storage_guild = get_storage_guild(bot)
    if not storage_guild:
        return None
    chest_emoji = get(storage_guild.emojis, name=CHEST_EMOJI_NAME)
    return str(chest_emoji.url) if chest_emoji else None


def get_item_display(bot, item_name: str) -> str:
    lower_name = item_name.lower()

    if lower_name in FISH_EMOJI_NAMES:
        storage_guild = get_storage_guild(bot)
        if storage_guild:
            emoji_obj = get(storage_guild.emojis, name=FISH_EMOJI_NAMES[lower_name])
            if emoji_obj:
                return str(emoji_obj)

    if lower_name in ITEM_EMOJIS:
        return ITEM_EMOJIS[lower_name]

    return "📦"


def ensure_user(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO users (
                user_id, coins, last_daily, last_work, last_fish, last_dig,
                luck_boost_until, xp, level, adventure_started, current_place,
                equipped_rod, equipped_shovel
            )
            VALUES (%s, 0, NULL, NULL, NULL, NULL, NULL, 0, 1, 0, 1, NULL, NULL)
            ON DUPLICATE KEY UPDATE user_id = user_id
            """,
            (str(user_id),)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_user_profile(user_id: int):
    ensure_user(user_id)
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM users WHERE user_id = %s", (str(user_id),))
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def set_user_started(user_id: int):
    ensure_user(user_id)
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE users
            SET adventure_started = 1,
                current_place = 1,
                equipped_rod = 'old rod',
                equipped_shovel = 'old shovel'
            WHERE user_id = %s
            """,
            (str(user_id),)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def reset_all_users():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM inventory")
        cur.execute("DELETE FROM users")
        conn.commit()
    finally:
        cur.close()
        conn.close()


def set_current_place(user_id: int, place_id: int):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET current_place = %s WHERE user_id = %s", (place_id, str(user_id)))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def set_equipped_rod(user_id: int, rod_name: str):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET equipped_rod = %s WHERE user_id = %s", (rod_name.lower(), str(user_id)))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def set_equipped_shovel(user_id: int, shovel_name: str):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET equipped_shovel = %s WHERE user_id = %s", (shovel_name.lower(), str(user_id)))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def add_xp(user_id: int, xp_amount: int):
    ensure_user(user_id)
    profile = get_user_profile(user_id)
    xp = profile["xp"] + xp_amount
    level = profile["level"]
    leveled_up = False

    while xp >= xp_needed_for_level(level):
        xp -= xp_needed_for_level(level)
        level += 1
        leveled_up = True

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE users SET xp = %s, level = %s WHERE user_id = %s",
            (xp, level, str(user_id))
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()

    return level, xp, leveled_up


def get_balance(user_id: int) -> int:
    return get_user_profile(user_id)["coins"]


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


def _get_time_field(user_id: int, field: str):
    profile = get_user_profile(user_id)
    return profile[field]


def _set_time_field(user_id: int, field: str, value):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(f"UPDATE users SET {field} = %s WHERE user_id = %s", (value, str(user_id)))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_last_daily(user_id: int):
    return _get_time_field(user_id, "last_daily")


def set_last_daily(user_id: int, value):
    _set_time_field(user_id, "last_daily", value)


def get_last_work(user_id: int):
    return _get_time_field(user_id, "last_work")


def set_last_work(user_id: int, value):
    _set_time_field(user_id, "last_work", value)


def get_last_fish(user_id: int):
    return _get_time_field(user_id, "last_fish")


def set_last_fish(user_id: int, value):
    _set_time_field(user_id, "last_fish", value)


def get_last_dig(user_id: int):
    return _get_time_field(user_id, "last_dig")


def set_last_dig(user_id: int, value):
    _set_time_field(user_id, "last_dig", value)


def get_luck_boost_until(user_id: int):
    return _get_time_field(user_id, "luck_boost_until")


def set_luck_boost_until(user_id: int, value):
    _set_time_field(user_id, "luck_boost_until", value)


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
        if not row or row["amount"] < amount:
            return False

        new_amount = row["amount"] - amount
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


def get_shop_items(category=None):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        if category:
            cur.execute(
                """
                SELECT item_name, price, description, stock, category
                FROM shop
                WHERE category = %s
                ORDER BY price ASC, item_name ASC
                """,
                (category,)
            )
        else:
            cur.execute(
                "SELECT item_name, price, description, stock, category FROM shop ORDER BY price ASC, item_name ASC"
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
            "SELECT item_name, price, description, stock, category FROM shop WHERE item_name = %s",
            (item_name.lower(),)
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def add_shop_item(item_name: str, price: int, description: str, category: str = "items"):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO shop (item_name, price, description, stock, category)
            VALUES (%s, %s, %s, 0, %s)
            ON DUPLICATE KEY UPDATE
                price = VALUES(price),
                description = VALUES(description),
                category = VALUES(category)
            """,
            (item_name.lower(), price, description, category)
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
        cur.execute("UPDATE shop SET stock = %s WHERE item_name = %s", (new_stock, item_name.lower()))
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
        cur.execute("SELECT meta_value FROM bot_meta WHERE meta_key = %s", (meta_key,))
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
        update_shop_stock(item["item_name"], random.randint(1, 5))

    set_meta("last_shop_restock", now.isoformat())
    return True


def get_sell_price(item_name: str):
    item_name = item_name.lower()
    if item_name in FISH_SELL_PRICES:
        return FISH_SELL_PRICES[item_name]
    shop_item = get_shop_item(item_name)
    if shop_item:
        return max(1, shop_item["price"] // 2)
    if item_name == "trash":
        return 1
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
