import asyncio
import discord
from discord.ext import commands

from config import TOKEN, PREFIXES


class HirayaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.emojis_and_stickers = True

        super().__init__(
            command_prefix=PREFIXES,
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        await self.load_extension("commands.fun")
        await self.load_extension("commands.economy")
        await self.load_extension("commands.moderation")
        await self.load_extension("commands.admin")

    async def on_ready(self):
        print(f"✅ Logged in as {self.user} ({self.user.id})")


bot = HirayaBot()
bot.run(TOKEN)