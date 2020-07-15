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

    async def autodel_msg(self, msg):
        try:
            await msg.delete(delay=5)
        except discord.Forbidden:
            pass

    @commands.command(aliases=['after'])
    @has_any_role()
    async def remind_after(self, ctx, text: str):
        text = mj.zen_to_han(text)

        print(re.findall(r'\d+', text))
        print(re.findall(r'[a-zA-Z]', text))
        print(datetime.now())

    @has_any_role()
    @commands.group(aliases=['reminder'], invoke_without_command=True)
    async def remind(self, ctx):
        settime = 3
        emoji_in = '\N{THUMBS UP SIGN}'
        emoji_go = '\N{NEGATIVE SQUARED CROSS MARK}'
        emoji_ok = '\N{WHITE HEAVY CHECK MARK}'

        num_emoji_list = [f'{i}\ufe0f\u20e3' for i in range(10)]

        init_reaction_list = [emoji_ok, ] + num_emoji_list

        embed = discord.Embed(title="リマインダを設定します", colour=0x1e90ff)
        embed.add_field(
            name="対話形式でリマインダを設定します",
            value=f"無操作タイムアウトは{settime}分です\n少々お待ちください",
            inline=True)
        embed.set_footer(text='少し待ってからリアクションをつけてください')

        main_msg = await ctx.send(embed=embed)

        for reaction in init_reaction_list:
            try:
                await main_msg.add_reaction(reaction)
            except commands.HTTPException:
                err_msg = await ctx.send('HTTPExceptionエラーです')
                await self.autodel_msg(err_msg)
            except commands.Forbidden:
                err_msg = await ctx.send('権限エラーです')
                await self.autodel_msg(err_msg)
            await asyncio.sleep(0.2)

        while True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=settime * 60)
            except asyncio.TimeoutError:
                await main_msg.delete()
                await ctx.send('タイムアウトしました')
                break
            else:
                pass # ここから

    @remind.error
    async def remind_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            notify_msg = await ctx.send(f'{ctx.author.mention}\n引数エラーです\n順番が間違っていませんか？')
            await self.autodel_msg(notify_msg)
        else:
            raise

    @commands.command(aliases=['ls_mi'])
    @has_any_role()
    async def list_reminder(self, ctx):
        if len(self.schedule_dict) == 0:
            await ctx.send("予定されたリマインダはありません")
        else:
            embed = discord.Embed(
                title="予定されたリマインダは以下の通りです",
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
