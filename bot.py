# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import copy
import logging
import os
import traceback

import discord
from discord.ext import commands
from discord_sentry_reporting import use_sentry
from dotenv import load_dotenv
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


class MyBot(commands.Bot):
    def __init__(self, command_prefix):
        super().__init__(command_prefix, help_command=None, intents=intents)

        for cog in os.listdir(currentpath + "/cogs"):
            if cog.endswith(".py"):
                try:
                    self.load_extension(f'cogs.{cog[:-3]}')
                except Exception:
                    traceback.print_exc()

    async def on_ready(self):
        print('-----')
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')
        logging.warning('rebooted')
        await bot.change_presence(activity=discord.Game(name='リアクション集計中'))

    async def on_message(self, message):
        message_contents = message.content.split('\n')

        for content in message_contents:
            message.content = content
            await bot.process_commands(message)


if __name__ == '__main__':
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(dotenv_path)

    token = os.getenv('DISCORD_BOT_TOKEN')
    dsn = os.getenv('SENTRY_DSN')

    if token is None:
        raise FileNotFoundError("Token not found error!")
    if dsn is None:
        raise FileNotFoundError("dsn not found error!")

    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s')
    logging.disable(logging.INFO)

    sentry_logging = LoggingIntegration(
        level=logging.INFO,        # Capture info and above as breadcrumbs
        event_level=logging.WARNING  # Send errors as events
    )

    currentpath = os.path.dirname(os.path.abspath(__file__))

    intents = discord.Intents.default()
    intents.members = True
    intents.typing = False

    bot = MyBot(command_prefix=commands.when_mentioned_or('/'))

    use_sentry(
        bot,
        dsn=dsn,
        integrations=[AioHttpIntegration(), sentry_logging]
    )
    bot.run(token)
