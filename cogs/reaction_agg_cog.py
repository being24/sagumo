# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import json
import os
import subprocess
import typing
from datetime import datetime, timedelta

import discord
from discord.ext import commands  # Bot Commands Frameworkのインポート


def has_any_role():
    async def predicate(ctx):
        if len(ctx.author.roles) > 1:
            return True
    return commands.check(predicate)


class reaction(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.master_path = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))

        self.json_name = self.master_path + "/data/reacrion.json"

        if not os.path.isfile(self.json_name):
            self.reaction_dict = {}
            self.dump_json(self.reaction_dict)

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
    @has_any_role()
    async def count(self, ctx, num: typing.Optional[int] = 0):
        if num == 0:
            await ctx.send("引数を正しく入力してください")
            return

        msg = await ctx.send(f"{ctx.author.mention}\nリアクション集計を行います: 目標リアクション数 ** {num} **\n本メッセージにリアクションをつけてください")
        today = datetime.today()
        now = (today + timedelta(minutes=num)
               ).strftime('%Y-%m-%d %H:%M:%S')
        self.reaction_dict[msg.id] = {
            "cnt": num,
            "author": ctx.author.mention,
            "reaction_sum": 0,
            "channel": ctx.channel.id,
            "matte": 0,
            "time": now,
            "url": ctx.message.jump_url}
        self.dump_json(self.reaction_dict)

    @commands.command(aliases=['ls'])
    @has_any_role()
    async def list_data(self, ctx):
        if len(self.reaction_dict) == 0:
            await ctx.send("集計中のリアクションはありません")
        else:
            embed = discord.Embed(
                title="集計中のリアクションは以下の通りです",
                description=f"{len(self.reaction_dict)}件集計中",
                color=0xffffff)

            for num, i in enumerate(self.reaction_dict):
                auth = self.reaction_dict[i]["author"]
                time = self.reaction_dict[i]["time"]
                url = self.reaction_dict[i]["url"]
                reaction_sum = self.reaction_dict[i]["reaction_sum"]
                reaction_cnt = self.reaction_dict[i]["cnt"]

                if self.reaction_dict[i]["matte"] > 0:
                    matte = " **待って！**"
                else:
                    matte = ""

                embed.add_field(
                    name=f"{num+1}番目",
                    value=f"ID : {i} by : {auth} time : {time} prog : {reaction_sum}/{reaction_cnt}{matte}\n{url}",
                    inline=False)
            embed.set_footer(text="あんまり貯めないでね")
            await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def clear_all(self, ctx):
        self.reaction_dict = {}
        self.dump_json(self.reaction_dict)
        await ctx.send("全てのjsonデータを削除しました")

    @commands.command(aliases=['rm'])
    @commands.has_permissions(ban_members=True)
    async def remove(self, ctx, num: typing.Optional[str]):
        try:
            num.replace(" ", "")
            url = self.reaction_dict[str(num)]["url"]
            del self.reaction_dict[str(num)]
            await ctx.send(f"1件削除しました\n{url}")
        except KeyError:
            await ctx.send(f"キーが存在しません")

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
