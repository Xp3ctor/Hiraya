from discord.ext import commands
import discord


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int):
        if amount <= 0:
            await ctx.send("Please enter a number greater than 0.")
            return

        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"🧹 Deleted **{len(deleted) - 1}** messages.")
        await msg.delete(delay=3)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        if member == ctx.author:
            await ctx.send("You cannot kick yourself.")
            return

        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("You cannot kick someone with an equal or higher role.")
            return

        await member.kick(reason=reason)
        await ctx.send(f"👢 Kicked **{member}** | Reason: {reason}")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        if member == ctx.author:
            await ctx.send("You cannot ban yourself.")
            return

        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("You cannot ban someone with an equal or higher role.")
            return

        await member.ban(reason=reason)
        await ctx.send(f"🔨 Banned **{member}** | Reason: {reason}")

    @kick.error
    async def kick_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use `kick`.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Usage: `h!kick @user [reason]`.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("Member not found.")

    @ban.error
    async def ban_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use `ban`.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Usage: `h!ban @user [reason]`.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("Member not found.")

    @clear.error
    async def clear_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use `clear`.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Usage: `h!clear <amount>`.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Amount must be a number.")


async def setup(bot):
    await bot.add_cog(Moderation(bot))