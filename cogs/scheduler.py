# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import asyncio
import json
import os
import re
from datetime import datetime, timedelta

import mojimoji as mj
from discord.ext import commands
import discord


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
            self.schedule_dict = json.load(f)

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

    @commands.command(aliases=['after'])
    @has_any_role()
    async def remind_after(self, ctx, text: str):
        text = mj.zen_to_han(text)

        print(re.findall(r'\d+', text))
        print(re.findall(r'[a-zA-Z]', text))
        print(datetime.now())

    @has_any_role()
    @commands.group(aliases=['every'], invoke_without_command=True)
    async def remind_every(self, ctx, text: str, content: str, *roles: discord.Role):
        # '%YY-%mm-%dd %HH:%MM'
        text = mj.zen_to_han(text)
        numbers = re.findall(r'\d+', text)
        chars = re.findall(r'[a-zA-Z]', text)

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.schedule_dict[str(ctx.message.id)] = {
            "author": ctx.author.mention,
            "channel": ctx.channel.id,
            "time": now,
            "url": ctx.message.jump_url,
            "content": content,
            "role": [i.id for i in roles]}
        self.dump_json(self.schedule_dict)
        print(numbers)
        print(chars)
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    @remind_every.command()
    async def help(self, ctx):
        await ctx.send('%YY-%mm-%dd %HH:%MM')

    @remind_every.error
    async def remind_every_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            notify_msg = await ctx.send(f'{ctx.author.mention}\n引数エラーです\n順番が間違っていませんか？')
            await asyncio.sleep(5)
            try:
                await notify_msg.delete()
            except discord.Forbidden:
                pass
        else:
            raise

    @commands.command(aliases=['ls_r'])
    @has_any_role()
    async def list_reminder(self, ctx):
        if len(self.schedule_dict) == 0:
            await ctx.send("集計中のリアクションはありません")
        else:
            embed = discord.Embed(
                title="集計中のリアクションは以下の通りです",
                description=f"{len(self.schedule_dict)}件集計中",
                color=0xffffff)

            for num, i in enumerate(self.schedule_dict):
                detail = ''
                for j in self.schedule_dict[i].keys():
                    if j == 'role':
                        detail += ' '.join(
                            [f'<@&{i}>' for i in self.schedule_dict[i]["role"]])
                    else:
                        detail += f'{j}:{self.schedule_dict[i][j]} '

                embed.add_field(
                    name=f"{num+1}番目",
                    value=f"{detail}",
                    inline=False)
            embed.set_footer(text="アセアセ…")
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Scheduler(bot))
