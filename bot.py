# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import codecs
import json
import os
import sys
import traceback

import discord
from discord.ext import commands


class MyBot(commands.Bot):
    def __init__(self, command_prefix):
        super().__init__(command_prefix, help_command=None)

        self.INITIAL_COGS = [
            filename[:-3] for filename in os.listdir(currentpath + "/cogs") if filename.endswith(".py")]

        for cog in self.INITIAL_COGS:
            try:
                self.load_extension(f'cogs.{cog}')
            except Exception:
                traceback.print_exc()

        with open(currentpath + "/setting.json", encoding='utf-8') as f:
            self.json_data = json.load(f)

    async def on_ready(self):
        print('-----')
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')
        await bot.change_presence(activity=discord.Game(name="リアクション集計中"))


def read_token():
    file = currentpath + "/token"
    try:
        for line in open(file, 'r'):
            temp = line.replace(" ", "").strip().split("=")
            token = temp[1]
    except FileNotFoundError:
        print("ファイルが見つかりません・・・。")
        print(sys.exc_info())
        return

    return token


if __name__ == '__main__':
    currentpath = os.path.dirname(os.path.abspath(__file__))

    token = read_token()

    bot = MyBot(command_prefix="/")
    bot.run(token)
