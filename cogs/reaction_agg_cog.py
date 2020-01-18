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

    def dump_json(self, json_data):
        with open(self.master_path + "/data/reacrion.json", "w") as f:
            json.dump(
                json_data,
                f,
                ensure_ascii=False,
                indent=4,
                separators=(
                    ',',
                    ': '))

    @commands.command(aliases=['cnt'])
    @commands.has_permissions(kick_members=True)
    async def count(self, ctx, num: typing.Optional[int] = 0):
        if num == 0:
            await ctx.send("引数を正しく入力してください")
            return

        msg = await ctx.send(f"{ctx.author.mention}\nリアクション集計を行います : 目標リアクション数 **{num}**")
        self.reaction_dict[msg.id] = {
            "cnt": num, "author": ctx.author.mention,
            "reaction_sum": 0, "channel": ctx.channel.id,
            "matte": 0}
        self.dump_json(self.reaction_dict)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction):
        print(reaction)
        if reaction.message.author.bot is False:
            pass

        for msg_id in list(self.reaction_dict):
            if msg_id == reaction.message.id:
                if "matte" in reaction.emoji.name:
                    print("待って")

                self.reaction_dict[msg_id]["reaction_sum"] += 1

                if self.reaction_dict[msg_id]["cnt"] == self.reaction_dict[msg_id][
                        "reaction_sum"] and self.reaction_dict[msg_id]["matte"] == 0:
                    channel = self.bot.get_channel(
                        self.reaction_dict[msg_id]["channel"])
                    mention = self.reaction_dict[msg_id]["author"]
                    await channel.send(f"{mention} : 規定数のリアクションがたまりました")

                    self.reaction_dict.pop(msg_id, None)

                self.dump_json(self.reaction_dict)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, reaction):
        for msg_id in self.reaction_dict.keys():
            if msg_id == reaction.message.id:
                self.reaction_dict[msg_id]["reaction_sum"] -= 1
                self.dump_json(self.reaction_dict)

    @commands.Cog.listener()
    async def on_error(parameter_list):
        pass


def setup(bot):
    bot.add_cog(reaction(bot))
