# !/usr/bin/env python3

import asyncio
import logging
import os
import typing
from datetime import datetime, timedelta

import discord
from discord.ext import commands, tasks

from .utils.common import CommonUtil
from .utils.inactive import InactiveManager
from .utils.setting_manager import SettingManager


class InactiveDetector(commands.Cog):
    """
    非アクティブを検知するcog
    """

    def __init__(self, bot):
        self.bot = bot

        self.setting_mng = SettingManager()
        self.c = CommonUtil()
        self.inactive_mng = InactiveManager()

        self.inactive_loop.stop()
        self.inactive_loop.start()

        self.notify_msg_channel = os.getenv('NOTIFY_CHANNEL_ID')

    @commands.Cog.listener()
    async def on_ready(self):
        """on_ready時に発火する関数
        """
        await self.inactive_mng.create_table()
        await self.setting_mng.create_table()

    @commands.command(aliases=['resi_active'],
                      description='指定された役職のメンバーをDBに登録するコマンド')
    async def register_roles_watching(self, ctx, *role_or_members: typing.Union[discord.Role, discord.Member]):
        """指定された役職のメンバーをDBに登録するコマンド
        """
        # 指定された役職とユーザーから、ユーザーのリストを作成する
        members = []
        for role_or_member in role_or_members:
            if isinstance(role_or_member, discord.Role):
                members = members + role_or_member.members
            else:
                members.append(role_or_member)

        # 重複除去
        members = list(set(members))

        # IDの取り出し
        members = [member.id for member in members]

        # DBにdo_nothingで登録する
        await self.inactive_mng.register_members(members)

        # 返事する
        await ctx.reply(f'{len(members)}人のメンバーを登録しました')

    @commands.command(description='アクティブ化するコマンド')
    async def activate(self, ctx, *users: discord.Member):
        """指定されたメンバーをアクティブ化する
        """
        for user in users:
            await self.inactive_mng.set_active(user.id)

        await ctx.reply(f'{len(users)}人のメンバーをアクティブ化しました')

    @commands.command(description='非アクティブ化するコマンド')
    async def inactivate(self, ctx, *users: discord.Member):
        """指定されたメンバーをアクティブ化する
        """
        for user in users:
            await self.inactive_mng.set_inactive(user.id)

        await ctx.reply(f'{len(users)}人のメンバーを非アクティブ化しました')

    @commands.command(description='アクティブメンバーの一覧を表示する関数')
    async def check_active(self, ctx):
        """アクティブメンバーの一覧を表示する関数"""
        actives = await self.inactive_mng.get_active_members()
        if actives is None:
            await ctx.reply('アクティブなメンバーはいません。そんなことある？')
            return

        embed = discord.Embed(title='アクティブメンバー一覧',
                              description=f'{len(actives)}人のメンバーがアクティブです。')

        for user_id in actives:
            user = self.bot.get_user(user_id)
            embed.add_field(name=user.name, value=user.mention)

        await ctx.reply(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.command(description='非アクティブメンバーの一覧を表示する関数')
    async def check_inactive(self, ctx):
        """非アクティブメンバーの一覧を表示する関数"""
        inactive = await self.inactive_mng.get_inactive_members()
        if inactive is None:
            await ctx.reply('非アクティブなメンバーはいません。')
            return

        embed = discord.Embed(title='非アクティブメンバー一覧',
                              description=f'{len(inactive)}人のメンバーが非アクティブです。')

        for user_id in inactive:
            user = self.bot.get_user(user_id)
            embed.add_field(name=user.name, value=user.mention)

        await ctx.reply(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.command(aliases=['remove_active'],
                      description='指定された役職のメンバーをDBから削除するコマンド')
    async def remove_member_watching(self, ctx, member: discord.Member):
        """指定されたメンバーをDBから削除するコマンド"""
        # 指定されたメンバーのIDを取得
        user_id = member.id
        # DBに存在確認
        if await self.inactive_mng.check_member(user_id):
            await self.inactive_mng.remove_member(user_id)

            # 返事する
            await ctx.reply(f'{member.name}をDBから削除しました')
        else:
            await ctx.reply(f'{member.name}はDBに存在しません')

    @commands.command(description='指定された役職のメンバーをDBから削除するコマンド')
    async def test(self, ctx):
        channel = self.bot.get_channel(self.notify_msg_channel)
        if channel is None:
            channel = self.bot.get_channel(682930390276505601)

        # 送信する
        try:
            await channel.send('embed=embed', allowed_mentions=discord.AllowedMentions.none())
        except discord.Forbidden:
            channel = self.bot.get_channel(609059625098018828)
            await channel.send('embed=embed', allowed_mentions=discord.AllowedMentions.none())


    @commands.Cog.listener()
    async def on_message(self, message):
        # メッセージの送り主がDBに登録されていた場合、last_postedを更新する
        if not await self.inactive_mng.check_member(message.author.id):
            return
        await self.inactive_mng.update_last_posted(message.author.id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction: discord.RawReactionActionEvent):
        # リアクションの送り主がDBに登録されていた場合、last_reactを更新する
        if not await self.inactive_mng.check_member(reaction.user_id):
            return
        await self.inactive_mng.update_last_react(reaction.user_id)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, reaction: discord.RawReactionActionEvent):
        # リアクションの削除主がDBに登録されていた場合、last_reactを更新する
        if not await self.inactive_mng.check_member(reaction.user_id):
            return
        await self.inactive_mng.update_last_react(reaction.user_id)

    @tasks.loop(hours=1.0)
    async def inactive_loop(self) -> None:
        # 一時間ごとにDBから非アクティブメンバーを検索して、通知する
        # 最終のリアクションとポストの現在時間との差が3ヶ月以上のアカウントを取得する
        inactive_list = await self.inactive_mng.check_period_no_work()
        if inactive_list is None:
            return

        # 埋込み型を作る
        embed = discord.Embed(
            title='非アクティブメンバー判定のメンバー一覧',
            description=f'{len(inactive_list)}人のメンバーの活動が3ヶ月以上確認されていません。')

        for user_id in inactive_list:
            user = self.bot.get_user(user_id)
            embed.add_field(name=user.name, value=user.mention)

        # 送信先を取得する
        channel = self.bot.get_channel(self.notify_msg_channel)
        if channel is None:
            channel = self.bot.get_channel(682930390276505601)

        # 送信する
        try:
            await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
        except discord.Forbidden:
            pass

        # 通知済みに設定する
        await self.inactive_mng.set_notified(inactive_list)

    @inactive_loop.before_loop
    async def before_printer(self):
        print('reaction waiting...')
        await self.bot.wait_until_ready()
        await asyncio.sleep(5)

    @inactive_loop.error
    async def error(self, arg):
        print(arg)
        logging.warning(arg)


def setup(bot):
    bot.add_cog(InactiveDetector(bot))
