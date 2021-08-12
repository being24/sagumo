# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import discord
from discord.ext import commands

from cogs.utils.common import CommonUtil

from .utils.setting_manager import SettingManager


class NickNameManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.setting_mng = SettingManager()
        self.c = CommonUtil()

    @commands.command(aliases=['s_init'], description='沙雲の管理用役職を登録するコマンド')
    @commands.has_permissions(ban_members=True)
    async def sagumo_initialization(self, ctx, bot_manager: discord.Role, bot_user: discord.Role):
        """管理用役職:bot管理者とbot使用者を登録するコマンド、順番注意"""
        if await self.setting_mng.is_exist(ctx.guild.id):
            await self.setting_mng.update_guild(
                guild_id=ctx.guild.id,
                bot_manager_id=bot_manager.id,
                bot_user_id=bot_user.id)
            await ctx.reply(f'{ctx.guild}のbot管理者に{bot_manager.mention}を、bot操作者に{bot_user.mention}に更新しました', mention_author=False)
        else:
            await self.setting_mng.register_guild(
                guild_id=ctx.guild.id,
                bot_manager_id=bot_manager.id,
                bot_user_id=bot_user.id)
            await ctx.reply(f'{ctx.guild}のbot管理者に{bot_manager.mention}を、bot操作者に{bot_user.mention}を設定しました')

    @commands.command(aliases=['s_state'], description='沙雲の管理用役職を確認するコマンド')
    async def sagumo_status(self, ctx):
        if guild_setting := await self.setting_mng.get_guild(ctx.guild.id):
            bot_manager = self.c.return_member_or_role(
                guild=ctx.guild, id=guild_setting.bot_manager_id)
            bot_user = self.c.return_member_or_role(
                guild=ctx.guild, id=guild_setting.bot_user_id)

            await ctx.reply(f'{ctx.guild}のbot管理者は{bot_manager.mention}、bot操作者は{bot_user.mention}です', mention_author=False)

        else:
            await ctx.reply(f'{ctx.guild}のbot管理者、bot操作者は登録されていません', mention_author=False)

    @commands.command(aliases=['sync'],
                      description='沙雲の有効なサーバーでニックネームを統一するコマンド')
    async def sync_nickname(self, ctx, name: str):
        guild_ids = await self.setting_mng.get_guild_ids()
        if guild_ids is None:
            msg = await ctx.reply("沙雲の有効なサーバーはありません")
            await self.c.autodel_msg(msg=msg)
            return

        for guild_id in guild_ids:
            guild = self.bot.get_guild(guild_id)

            if guild is None:
                msg = await ctx.reply("サーバーの取得に失敗しました")
                await self.c.autodel_msg(msg=msg)
                continue

            bot_member = guild.get_member(self.bot.user.id)

            if not bot_member.guild_permissions.manage_nicknames:
                msg = await ctx.reply("ニックネームの編集権限がありません")
                await self.c.autodel_msg(msg=msg)
                return

            member = guild.get_member(ctx.author.id)

            if member is None:
                msg = await ctx.reply("メンバーの取得に失敗しました")
                await self.c.autodel_msg(msg=msg)
                return

            try:
                await member.edit(nick=name)
            except discord.Forbidden:
                msg = await ctx.reply(f"{guild}において名前変更に失敗しました、権限の位置の問題だと思われます")
                await self.c.autodel_msg(msg=msg)
                return

    @commands.command(aliases=['catalog'],
                      description='沙雲の有効なサーバーの一覧を表示するコマンド')
    async def catalog_guild(self, ctx):
        guild_ids = await self.setting_mng.get_guild_ids()

        if guild_ids is None:
            msg = await ctx.reply("沙雲の有効なサーバーはありません")
            await self.c.autodel_msg(msg=msg)
            return

        embed = discord.Embed(title="沙雲の有効なサーバーの一覧")

        for guild_id in guild_ids:
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                name = guild_id
            else:
                name = guild.name

            embed.add_field(name="サーバー名", value=name, inline=False)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(NickNameManagement(bot))