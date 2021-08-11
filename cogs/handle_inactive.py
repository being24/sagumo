# !/usr/bin/env python3

import asyncio
import logging
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

        # self.inavtive_loop.stop()
        # self.inavtive_loop.start()

    @commands.Cog.listener()
    async def on_ready(self):
        """on_ready時に発火する関数
        """
        await self.inactive_mng.create_table()
        await self.setting_mng.create_table()

    @commands.command(aliases=['resi_active'],
                      description='指定された役職のメンバーをDBに登録するコマンド')
    async def register_roles_watching(self, ctx, *role_or_members: typing.Union[discord.Role, discord.Member]):
        # 指定された役職とユーザーから、ユーザーのリストを作成する
        members = []
        for role_or_member in role_or_members:
            if isinstance(role_or_member, discord.Role):
                members = members + role_or_member.members
            else:
                members.append(role_or_member)

        members = list(set(members))

        # DBにdo_nothingで登録する
        print(members)

    async def check_inactive(self):
        # 非アクティブを一覧する
        pass

    async def check_active(self):
        # アクティブを一覧する
        pass

    @commands.command(aliases=['remove_active'],
                      description='指定された役職のメンバーをDBから削除するコマンド')
    async def remove_member_watching(self, ctx, member: discord.Member):
        # 指定されたメンバーをDBから削除する
        pass

    @commands.Cog.listener()
    async def on_message(self, message):
        # メッセージの送り主がDBに登録されていた場合、last_postedを更新する
        pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction: discord.Reaction, user: typing.Union[discord.Member, discord.User]):
        # リアクションの送り主がDBに登録されていた場合、last_reactを更新する

        pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, reaction: discord.Reaction, user: typing.Union[discord.Member, discord.User]):
        # リアクションの削除主がDBに登録されていた場合、last_reactを更新する

        pass

    @tasks.loop(hours=1.0)
    async def inactive_loop(self) -> None:
        # 一時間ごとにDBから非アクティブメンバーを検索して、通知する
        # 最終のリアクションとポストの現在時間との差が3ヶ月以上で、通知されていない場合は通知する
        pass

    @inactive_loop.before_loop
    async def before_printer(self):
        print('reaction waiting...')
        await self.bot.wait_until_ready()

    @inactive_loop.error
    async def error(self, arg):
        print(arg)
        logging.warning(arg)


def setup(bot):
    bot.add_cog(InactiveDetector(bot))
