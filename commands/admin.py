from discord.ext import commands
import discord

from database import (
    set_balance, add_balance, add_item, remove_item,
    add_shop_item, remove_shop_item, get_item_display
)


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setcoins(self, ctx, member: discord.Member, amount: int):
        if amount < 0:
            await ctx.send("❌ Coins cannot be negative.")
            return

        set_balance(member.id, amount)
        await ctx.send(f"💰 Set **{member}** coins to **{amount}**.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addcoins(self, ctx, member: discord.Member, amount: int):
        if amount <= 0:
            await ctx.send("❌ Amount must be greater than 0.")
            return

        add_balance(member.id, amount)
        await ctx.send(f"💰 Added **{amount}** coins to **{member}**.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def giveitem(self, ctx, member: discord.Member, item_name: str, amount: int = 1):
        if amount <= 0:
            await ctx.send("❌ Amount must be greater than 0.")
            return

        add_item(member.id, item_name, amount)
        item_display = get_item_display(self.bot, item_name)
        await ctx.send(f"🎁 Gave **{amount} {item_display} {item_name.title()}** to **{member}**.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def removeitem(self, ctx, member: discord.Member, item_name: str, amount: int = 1):
        if amount <= 0:
            await ctx.send("❌ Amount must be greater than 0.")
            return

        success = remove_item(member.id, item_name, amount)
        if not success:
            await ctx.send("❌ User does not have enough of that item.")
            return

        item_display = get_item_display(self.bot, item_name)
        await ctx.send(f"🗑️ Removed **{amount} {item_display} {item_name.title()}** from **{member}**.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addshopitem(self, ctx, item_name: str, price: int, *, description: str = "No description."):
        if price < 0:
            await ctx.send("❌ Price cannot be negative.")
            return

        add_shop_item(item_name, price, description)
        item_display = get_item_display(self.bot, item_name)
        await ctx.send(f"🛒 Added/updated shop item **{item_display} {item_name.title()}** for **{price}** coins.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def removeshopitem(self, ctx, item_name: str):
        remove_shop_item(item_name)
        item_display = get_item_display(self.bot, item_name)
        await ctx.send(f"🗑️ Removed **{item_display} {item_name.title()}** from the shop.")

    @setcoins.error
    @addcoins.error
    @giveitem.error
    @removeitem.error
    @addshopitem.error
    @removeshopitem.error
    async def admin_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need administrator permission to use that command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Missing required arguments.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument type.")


async def setup(bot):
    await bot.add_cog(Admin(bot))