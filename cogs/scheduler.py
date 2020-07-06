# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import json
import os
import typing
from datetime import datetime, timedelta

import discord
from discord.ext import commands


def has_any_role():
    async def predicate(ctx):
        if len(ctx.author.roles) > 1:
            return True
    return commands.check(predicate)


class Scheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.master_path = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))

        self.json_name = self.master_path + "/data/scheduler.json"

        if not os.path.isfile(self.json_name):
            self.schedule_dict = {}
            self.dump_json(self.schedule_dict)

        with open(self.json_name, encoding='utf-8') as f:
            self.reaction_dict = json.load(f)

    def dump_json(self, json_data):
        with open(self.json_name, "w") as f:
            json.dump(
                json_data,
                f,
                ensure_ascii=False,
                indent=4,
                separators=(
                    ',',
                    ': '))

    @commands.command()
    @has_any_role()
    async def remind(self, ctx, num: typing.Optional[int] = 0):
        return


def setup(bot):
    bot.add_cog(Scheduler(bot))
