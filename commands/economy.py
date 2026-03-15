import asyncio
import random
import math
from datetime import timedelta

import discord
from discord.ext import commands

from database import (
    utc_now, format_remaining, get_balance, add_balance, remove_balance,
    get_last_daily, set_last_daily, get_last_work, set_last_work,
    get_last_fish, set_last_fish, add_item, remove_item, get_item_amount,
    get_inventory, get_inventory_item_rows, get_shop_items, get_shop_item,
    get_sell_price, get_top_coin_users, get_top_fish_users, get_item_display,
    get_chest_thumbnail_url, refresh_shop_stock_if_needed, reduce_shop_stock,
    FISH_NAMES, FISH_SELL_PRICES, FISH_XP, get_luck_boost_until,
    set_luck_boost_until, get_user_profile, add_xp, xp_needed_for_level,
    PLACES, set_current_place, set_user_started, get_last_dig, set_last_dig,
    ROD_LUCK, SHOVEL_LUCK, set_equipped_rod, set_equipped_shovel
)

POTION_DURATIONS = {
    "small luck potion": 15,
    "medium luck potion": 30,
    "large luck potion": 60
}

NORMAL_FISH_TABLE = [
    {"name": "Nothing",        "weight": 100, "quantity": (0, 0)},
    {"name": "Common Fish",    "weight": 300, "quantity": (2, 5)},
    {"name": "Uncommon Fish",  "weight": 250, "quantity": (2, 4)},
    {"name": "Rare Fish",      "weight": 200, "quantity": (1, 3)},
    {"name": "Epic Fish",      "weight": 100, "quantity": (1, 2)},
    {"name": "Legendary Fish", "weight": 40,  "quantity": (1, 1)},
    {"name": "Mythical Fish",  "weight": 10,  "quantity": (1, 1)},
]

BOOSTED_FISH_TABLE = [
    {"name": "Nothing",        "weight": 60,  "quantity": (0, 0)},
    {"name": "Common Fish",    "weight": 240, "quantity": (2, 5)},
    {"name": "Uncommon Fish",  "weight": 260, "quantity": (2, 4)},
    {"name": "Rare Fish",      "weight": 240, "quantity": (1, 3)},
    {"name": "Epic Fish",      "weight": 140, "quantity": (1, 2)},
    {"name": "Legendary Fish", "weight": 50,  "quantity": (1, 1)},
    {"name": "Mythical Fish",  "weight": 10,  "quantity": (1, 1)},
]

DIG_TABLE = [
    {"name": "trash", "weight": 500, "quantity": (1, 3)},
    {"name": "apple", "weight": 120, "quantity": (1, 2)},
    {"name": "bread", "weight": 80, "quantity": (1, 2)},
    {"name": "small luck potion", "weight": 30, "quantity": (1, 1)},
    {"name": "medium luck potion", "weight": 12, "quantity": (1, 1)},
    {"name": "large luck potion", "weight": 5, "quantity": (1, 1)},
    {"name": "old rod", "weight": 6, "quantity": (1, 1)},
    {"name": "iron rod", "weight": 3, "quantity": (1, 1)},
    {"name": "old shovel", "weight": 6, "quantity": (1, 1)},
    {"name": "iron shovel", "weight": 3, "quantity": (1, 1)},
]


def make_progress_bar(current: int, needed: int, length: int = 16) -> str:
    if needed <= 0:
        needed = 1
    ratio = max(0, min(1, current / needed))
    filled = round(ratio * length)
    return f"[{'█' * filled}{'░' * (length - filled)}] {int(ratio * 100)}%"


def ensure_started(profile):
    return bool(profile["adventure_started"])


def roll_weighted(table):
    total_weight = sum(entry["weight"] for entry in table)
    roll = random.randint(1, total_weight)
    current = 0
    for entry in table:
        current += entry["weight"]
        if roll <= current:
            qty = random.randint(entry["quantity"][0], entry["quantity"][1])
            return entry["name"], qty
    return "trash", 1


def get_place_name(place_id: int) -> str:
    return PLACES.get(place_id, PLACES[1])["name"]


def get_fish_table_for_place(place_id: int, potion_active: bool, equipped_rod: str | None):
    place = PLACES.get(place_id, PLACES[1])
    place_bonus = place.get("luck_bonus", 0)
    rod_bonus = ROD_LUCK.get((equipped_rod or "").lower(), 0)

    common = 300
    uncommon = 250
    rare = 200
    epic = 100
    legendary = 40
    mythical = 10
    nothing = 100

    total_bonus = place_bonus + rod_bonus

    rare += total_bonus * 2
    epic += total_bonus * 2
    legendary += total_bonus
    mythical += max(1, total_bonus // 3)
    nothing = max(20, nothing - total_bonus * 2)

    if potion_active:
        rare += 30
        epic += 20
        legendary += 10
        mythical += 5
        nothing = max(10, nothing - 20)

    return [
        {"name": "Nothing",        "weight": nothing,    "quantity": (0, 0)},
        {"name": "Common Fish",    "weight": common,     "quantity": (2, 5)},
        {"name": "Uncommon Fish",  "weight": uncommon,   "quantity": (2, 4)},
        {"name": "Rare Fish",      "weight": rare,       "quantity": (1, 3)},
        {"name": "Epic Fish",      "weight": epic,       "quantity": (1, 2)},
        {"name": "Legendary Fish", "weight": legendary,  "quantity": (1, 1)},
        {"name": "Mythical Fish",  "weight": mythical,   "quantity": (1, 1)},
    ]


def get_dig_table_for_shovel(equipped_shovel: str | None):
    shovel_bonus = SHOVEL_LUCK.get((equipped_shovel or "").lower(), 0)

    trash = 500
    apple = 120
    bread = 80
    small_luck = 30
    medium_luck = 12
    large_luck = 5
    old_rod = 6
    iron_rod = 3
    old_shovel = 6
    iron_shovel = 3

    apple += shovel_bonus
    bread += shovel_bonus
    small_luck += max(1, shovel_bonus // 2)
    medium_luck += max(1, shovel_bonus // 3)
    large_luck += max(1, shovel_bonus // 6)
    old_rod += max(1, shovel_bonus // 5)
    iron_rod += max(1, shovel_bonus // 8)
    old_shovel += max(1, shovel_bonus // 5)
    iron_shovel += max(1, shovel_bonus // 8)

    trash = max(150, trash - shovel_bonus * 8)

    return [
        {"name": "trash", "weight": trash, "quantity": (1, 3)},
        {"name": "apple", "weight": apple, "quantity": (1, 2)},
        {"name": "bread", "weight": bread, "quantity": (1, 2)},
        {"name": "small luck potion", "weight": small_luck, "quantity": (1, 1)},
        {"name": "medium luck potion", "weight": medium_luck, "quantity": (1, 1)},
        {"name": "large luck potion", "weight": large_luck, "quantity": (1, 1)},
        {"name": "old rod", "weight": old_rod, "quantity": (1, 1)},
        {"name": "iron rod", "weight": iron_rod, "quantity": (1, 1)},
        {"name": "old shovel", "weight": old_shovel, "quantity": (1, 1)},
        {"name": "iron shovel", "weight": iron_shovel, "quantity": (1, 1)},
    ]


class ShopView(discord.ui.View):
    def __init__(self, bot, author_id, items, title, refreshed=False):
        super().__init__(timeout=120)
        self.bot = bot
        self.author_id = author_id
        self.items = items
        self.title = title
        self.page = 0
        self.per_page = 4
        self.refreshed = refreshed
        self.max_page = max(0, math.ceil(len(items) / self.per_page) - 1)
        self._update_buttons()

    def _update_buttons(self):
        self.prev_button.disabled = self.page <= 0
        self.next_button.disabled = self.page >= self.max_page

    def make_embed(self):
        desc = "Available items:"
        if self.refreshed:
            desc += "\n🔄 Shop stock has been refreshed."

        embed = discord.Embed(
            title=self.title,
            description=desc,
            color=discord.Color.green()
        )

        start = self.page * self.per_page
        end = start + self.per_page

        for row in self.items[start:end]:
            item_display = get_item_display(self.bot, row["item_name"])
            embed.add_field(
                name=f"{item_display} {row['item_name'].title()} - {row['price']} coins",
                value=f"{row['description'] or 'No description.'}\n**Stock:** {row['stock']}",
                inline=False
            )

        embed.set_footer(text=f"Page {self.page + 1}/{self.max_page + 1}")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This menu is not yours.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def startadventure(self, ctx):
        profile = get_user_profile(ctx.author.id)
        if profile["adventure_started"]:
            await ctx.send("❌ You already started your adventure.")
            return

        set_user_started(ctx.author.id)
        add_item(ctx.author.id, "old rod", 1)
        add_item(ctx.author.id, "old shovel", 1)
        add_item(ctx.author.id, "small luck potion", 1)

        embed = discord.Embed(
            title="🌊 Adventure Started",
            description=(
                "You arrive at **Fishing Village**, a peaceful seaside town.\n\n"
                "An old fisherman hands you an **Old Rod**, a **Old Shovel**, "
                "and a **Small Luck Potion**.\n\n"
                "“The sea provides for those who are patient,” he says.\n"
                "Your journey begins now."
            ),
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def profile(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        profile = get_user_profile(target.id)

        level = profile["level"]
        xp = profile["xp"]
        needed = xp_needed_for_level(level)
        coins = profile["coins"]
        place_name = get_place_name(profile["current_place"])
        rod = profile["equipped_rod"] or "None"
        shovel = profile["equipped_shovel"] or "None"
        rod_bonus = ROD_LUCK.get(rod.lower(), 0) if rod != "None" else 0
        shovel_bonus = SHOVEL_LUCK.get(shovel.lower(), 0) if shovel != "None" else 0

        boost_until = profile["luck_boost_until"]
        if boost_until and utc_now() < boost_until:
            boost_text = format_remaining(boost_until - utc_now())
        else:
            boost_text = "No active boost"

        embed = discord.Embed(
            title=f"📜 {target.display_name}'s Profile",
            color=discord.Color.gold()
        )
        embed.add_field(name="Level", value=f"**{level}**", inline=True)
        embed.add_field(name="Coins", value=f"**{coins}**", inline=True)
        embed.add_field(name="Place", value=place_name, inline=True)
        embed.add_field(name="XP", value=f"{xp}/{needed}\n{make_progress_bar(xp, needed)}", inline=False)
        embed.add_field(name="Rod", value=f"{rod.title()} (+{rod_bonus}% fishing luck)", inline=True)
        embed.add_field(name="Shovel", value=f"{shovel.title()} (+{shovel_bonus}% dig luck)", inline=True)
        embed.add_field(name="Luck Boost", value=boost_text, inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=["bal", "coins", "cash"])
    async def balance(self, ctx):
        await ctx.send(f"💰 {ctx.author.mention}, you have **{get_balance(ctx.author.id)}** coins.")

    @commands.command()
    async def give(self, ctx, member: discord.Member, amount: int):
        if member.bot or member == ctx.author:
            await ctx.send("❌ Invalid target.")
            return
        if amount <= 0:
            await ctx.send("❌ Amount must be greater than 0.")
            return
        balance = get_balance(ctx.author.id)
        if balance < amount:
            await ctx.send(f"❌ You only have **{balance}** coins.")
            return
        remove_balance(ctx.author.id, amount)
        add_balance(member.id, amount)
        await ctx.send(f"💸 {ctx.author.mention} gave **{amount}** coins to {member.mention}.")

    @commands.command()
    async def daily(self, ctx):
        profile = get_user_profile(ctx.author.id)
        if not ensure_started(profile):
            await ctx.send("❌ Use `h!startadventure` first.")
            return

        now = utc_now()
        last_daily = get_last_daily(ctx.author.id)
        cooldown = timedelta(hours=24)

        if last_daily and now < last_daily + cooldown:
            await ctx.send(f"⏳ Come back in **{format_remaining((last_daily + cooldown) - now)}**.")
            return

        reward = random.randint(150, 300)
        add_balance(ctx.author.id, reward)
        set_last_daily(ctx.author.id, now)

        await ctx.send(
            f"🏘️ The villagers of **{get_place_name(profile['current_place'])}** thank you for helping today.\n"
            f"You receive **{reward}** coins."
        )

    @commands.command()
    async def work(self, ctx):
        profile = get_user_profile(ctx.author.id)
        if not ensure_started(profile):
            await ctx.send("❌ Use `h!startadventure` first.")
            return

        now = utc_now()
        last_work = get_last_work(ctx.author.id)
        cooldown = timedelta(minutes=30)

        if last_work and now < last_work + cooldown:
            await ctx.send(f"⏳ Work again in **{format_remaining((last_work + cooldown) - now)}**.")
            return

        earned = random.randint(20, 80)
        add_balance(ctx.author.id, earned)
        set_last_work(ctx.author.id, now)
        await ctx.send(f"🛠️ You helped around **{get_place_name(profile['current_place'])}** and earned **{earned}** coins.")

    @commands.command()
    async def shop(self, ctx, category: str = "items"):
        refresh_shop_stock_if_needed()

        category = category.lower()
        if category not in {"items", "rods", "shovels"}:
            await ctx.send("❌ Use `h!shop items`, `h!shop rods`, or `h!shop shovels`.")
            return

        items = get_shop_items(category)
        if not items:
            await ctx.send("🛒 That shop is empty.")
            return

        title = {
            "items": "🧪 Item Shop",
            "rods": "🎣 Rod Shop",
            "shovels": "⛏️ Shovel Shop"
        }[category]

        view = ShopView(self.bot, ctx.author.id, items, title, refreshed=False)
        await ctx.send(embed=view.make_embed(), view=view)

    @commands.command()
    async def buy(self, ctx, *, item_and_amount: str):
        refresh_shop_stock_if_needed()
        parts = item_and_amount.rsplit(" ", 1)

        if len(parts) == 2 and parts[1].isdigit():
            item_name = parts[0]
            amount = int(parts[1])
        else:
            item_name = item_and_amount
            amount = 1

        item_name = item_name.strip()
        if amount <= 0:
            await ctx.send("❌ Amount must be greater than 0.")
            return

        item = get_shop_item(item_name)
        if not item:
            await ctx.send("❌ That item is not in the shop.")
            return
        if item["stock"] < amount:
            await ctx.send(f"❌ Not enough stock. Only **{item['stock']}** left.")
            return

        total_cost = item["price"] * amount
        if get_balance(ctx.author.id) < total_cost:
            await ctx.send(f"❌ You need **{total_cost}** coins.")
            return

        if not reduce_shop_stock(item["item_name"], amount):
            await ctx.send("❌ Stock changed before your purchase. Try again.")
            return

        remove_balance(ctx.author.id, total_cost)
        add_item(ctx.author.id, item["item_name"], amount)
        await ctx.send(
            f"🛍️ You bought **{amount} {get_item_display(self.bot, item['item_name'])} {item['item_name'].title()}** "
            f"for **{total_cost}** coins."
        )

    @commands.command()
    async def equip(self, ctx, slot: str, *, item_name: str):
        profile = get_user_profile(ctx.author.id)
        if not ensure_started(profile):
            await ctx.send("❌ Use `h!startadventure` first.")
            return

        slot = slot.lower().strip()
        item_name = item_name.lower().strip()

        if slot == "rod":
            if item_name not in ROD_LUCK:
                await ctx.send("❌ That is not a valid rod.")
                return
            if get_item_amount(ctx.author.id, item_name) <= 0:
                await ctx.send(f"❌ You do not own **{item_name.title()}**.")
                return
            set_equipped_rod(ctx.author.id, item_name)
            await ctx.send(f"🎣 Equipped **{item_name.title()}**. Fishing luck: **+{ROD_LUCK[item_name]}%**.")
            return

        if slot == "shovel":
            if item_name not in SHOVEL_LUCK:
                await ctx.send("❌ That is not a valid shovel.")
                return
            if get_item_amount(ctx.author.id, item_name) <= 0:
                await ctx.send(f"❌ You do not own **{item_name.title()}**.")
                return
            set_equipped_shovel(ctx.author.id, item_name)
            await ctx.send(f"⛏️ Equipped **{item_name.title()}**. Dig luck: **+{SHOVEL_LUCK[item_name]}%**.")
            return

        await ctx.send("❌ Use `h!equip rod <rod name>` or `h!equip shovel <shovel name>`.")

    @commands.command()
    async def use(self, ctx, *, item_name: str):
        item_name = item_name.strip().lower()
        owned = get_item_amount(ctx.author.id, item_name)
        if owned <= 0:
            await ctx.send(f"❌ You do not have any **{item_name.title()}**.")
            return

        if item_name in POTION_DURATIONS:
            current_boost = get_luck_boost_until(ctx.author.id)
            now = utc_now()
            if current_boost and now < current_boost:
                await ctx.send(
                    f"❌ You already have an active luck boost. Remaining time: "
                    f"**{format_remaining(current_boost - now)}**."
                )
                return

            if not remove_item(ctx.author.id, item_name, 1):
                await ctx.send("❌ Could not use that item.")
                return

            minutes = POTION_DURATIONS[item_name]
            boost_until = now + timedelta(minutes=minutes)
            set_luck_boost_until(ctx.author.id, boost_until)

            await ctx.send(
                f"🧪 {ctx.author.mention} used **{item_name.title()}**. "
                f"Fishing luck boosted for **{minutes} minutes**!"
            )
            return

        await ctx.send("❌ That item cannot be used right now.")

    @commands.command()
    async def fish(self, ctx):
        profile = get_user_profile(ctx.author.id)
        if not ensure_started(profile):
            await ctx.send("❌ Use `h!startadventure` first.")
            return

        now = utc_now()
        last_fish = get_last_fish(ctx.author.id)
        cooldown = timedelta(minutes=1)

        if last_fish and now < last_fish + cooldown:
            await ctx.send(f"⏳ Fish again in **{format_remaining((last_fish + cooldown) - now)}**.")
            return

        equipped_rod = profile["equipped_rod"]
        if not equipped_rod:
            await ctx.send("❌ You need a rod equipped.")
            return

        set_last_fish(ctx.author.id, now)

        active_boost = get_luck_boost_until(ctx.author.id)
        potion_active = active_boost is not None and now < active_boost
        place_id = profile["current_place"]
        place = PLACES.get(place_id, PLACES[1])
        rod_bonus = ROD_LUCK.get((equipped_rod or "").lower(), 0)

        cast = await ctx.send(
            f"🎣 {ctx.author.mention} casts a line in **{place['name']}**...\n"
            f"✨ Place Luck: **+{place['luck_bonus']}%** | Rod Luck: **+{rod_bonus}%**"
        )
        await asyncio.sleep(random.randint(3, 5))

        fish_table = get_fish_table_for_place(place_id, potion_active, equipped_rod)
        result_name, qty = roll_weighted(fish_table)

        if result_name.lower() == "nothing":
            msg = (
                f"🌊 {ctx.author.mention} caught **nothing** in **{place['name']}**.\n"
                f"✨ Place Luck: **+{place['luck_bonus']}%** | Rod Luck: **+{rod_bonus}%**"
            )
            if potion_active:
                msg += "\n🧪 Luck Potion Active"
            await cast.edit(content=msg)
            return

        add_item(ctx.author.id, result_name, qty)
        xp_gain = FISH_XP[result_name.lower()] * qty
        new_level, current_xp, leveled_up = add_xp(ctx.author.id, xp_gain)

        msg = (
            f"{get_item_display(self.bot, result_name)} {ctx.author.mention} caught "
            f"**{qty} {result_name}** in **{place['name']}**\n"
            f"✨ Place Luck: **+{place['luck_bonus']}%** | Rod Luck: **+{rod_bonus}%**\n"
            f"📘 Gained **{xp_gain} XP**"
        )

        if potion_active:
            msg += "\n🧪 Luck Potion Active"

        if leveled_up:
            msg += f"\n🎉 You leveled up to **Level {new_level}**!"

        await cast.edit(content=msg)

    @commands.command()
    async def dig(self, ctx):
        profile = get_user_profile(ctx.author.id)
        if not ensure_started(profile):
            await ctx.send("❌ Use `h!startadventure` first.")
            return

        now = utc_now()
        last_dig = get_last_dig(ctx.author.id)
        cooldown = timedelta(minutes=2)

        if last_dig and now < last_dig + cooldown:
            await ctx.send(f"⏳ Dig again in **{format_remaining((last_dig + cooldown) - now)}**.")
            return

        equipped_shovel = profile["equipped_shovel"]
        if not equipped_shovel:
            await ctx.send("❌ You need a shovel equipped.")
            return

        set_last_dig(ctx.author.id, now)
        shovel_bonus = SHOVEL_LUCK.get((equipped_shovel or "").lower(), 0)

        digging = await ctx.send(
            f"⛏️ {ctx.author.mention} starts digging...\n"
            f"✨ Shovel Luck: **+{shovel_bonus}%**"
        )
        await asyncio.sleep(random.randint(2, 4))

        dig_table = get_dig_table_for_shovel(equipped_shovel)
        item_name, qty = roll_weighted(dig_table)
        add_item(ctx.author.id, item_name, qty)

        xp_gain = 5 if item_name == "trash" else 15
        new_level, current_xp, leveled_up = add_xp(ctx.author.id, xp_gain)

        msg = (
            f"{get_item_display(self.bot, item_name)} {ctx.author.mention} dug up "
            f"**{qty} {item_name.title()}**\n"
            f"✨ Shovel Luck: **+{shovel_bonus}%**\n"
            f"📘 Gained **{xp_gain} XP**"
        )

        if leveled_up:
            msg += f"\n🎉 You leveled up to **Level {new_level}**!"

        await digging.edit(content=msg)

    @commands.command()
    async def travel(self, ctx, place_id: int):
        profile = get_user_profile(ctx.author.id)
        if not ensure_started(profile):
            await ctx.send("❌ Use `h!startadventure` first.")
            return

        if place_id not in PLACES:
            await ctx.send("❌ Invalid place number. Use 1 to 5.")
            return

        place = PLACES[place_id]
        level = profile["level"]
        coins = profile["coins"]
        rod = (profile["equipped_rod"] or "").lower()

        if level < place["required_level"]:
            await ctx.send(f"❌ You need **Level {place['required_level']}**.")
            return
        if coins < place["required_coins"]:
            await ctx.send(f"❌ You need **{place['required_coins']}** coins.")
            return
        if rod != place["required_rod"]:
            await ctx.send(f"❌ You need **{place['required_rod'].title()}** equipped.")
            return

        set_current_place(ctx.author.id, place_id)
        await ctx.send(
            f"🗺️ You traveled to **{place['name']}**.\n"
            f"{place['story']}\n"
            f"✨ This place gives **+{place['luck_bonus']}% fishing luck**."
        )

    @commands.command()
    async def places(self, ctx):
        lines = []
        for pid, place in PLACES.items():
            lines.append(
                f"**{pid}. {place['name']}** — "
                f"Level {place['required_level']}, "
                f"{place['required_coins']} coins, "
                f"{place['required_rod'].title()}, "
                f"Luck **+{place['luck_bonus']}%**"
            )

        embed = discord.Embed(
            title="🗺️ Adventure Places",
            description="\n".join(lines),
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def sell(self, ctx, *, item_and_amount: str):
        parts = item_and_amount.rsplit(" ", 1)

        if len(parts) == 2 and parts[1].isdigit():
            item_name = parts[0]
            amount = int(parts[1])
        else:
            item_name = item_and_amount
            amount = 1

        item_name = item_name.strip().lower()
        if amount <= 0:
            await ctx.send("❌ Amount must be greater than 0.")
            return

        owned = get_item_amount(ctx.author.id, item_name)
        if owned < amount:
            await ctx.send(f"❌ You only have **{owned}** {item_name.title()}(s).")
            return

        sell_price = get_sell_price(item_name)
        if sell_price is None:
            await ctx.send("❌ That item cannot be sold.")
            return

        total = sell_price * amount
        if not remove_item(ctx.author.id, item_name, amount):
            await ctx.send("❌ Could not sell that item.")
            return

        add_balance(ctx.author.id, total)
        await ctx.send(
            f"💸 You sold **{amount} {get_item_display(self.bot, item_name)} {item_name.title()}** "
            f"for **{total}** coins."
        )

    @commands.command()
    async def sellall(self, ctx, *, item_name: str):
        item_name = item_name.strip().lower()
        owned = get_item_amount(ctx.author.id, item_name)

        if owned <= 0:
            await ctx.send(f"❌ You do not have any **{item_name.title()}**.")
            return

        sell_price = get_sell_price(item_name)
        if sell_price is None:
            await ctx.send("❌ That item cannot be sold.")
            return

        total = sell_price * owned
        if not remove_item(ctx.author.id, item_name, owned):
            await ctx.send("❌ Could not sell that item.")
            return

        add_balance(ctx.author.id, total)
        await ctx.send(
            f"💸 You sold **all {owned} {get_item_display(self.bot, item_name)} {item_name.title()}** "
            f"for **{total}** coins."
        )

    @commands.command()
    async def sellallfish(self, ctx):
        fish_rows = get_inventory_item_rows(ctx.author.id, FISH_NAMES)
        if not fish_rows:
            await ctx.send("❌ You have no fish to sell.")
            return

        total_coins = 0
        sold_lines = []

        for row in fish_rows:
            item_name = row["item_name"].lower()
            amount = row["amount"]
            value = FISH_SELL_PRICES[item_name] * amount
            if remove_item(ctx.author.id, item_name, amount):
                total_coins += value
                sold_lines.append(f"{amount}x {get_item_display(self.bot, item_name)} {item_name.title()} = {value} coins")

        add_balance(ctx.author.id, total_coins)
        embed = discord.Embed(
            title="🐟 Sold All Fish",
            description="\n".join(sold_lines),
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Total earned: {total_coins} coins")
        await ctx.send(embed=embed)

    @commands.command(aliases=["inv"])
    async def inventory(self, ctx):
        items = get_inventory(ctx.author.id)
        fish_lines, item_lines = [], []
        fish_total = item_total = 0

        for row in items:
            item_name = row["item_name"]
            amount = row["amount"]
            line = f"{amount}x {get_item_display(self.bot, item_name)} {item_name.title()}"
            if item_name.lower() in FISH_NAMES:
                fish_lines.append(line)
                fish_total += amount
            else:
                item_lines.append(line)
                item_total += amount

        embed = discord.Embed(
            title="Inventory",
            description="Use `h!equip rod <name>`, `h!equip shovel <name>`, `h!use`, `h!sell`, `h!sellall`, `h!sellallfish`.",
            color=discord.Color.from_rgb(43, 45, 49)
        )
        embed.set_author(name=f"{ctx.author.display_name}'s Inventory", icon_url=ctx.author.display_avatar.url)
        embed.add_field(name=f"Fishes ({fish_total})", value="\n".join(fish_lines) if fish_lines else "*No fishes*", inline=True)
        embed.add_field(name=f"Items ({item_total})", value="\n".join(item_lines) if item_lines else "*No items*", inline=True)

        chest_url = get_chest_thumbnail_url(self.bot)
        if chest_url:
            embed.set_thumbnail(url=chest_url)

        await ctx.send(embed=embed)

    @commands.command(aliases=["lb"])
    async def leaderboard(self, ctx):
        rows = get_top_coin_users(10)
        if not rows:
            await ctx.send("No coin data yet.")
            return

        lines = []
        for i, row in enumerate(rows, start=1):
            user = ctx.guild.get_member(int(row["user_id"]))
            name = user.display_name if user else f"User {row['user_id']}"
            lines.append(f"**{i}.** {name} — **{row['coins']}** coins")

        embed = discord.Embed(title="🏆 Coin Leaderboard", description="\n".join(lines), color=discord.Color.blurple())
        await ctx.send(embed=embed)

    @commands.command(aliases=["fishlb"])
    async def fishleaderboard(self, ctx):
        rows = get_top_fish_users(10)
        if not rows:
            await ctx.send("No fishing data yet.")
            return

        lines = []
        for i, row in enumerate(rows, start=1):
            user = ctx.guild.get_member(int(row["user_id"]))
            name = user.display_name if user else f"User {row['user_id']}"
            lines.append(f"**{i}.** {name} — **{row['total_fish']}** fish")

        embed = discord.Embed(title="🎣 Fish Leaderboard", description="\n".join(lines), color=discord.Color.teal())
        await ctx.send(embed=embed)

    @buy.error
    @sell.error
    @sellall.error
    @give.error
    @use.error
    @travel.error
    @equip.error
    async def item_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Missing required arguments.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument.")
        else:
            raise error


async def setup(bot):
    await bot.add_cog(Economy(bot))
