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

    async def judge_and_notice(self, msg_id):
        if self.reaction_dict[msg_id]["cnt"] <= self.reaction_dict[msg_id][
                "reaction_sum"] and self.reaction_dict[msg_id]["matte"] == 0:
            channel = self.bot.get_channel(
                self.reaction_dict[msg_id]["channel"])
            mention = self.reaction_dict[msg_id]["author"]
            await channel.send(f"{mention} : 規定数のリアクションがたまりました")

            self.reaction_dict.pop(msg_id, None)
            self.dump_json(self.reaction_dict)

    @commands.command(aliases=['cnt'])
    @commands.has_permissions(kick_members=True)
    async def count(self, ctx, num: typing.Optional[int] = 0):
        if num == 0:
            await ctx.send("引数を正しく入力してください")
            return

        msg = await ctx.send(f"{ctx.author.mention}\nリアクション集計を行います: 目標リアクション数 ** {num} **\n本メッセージにリアクションをつけてください")
        self.reaction_dict[msg.id] = {
            "cnt": num, "author": ctx.author.mention,
            "reaction_sum": 0, "channel": ctx.channel.id,
            "matte": 0}
        self.dump_json(self.reaction_dict)

    @commands.command(aliases=['cl'])
    @commands.has_permissions(kick_members=True)
    async def clear(self, ctx):
        self.reaction_dict = {}
        self.dump_json(self.reaction_dict)
        await ctx.send("全てのjsonデータを削除しました")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction):
        for msg_id in list(self.reaction_dict):
            if int(msg_id) == reaction.message_id:
                if "matte" in reaction.emoji.name:
                    self.reaction_dict[msg_id]["matte"] += 1
                    channel = self.bot.get_channel(reaction.channel_id)
                    msg = await channel.fetch_message(reaction.message_id)
                    await msg.edit(content=msg.content + "\n待ちます")
                else:
                    self.reaction_dict[msg_id]["reaction_sum"] += 1

                await self.judge_and_notice(msg_id)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, reaction):
        for msg_id in list(self.reaction_dict):
            if int(msg_id) == reaction.message_id:
                if "matte" in reaction.emoji.name:
                    self.reaction_dict[msg_id]["matte"] -= 1
                    channel = self.bot.get_channel(reaction.channel_id)
                    msg = await channel.fetch_message(reaction.message_id)
                    await msg.edit(content=msg.content.replace("\n待ちます", "", 1))
                else:
                    self.reaction_dict[msg_id]["reaction_sum"] -= 1

                await self.judge_and_notice(msg_id)


def setup(bot):
    bot.add_cog(reaction(bot))
