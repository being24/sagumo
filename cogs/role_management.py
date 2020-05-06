# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import os

import discord
from discord.ext import commands


class RoleManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.master_path = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))

        self.json_name = self.master_path + "/data/role.json"

        self.emoji_in = '\N{THUMBS UP SIGN}'
        self.emoji_go = '\N{NEGATIVE SQUARED CROSS MARK}'

        if not os.path.isfile(self.json_name):
            self.role_dict = {}
            self.dump_json(self.role_dict)

        with open(self.json_name, encoding='utf-8') as f:
            self.role_dict = json.load(f)

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

    @commands.command(aliases=['ar'])
    @commands.has_permissions(ban_members=True)
    async def add_role(self, ctx, member: discord.Member, role: discord.Role):
        try:
            await member.add_roles(role)
            await ctx.send(f'{member.mention}に役職 : {role}を付与しました')
        except discord.Forbidden as e:
            await ctx.send(f'役職 : {role}の付与に失敗しました\n権限エラーです\n{e}')
        except discord.HTTPException as e:
            await ctx.send(f'役職 : {role}の付与に失敗しました\nhttpエラーです\n{e}')

    @commands.command(aliases=['rr'])
    @commands.has_permissions(ban_members=True)
    async def remove_role(self, ctx, member: discord.Member, role: discord.Role):
        try:
            await member.remove_roles(role)
            await ctx.send(f'{member.mention}から役職 : {role}を剥奪しました')
        except discord.Forbidden as e:
            await ctx.send(f'役職 : {role}の剥奪に失敗しました\n権限エラーです\n{e}')
        except discord.HTTPException as e:
            await ctx.send(f'役職 : {role}の剥奪に失敗しました\nhttpエラーです\n{e}')

    @commands.command(aliases=['arbr'])
    @commands.has_permissions(ban_members=True)
    async def add_role_by_reaction(self, ctx, role: discord.Role):
        # つけるのミスった時のことも考える
        embed = discord.Embed(
            title=f"role:{role.name}の付与を開始します",
            colour=0x1e90ff)
        embed.add_field(
            name=f"参加する方はリアクション{self.emoji_in}を押してください",
            value=f"{role.mention}をつけます",
            inline=True)
        embed.set_footer(text='リアクションを外すとroleが外れます')

        msg = await ctx.send(embed=embed)

        self.role_dict[str(msg.id)] = {
            "role": role.id,
            "author": ctx.author.mention,
            "url": ctx.message.jump_url}

        self.dump_json(self.role_dict)

        await msg.add_reaction(self.emoji_in)
        await msg.add_reaction(self.emoji_go)
        await asyncio.sleep(0.3)


def setup(bot):
    bot.add_cog(RoleManagement(bot))
