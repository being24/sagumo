# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import json
import os
import subprocess
import typing

import discord
from discord.ext import commands  # Bot Commands Frameworkのインポート


class reaction(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.master_path = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))

        with open(self.master_path + "/data/reacrion.json", encoding='utf-8') as f:
            self.reaction_dict = json.load(f)

        print(self.reaction_dict)
        print("Hi!")

    @commands.command(aliases=['cnt'])
    @commands.has_permissions(kick_members=True)
    async def count(self, ctx, num: typing.Optional[int] = 6):
        print(ctx.message.id)
        self.reaction_dict[ctx.message.id] = num
        with open(self.master_path + "/data/reacrion.json", "w") as f:
            json.dump(
                self.reaction_dict,
                f,
                ensure_ascii=False,
                indent=4,
                separators=(
                    ',',
                    ': '))

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        print(reaction.message.id)
        for mgs_id in self.reaction_dict.keys():
            if mgs_id is reaction.message.id:
                print("対象IDです")


def setup(bot):
    bot.add_cog(reaction(bot))
