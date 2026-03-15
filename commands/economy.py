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
    get_inventory, get_inventory_item_rows,
    get_shop_items, get_shop_item, get_sell_price,
    get_top_coin_users, get_top_fish_users, get_item_display,
    get_chest_thumbnail_url, refresh_shop_stock_if_needed,
    reduce_shop_stock, FISH_NAMES, FISH_SELL_PRICES,
    get_luck_boost_until, set_luck_boost_until
)

NORMAL_FISH_TABLE = [
    {"name": "Nothing",        "weight": 100, "quantity": (0, 0), "emoji_fallback": "🌊"},
    {"name": "Common Fish",    "weight": 300, "quantity": (2, 5), "emoji_fallback": "🐟"},
    {"name": "Uncommon Fish",  "weight": 250, "quantity": (2, 4), "emoji_fallback": "🐠"},
    {"name": "Rare Fish",      "weight": 200, "quantity": (1, 3), "emoji_fallback": "🦈"},
    {"name": "Epic Fish",      "weight": 100, "quantity": (1, 2), "emoji_fallback": "🐡"},
    {"name": "Legendary Fish", "weight": 40,  "quantity": (1, 1), "emoji_fallback": "🐉"},
    {"name": "Mythical Fish",  "weight": 10,  "quantity": (1, 1), "emoji_fallback": "✨"},
]

BOOSTED_FISH_TABLE = [
    {"name": "Nothing",        "weight": 60,  "quantity": (0, 0), "emoji_fallback": "🌊"},
    {"name": "Common Fish",    "weight": 240, "quantity": (2, 5), "emoji_fallback": "🐟"},
    {"name": "Uncommon Fish",  "weight": 260, "quantity": (2, 4), "emoji_fallback": "🐠"},
    {"name": "Rare Fish",      "weight": 240, "quantity": (1, 3), "emoji_fallback": "🦈"},
    {"name": "Epic Fish",      "weight": 140, "quantity": (1, 2), "emoji_fallback": "🐡"},
    {"name": "Legendary Fish", "weight": 50,  "quantity": (1, 1), "emoji_fallback": "🐉"},
    {"name": "Mythical Fish",  "weight": 10,  "quantity": (1, 1), "emoji_fallback": "✨"},
]


def roll_fish(use_luck_boost=False):
    fish_table = BOOSTED_FISH_TABLE if use_luck_boost else NORMAL_FISH_TABLE
    total_weight = sum(entry["weight"] for entry in fish_table)
    roll = random.randint(1, total_weight)

    current = 0
    for entry in fish_table:
        current += entry["weight"]
        if roll <= current:
            min_qty, max_qty = entry["quantity"]
            quantity = random.randint(min_qty, max_qty) if max_qty > 0 else 0
            return {
                "name": entry["name"],
                "emoji_fallback": entry["emoji_fallback"],
                "quantity": quantity
            }

    return {
        "name": "Nothing",
        "emoji_fallback": "🌊",
        "quantity": 0
    }


class ShopView(discord.ui.View):
    def __init__(self, bot, author_id, items, refreshed=False):
        super().__init__(timeout=120)
        self.bot = bot
        self.author_id = author_id
        self.items = items
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
            title="🛒 Shop",
            description=desc,
            color=discord.Color.green()
        )

        start = self.page * self.per_page
        end = start + self.per_page
        page_items = self.items[start:end]

        for row in page_items:
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
            await interaction.response.send_message("❌ This shop menu is not yours.", ephemeral=True)
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

    @commands.command(aliases=["bal", "coins", "cash"])
    async def balance(self, ctx):
        coins = get_balance(ctx.author.id)
        await ctx.send(f"💰 {ctx.author.mention}, you have **{coins}** coins.")

    @commands.command()
    async def give(self, ctx, member: discord.Member, amount: int):
        if member.bot:
            await ctx.send("❌ You cannot give coins to a bot.")
            return

        if member == ctx.author:
            await ctx.send("❌ You cannot give coins to yourself.")
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
        now = utc_now()
        last_daily = get_last_daily(ctx.author.id)
        cooldown = timedelta(hours=24)

        if last_daily and now < last_daily + cooldown:
            remaining = (last_daily + cooldown) - now
            await ctx.send(f"⏳ You already claimed daily. Come back in **{format_remaining(remaining)}**.")
            return

        reward = random.randint(150, 300)
        add_balance(ctx.author.id, reward)
        set_last_daily(ctx.author.id, now)

        await ctx.send(f"🎁 {ctx.author.mention}, you claimed **{reward}** coins from daily.")

    @commands.command()
    async def work(self, ctx):
        now = utc_now()
        last_work = get_last_work(ctx.author.id)
        cooldown = timedelta(minutes=30)

        if last_work and now < last_work + cooldown:
            remaining = (last_work + cooldown) - now
            await ctx.send(f"⏳ You are tired. Work again in **{format_remaining(remaining)}**.")
            return

        earned = random.randint(20, 80)
        add_balance(ctx.author.id, earned)
        set_last_work(ctx.author.id, now)

        await ctx.send(f"💼 {ctx.author.mention}, you worked and earned **{earned}** coins.")

    @commands.command()
    async def shop(self, ctx):
        refreshed = refresh_shop_stock_if_needed()
        items = get_shop_items()

        if not items:
            await ctx.send("🛒 The shop is empty.")
            return

        view = ShopView(self.bot, ctx.author.id, items, refreshed=refreshed)
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
            await ctx.send(
                f"❌ Not enough stock. **{item['item_name'].title()}** only has **{item['stock']}** left."
            )
            return

        total_cost = item["price"] * amount
        current_balance = get_balance(ctx.author.id)

        if current_balance < total_cost:
            await ctx.send(f"❌ You need **{total_cost}** coins, but you only have **{current_balance}**.")
            return

        stock_updated = reduce_shop_stock(item["item_name"], amount)
        if not stock_updated:
            await ctx.send("❌ Stock changed before your purchase. Try again.")
            return

        remove_balance(ctx.author.id, total_cost)
        add_item(ctx.author.id, item["item_name"], amount)

        item_display = get_item_display(self.bot, item["item_name"])
        await ctx.send(
            f"🛍️ You bought **{amount} {item_display} {item['item_name'].title()}** for **{total_cost}** coins."
        )

    @commands.command()
    async def use(self, ctx, *, item_name: str):
        item_name = item_name.strip().lower()
        owned = get_item_amount(ctx.author.id, item_name)

        if owned <= 0:
            await ctx.send(f"❌ You do not have any **{item_name.title()}**.")
            return

        if item_name == "luck potion":
            current_boost = get_luck_boost_until(ctx.author.id)
            now = utc_now()

            if current_boost and now < current_boost:
                remaining = current_boost - now
                await ctx.send(
                    f"❌ You already have an active Luck Potion. Remaining time: **{format_remaining(remaining)}**."
                )
                return

            success = remove_item(ctx.author.id, item_name, 1)
            if not success:
                await ctx.send("❌ Could not use that item.")
                return

            boost_until = now + timedelta(minutes=15)
            set_luck_boost_until(ctx.author.id, boost_until)

            await ctx.send(
                f"🧪 {ctx.author.mention} used **Luck Potion**. Better fish chances for **15 minutes**!"
            )
            return

        await ctx.send("❌ That item cannot be used right now.")

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
        success = remove_item(ctx.author.id, item_name, amount)

        if not success:
            await ctx.send("❌ Could not sell that item.")
            return

        add_balance(ctx.author.id, total)
        item_display = get_item_display(self.bot, item_name)
        await ctx.send(f"💸 You sold **{amount} {item_display} {item_name.title()}** for **{total}** coins.")

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
        success = remove_item(ctx.author.id, item_name, owned)

        if not success:
            await ctx.send("❌ Could not sell that item.")
            return

        add_balance(ctx.author.id, total)
        item_display = get_item_display(self.bot, item_name)

        await ctx.send(f"💸 You sold **all {owned} {item_display} {item_name.title()}** for **{total}** coins.")

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
            sell_price = FISH_SELL_PRICES[item_name]
            total_value = sell_price * amount

            success = remove_item(ctx.author.id, item_name, amount)
            if success:
                total_coins += total_value
                item_display = get_item_display(self.bot, item_name)
                sold_lines.append(f"{amount}x {item_display} {item_name.title()} = {total_value} coins")

        if total_coins <= 0:
            await ctx.send("❌ Could not sell your fish.")
            return

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

        fish_lines = []
        item_lines = []
        fish_total = 0
        item_total = 0

        for row in items:
            item_name = row["item_name"]
            amount = row["amount"]
            item_display = get_item_display(self.bot, item_name)

            line = f"{amount}x {item_display} {item_name.title()}"

            if item_name.lower() in FISH_NAMES:
                fish_lines.append(line)
                fish_total += amount
            else:
                item_lines.append(line)
                item_total += amount

        fish_value = "\n".join(fish_lines) if fish_lines else "*No fishes in inventory*"
        item_value = "\n".join(item_lines) if item_lines else "*No items in inventory*"

        embed = discord.Embed(
            title="Inventory",
            description="Type `h!use <item>`, `h!sell <item> [amount]`, `h!sellall <item>`, or `h!sellallfish`.",
            color=discord.Color.from_rgb(43, 45, 49)
        )

        embed.set_author(
            name=f"{ctx.author.display_name}'s Inventory",
            icon_url=ctx.author.display_avatar.url
        )

        embed.add_field(name=f"Fishes ({fish_total})", value=fish_value, inline=True)
        embed.add_field(name=f"Items ({item_total})", value=item_value, inline=True)

        chest_url = get_chest_thumbnail_url(self.bot)
        if chest_url:
            embed.set_thumbnail(url=chest_url)

        await ctx.send(embed=embed)

    @commands.command()
    async def fish(self, ctx):
        now = utc_now()
        last_fish = get_last_fish(ctx.author.id)
        cooldown = timedelta(minutes=1)

        if last_fish and now < last_fish + cooldown:
            remaining = (last_fish + cooldown) - now
            await ctx.send(f"⏳ Your fishing rod is on cooldown. Fish again in **{format_remaining(remaining)}**.")
            return

        set_last_fish(ctx.author.id, now)

        active_luck_boost = get_luck_boost_until(ctx.author.id)
        use_luck = active_luck_boost is not None and now < active_luck_boost

        wait_time = random.randint(3, 5)
        cast_message = await ctx.send(f"🎣 {ctx.author.mention} cast a line... waiting for a bite.")
        await asyncio.sleep(wait_time)

        result = roll_fish(use_luck_boost=use_luck)

        if result["name"] == "Nothing":
            if use_luck:
                await cast_message.edit(
                    content=f"🌊 {ctx.author.mention} used luck but still caught **nothing** after **{wait_time}s**."
                )
            else:
                await cast_message.edit(
                    content=f"🌊 {ctx.author.mention} waited **{wait_time}s** and caught **nothing**."
                )
            return

        add_item(ctx.author.id, result["name"], result["quantity"])

        item_display = get_item_display(self.bot, result["name"])
        extra = " 🧪(Luck Boost)" if use_luck else ""
        await cast_message.edit(
            content=(
                f"{item_display} {ctx.author.mention} waited **{wait_time}s** and caught "
                f"**{result['quantity']} {result['name']}**.{extra}"
            )
        )

    @commands.command(aliases=["lb"])
    async def leaderboard(self, ctx):
        rows = get_top_coin_users(10)

        if not rows:
            await ctx.send("No coin data yet.")
            return

        embed = discord.Embed(title="🏆 Coin Leaderboard", color=discord.Color.blurple())
        lines = []

        for i, row in enumerate(rows, start=1):
            user = ctx.guild.get_member(int(row["user_id"]))
            name = user.display_name if user else f"User {row['user_id']}"
            lines.append(f"**{i}.** {name} — **{row['coins']}** coins")

        embed.description = "\n".join(lines)
        await ctx.send(embed=embed)

    @commands.command(aliases=["fishlb"])
    async def fishleaderboard(self, ctx):
        rows = get_top_fish_users(10)

        if not rows:
            await ctx.send("No fishing data yet.")
            return

        embed = discord.Embed(title="🎣 Fish Leaderboard", color=discord.Color.teal())
        lines = []

        for i, row in enumerate(rows, start=1):
            user = ctx.guild.get_member(int(row["user_id"]))
            name = user.display_name if user else f"User {row['user_id']}"
            lines.append(f"**{i}.** {name} — **{row['total_fish']}** fish")

        embed.description = "\n".join(lines)
        await ctx.send(embed=embed)

    @buy.error
    @sell.error
    @sellall.error
    @give.error
    @use.error
    async def item_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Missing required arguments.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument.")
        else:
            raise error


async def setup(bot):
    await bot.add_cog(Economy(bot))
