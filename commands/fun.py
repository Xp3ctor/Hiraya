import random
import discord
from discord.ext import commands

EIGHT_BALL_ANSWERS = [
    "Yes.",
    "No.",
    "Maybe.",
    "Definitely.",
    "I don't think so.",
    "Without a doubt.",
    "Ask again later.",
    "Most likely.",
    "Very doubtful.",
    "It is certain."
]

MEMES = [
    "https://i.imgflip.com/30b1gx.jpg",
    "https://i.imgflip.com/1bij.jpg",
    "https://i.imgflip.com/26am.jpg",
    "https://i.imgflip.com/4t0m5.jpg",
    "https://i.imgflip.com/3si4.jpg"
]


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", aliases=["command", "commands", "helpme"])
    async def help_command(self, ctx):
        embed = discord.Embed(
            title="Bot Commands",
            description="Here are the available commands.",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Prefixes",
            value="`h!ping`, `H!ping`, `h! ping`, and `H! ping` all work.",
            inline=False
        )

        embed.add_field(
            name="Fun",
            value="`ping`\n`hello`\n`roll`\n`8ball <question>`\n`meme`\n`help` / `command`",
            inline=False
        )

        embed.add_field(
            name="Economy",
            value=(
                "`balance` / `bal` / `coins` / `cash`\n"
                "`daily`\n"
                "`work`\n"
                "`give @user <amount>`\n"
                "`shop`\n"
                "`buy <item> [amount]`\n"
                "`sell <item> [amount]`\n"
                "`sellall <item>`\n"
                "`sellallfish`\n"
                "`inventory` / `inv`\n"
                "`fish`\n"
                "`leaderboard` / `lb`\n"
                "`fishleaderboard` / `fishlb`"
            ),
            inline=True
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("🏓 Pong!")

    @commands.command()
    async def hello(self, ctx):
        await ctx.send(f"Hello, {ctx.author.mention}!")

    @commands.command()
    async def roll(self, ctx):
        number = random.randint(1, 6)
        await ctx.send(f"🎲 You rolled **{number}**")

    @commands.command(name="8ball")
    async def eight_ball(self, ctx, *, question):
        answer = random.choice(EIGHT_BALL_ANSWERS)
        await ctx.send(f"🎱 **Question:** {question}\n**Answer:** {answer}")

    @commands.command()
    async def meme(self, ctx):
        await ctx.send(random.choice(MEMES))


async def setup(bot):
    await bot.add_cog(Fun(bot))
