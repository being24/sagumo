# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import asyncio
import json
import os
import re
from datetime import datetime, timedelta

import demoji
import discord
import mojimoji as mj
from discord.ext import commands


def has_some_role():
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

        self.emoji_in = '\N{THUMBS UP SIGN}'
        self.emoji_go = '\N{NEGATIVE SQUARED CROSS MARK}'
        self.emoji_ok = '\N{WHITE HEAVY CHECK MARK}'
        self.emoji_x = '\N{CROSS MARK}'

        self.num_emoji_list = [f'{i}\ufe0f\u20e3' for i in range(10)]

        if not os.path.isfile(self.json_name):
            self.schedule_dict = {}
            self.dump_json(self.schedule_dict)

        with open(self.json_name, encoding='utf-8') as f:
            self.schedule_dict = json.load(f)

        demoji.download_codes()

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

    async def reaction_remover(self, ctx, msg, reaction, user) -> None:
        try:
            await msg.remove_reaction(reaction.emoji, user)
        except discord.Forbidden:
            await ctx.send('リアクションの除去に失敗しました.')
        except discord.NotFound:
            await ctx.send('リアクションが見つかりません.')
        except discord.HTTPException:
            await ctx.send('通信エラーです.')

    def return_reaction_to_num(self, reaction) -> int:
        num = self.num_emoji_list.index(reaction)
        return num

    @has_some_role()
    @commands.group(aliases=['reminder'], invoke_without_command=True)
    async def remind(self, ctx):
        settime = 1

        init_reaction_list = [
            self.emoji_ok,
            self.emoji_x] + self.num_emoji_list

        embed = discord.Embed(title="リマインダを設定します", colour=0x1e90ff)
        embed.add_field(
            name="対話形式でリマインダを設定します",
            value=f"無操作タイムアウトは{settime}分です\n少々お待ちください",
            inline=True)
        embed.set_footer(text='少々お待ちください')

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

        embed.clear_fields()
        embed.add_field(
            name="繰り返し回数を決定します",
            value=f"ずっと繰り返す場合は{self.num_emoji_list[0]}を、それ以外の場合は該当の回数を押してください",
            inline=True)
        embed.set_footer(text='準備完了です')
        await main_msg.edit(embed=embed)

        while True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=settime * 60)
            except asyncio.TimeoutError:
                embed = discord.Embed(title="タイムアウトしました", colour=0x1e90ff)
                await main_msg.edit(embed=embed)
                await main_msg.clear_reactions()
                break
            else:
                if user.id != ctx.author.id:
                    await self.reaction_remover(ctx, main_msg, reaction, user)
                    caution_msg = await ctx.send(f'{user.mention}:送信主のみが設定できます')
                    await self.autodel_msg(caution_msg)
                    continue

                reaction_raw = demoji.findall(str(reaction))
                for i in reaction_raw:
                    reaction_raw = i

                if reaction.emoji == self.emoji_x:
                    embed = discord.Embed(title="キャンセルしました", colour=0x1e90ff)
                    await main_msg.edit(embed=embed)
                    await main_msg.clear_reactions()
                    break

                if reaction.emoji == self.num_emoji_list[0]:
                    embed.clear_fields()
                    embed.add_field(
                        name="繰り返し回数を決定します",
                        value=f"ずっと繰り返す場合は{self.num_emoji_list[0]}を、それ以外の場合は該当の回数を押してください",
                        inline=True)
                    embed.set_footer(text='準備完了です')

                    num = self.return_reaction_to_num(reaction_raw)

                    print(num)

                await self.reaction_remover(ctx, main_msg, reaction, user)

                pass  # ここから

    @remind.error
    async def remind_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            notify_msg = await ctx.send(f'{ctx.author.mention}\n引数エラーです\n順番が間違っていませんか？')
            await self.autodel_msg(notify_msg)
        else:
            raise

    @commands.command(aliases=['ls_mi'])
    @has_some_role()
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
