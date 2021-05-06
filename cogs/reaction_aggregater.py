# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import asyncio
import logging
import typing
from datetime import datetime, timedelta

import discord
from discord.ext import commands, tasks
from discord.ext.commands.errors import (BadArgument, BadUnionArgument,
                                         CommandInvokeError)
from discord.ext.menus import ListPageSource, MenuPages
from sqlalchemy.sql.elements import Null

from .utils.common import CommonUtil
from .utils.confirm import Confirm
from .utils.reaction_aggregation_manager import (AggregationManager,
                                                 ReactionParameter)
from .utils.setting_manager import SettingManager


class ReactionList(ListPageSource):
    def __init__(self, ctx, data):
        self.ctx = ctx
        super().__init__(data, per_page=10)

    @staticmethod
    def get_msgurl_from_reaction(reaction: ReactionParameter) -> str:
        """msgurlをリアクションから生成する関数

        Args:
            reaction (ReactionParameter): リアクションオブジェクト

        Returns:
            str: discordのURL
        """
        url = f'https://discord.com/channels/{reaction.guild_id}/{reaction.channel_id}/{reaction.message_id}'
        return url

    @staticmethod
    def return_member_or_role(guild: discord.Guild,
                              id: int) -> typing.Union[discord.Member,
                                                       discord.Role,
                                                       None]:
        """メンバーか役職オブジェクトを返す関数

        Args:
            guild (discord.guild): discordのguildオブジェクト
            id (int): 役職かメンバーのID

        Returns:
            typing.Union[discord.Member, discord.Role]: discord.Memberかdiscord.Role
        """
        user_or_role = guild.get_role(id)
        if user_or_role is None:
            user_or_role = guild.get_member(id)

        return user_or_role

    async def write_page(self, menu, fields=[]):
        offset = (menu.current_page * self.per_page) + 1
        len_data = len(self.entries)

        embed = discord.Embed(
            title="集計中のリアクションは以下の通りです",
            description=f"本サーバーでは{len_data}件集計中",
            color=0x0088ff)
        embed.set_thumbnail(url=self.ctx.guild.me.avatar_url)

        embed.set_footer(
            text=f"{offset:,} - {min(len_data, offset+self.per_page-1):,} of {len_data:,} records.")

        for num, reaction in enumerate(fields):
            time = reaction.created_at.strftime('%Y-%m-%d %H:%M:%S')

            url = self.get_msgurl_from_reaction(reaction)

            target = ' '.join(
                [f'{self.return_member_or_role(self.ctx.guild, id).mention}' for id in reaction.ping_id])

            if reaction.matte:
                matte = " **待って！**"
            else:
                matte = ""

            reaction_author = self.ctx.guild.get_member(reaction.author_id)

            if target == "":
                val = f"**ID** : {reaction.message_id} by : {reaction_author.mention} progress : {reaction.sum}/{reaction.target_value}{matte}\ntime : {time} [link.]({url})"
            else:
                val = f"**ID** : {reaction.message_id} by : {reaction_author.mention} progress : {reaction.sum}/{reaction.target_value}{matte}\ntarget: {target} time : {time} [link.]({url})"

            embed.add_field(
                name=f"{num+offset}番目",
                value=f"{val}",
                inline=False)

        return embed

    async def format_page(self, menu, entries):
        '''
        fields = []

        for entry in entries:
            fields.append((entry.brief, syntax(entry)))
        '''
        return await self.write_page(menu, entries)


class ReactionAggregator(commands.Cog):
    """
    リアクション集計のカテゴリ
    """

    def __init__(self, bot):
        self.bot = bot

        self.setting_mng = SettingManager()
        self.aggregation_mng = AggregationManager()
        self.c = CommonUtil()

        self.reaction_reminder.stop()
        self.reaction_reminder.start()

    async def start_paginating(self, ctx, reaction_list_of_guild):
        if reaction_list_of_guild is None:
            await ctx.send("集計中のリアクションはありません")
        else:
            menu = MenuPages(source=ReactionList(ctx, reaction_list_of_guild),
                             delete_message_after=True,
                             timeout=60.0)
            await menu.start(ctx)

    async def change_delete_msg(self, channel_id: int, message_id: int) -> None:
        """集計終了時元メッセージを変更する関数

        Args:
            channel_id (int): チャンネルID
            message_id (int): メッセージID
        """
        channel = self.bot.get_channel(channel_id)
        try:
            msg = await channel.fetch_message(message_id)
            await msg.clear_reactions()
            await msg.edit(content="集計終了しました")
        except discord.Forbidden:
            pass
        except discord.NotFound:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        """on_ready時に発火する関数
        """
        await self.aggregation_mng.create_table()
        await self.setting_mng.create_table()

    async def judge_and_notice(self, message_id: int):
        reaction_data = await self.aggregation_mng.get_aggregation(message_id)
        if reaction_data is None:
            return

        if reaction_data.target_value == reaction_data.sum and reaction_data.matte == 0:
            channel = self.bot.get_channel(reaction_data.channel_id)
            guild = self.bot.get_guild(reaction_data.guild_id)
            command_msg = await channel.fetch_message(reaction_data.command_id)

            url = self.c.get_msgurl_from_reaction(reaction_data)

            roles = [
                self.c.return_member_or_role(guild, id).name
                for id in reaction_data.ping_id]

            if len(roles) == 0:
                roles = 'None'
            else:
                roles = ' '.join(roles)

            now = datetime.now()

            await self.aggregation_mng.set_value_to_notified(reaction_data.message_id, now)

            embed = discord.Embed(title="規定数のリアクションがたまりました")
            embed.add_field(name="終了した集計のリンク", value=f"{url}", inline=False)
            embed.add_field(
                name="集計完了時間",
                value=f"{now.strftime('%Y-%m-%d %H:%M:%S')}",
                inline=False)
            embed.set_footer(text=f"target : {roles}")

            await command_msg.reply(embed=embed)

            msg = await channel.fetch_message(reaction_data.message_id)
            await msg.edit(content=msg.content + "\n\t終了しました")

        elif reaction_data.notified_at is not Null and reaction_data.target_value > reaction_data.sum:
            channel = self.bot.get_channel(reaction_data.channel_id)
            msg = await channel.fetch_message(reaction_data.message_id)
            await msg.edit(content=msg.content.replace("\n\t終了しました", ""))

    @commands.command(aliases=['cnt'], description='リアクション集計コマンド')
    async def count(self, ctx, target_value: int = 0, *role_or_members: typing.Union[discord.Role, discord.Member]):
        """リアクション集計を行うコマンド"""
        if not await self.c.has_bot_user(ctx):
            return

        if target_value == 0:
            await ctx.send("引数を正しく入力してください")
            return

        if len(role_or_members) == 0:
            insert_roles_id = []
        else:
            insert_roles_id = [
                role_or_member.id for role_or_member in role_or_members]

        first_msg = f"リアクション集計を行います: 目標リアクション数 : **{target_value}**"

        if len(insert_roles_id) > 0:
            mid_msg = f"指定された役職/ユーザー : {' '.join([role_or_member.name for role_or_member in role_or_members])}\n"
        else:
            mid_msg = ""

        insert_roles_str = ','.join([str(id) for id in insert_roles_id])

        last_msg = "本メッセージにリアクションをつけてください"

        msg = await ctx.reply(f"{first_msg}\n{mid_msg}{last_msg}")

        now = datetime.now()

        await self.aggregation_mng.register_aggregation(
            message_id=msg.id,
            command_id=ctx.message.id,
            guild_id=ctx.guild.id,
            channel_id=ctx.channel.id,
            target_value=target_value,
            author_id=ctx.author.id,
            created_at=now,
            ping_id=insert_roles_str)

    @ count.error
    async def count_error(self, ctx, error):
        """カウント関数専用のエラーハンドラ

        Args:
            ctx (discord.ext.commands.context.Context): いつもの
            error (discord.ext.commands.CommandError): エラーの内容

        Raises:
            ValueError: なんでValueError出すのこれ
        """
        if isinstance(error, (BadArgument, BadUnionArgument)):
            notify_msg = await ctx.send(f'{ctx.author.mention}\n引数エラーです\n順番が間違っていませんか？')
            await self.c.autodel_msg(notify_msg)
        elif isinstance(error, CommandInvokeError):
            raise ValueError

    @ commands.group(aliases=['lsre', 'ls'],
                     description='集計中一覧', invoke_without_command=True)
    async def list_reaction(self, ctx):
        """集計中のリアクション一覧を表示するコマンド"""
        if not await self.c.has_bot_manager(ctx):
            return

        reaction_list_of_guild = await self.aggregation_mng.get_guild_list(ctx.guild.id)

        if reaction_list_of_guild is None:
            await ctx.send("集計中のリアクションはありません")
            return

        reaction_list_of_guild = [
            reaction for reaction in reaction_list_of_guild if reaction.notified_at is None]

        if len(reaction_list_of_guild) == 0:
            await ctx.send("集計中のリアクションはありません")
            return

        await self.start_paginating(ctx, reaction_list_of_guild)

    @list_reaction.command(description='現在DB上にある集計一覧を出力')
    async def all(self, ctx):
        """集計中のすべてのリアクション一覧を表示するコマンド"""
        if not await self.c.has_bot_manager(ctx):
            return

        reaction_list_of_guild = await self.aggregation_mng.get_guild_list(ctx.guild.id)
        await self.start_paginating(ctx, reaction_list_of_guild)

    @ commands.command(aliases=['rm'], description='集計を中止するコマンド')
    async def remove(self, ctx, message_id: int):
        """DBから情報を削除し、集計を中止するコマンド"""
        if not await self.c.has_bot_user(ctx):
            return

        if await self.aggregation_mng.is_exist(message_id):
            confirm = await Confirm(f'ID : {message_id}のリアクション集計を終了し、削除しますか？').prompt(ctx)
            if confirm:
                await self.aggregation_mng.remove_aggregation(message_id)
                await ctx.reply(f"ID : {message_id}は{ctx.author}により削除されました")
                await self.change_delete_msg(ctx.channel.id, message_id)
            else:
                notify_msg = await ctx.send(f"ID : {message_id}の削除を中止しました")
                await self.c.autodel_msg(notify_msg)
        else:
            notify_msg = await ctx.send(f"ID : {message_id}はリアクション集計対象ではありません")
            await self.c.autodel_msg(notify_msg)

    @ commands.command(aliases=['add_role'],
                       description='特定の役職持ちに特定のリアクションを付与するコマンド')
    async def add_role_for_init(self, ctx, add_role: discord.Role, *has_role: discord.Role):
        """bot管理者つけるために特定の役職持ちに役職を付与するコマンド"""
        if not await self.c.has_bot_manager(ctx):
            return
        target_members = []
        for role in has_role:
            temp_members = [
                member for member in ctx.guild.members if role in member.roles]
            target_members.extend(temp_members)

        target_members = list(set(target_members))

        for member in target_members:
            try:
                await member.add_roles(add_role, reason=f"{ctx.me}による自動付与")
                msg = await ctx.reply(f"{member}へ{add_role}を付与しました")
                await self.c.autodel_msg(msg)
                await asyncio.sleep(0.3)
            except discord.Forbidden:
                msg = await ctx.reply(f"{member}への{add_role}に失敗しました。権限不足です")
                await self.c.autodel_msg(msg)
            except BaseException as e:
                msg = await ctx.reply(f"{member}への{add_role}に失敗しました。{e}")
                await self.c.autodel_msg(msg, second=10)

        await ctx.reply('完了しました')

    @ commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction):
        """リアクションが追加されたときに、集計対象メッセージであれば+1する関数

        Args:
            reaction (discord.Reaction): reactionオブジェクト
        """
        if reaction.member is None or reaction.member.bot or reaction.guild_id is None:
            return
        if reaction_data := await self.aggregation_mng.get_aggregation(reaction.message_id):
            message_id = reaction.message_id

            member_role_ids = [role.id for role in reaction.member.roles]
            member_role_ids.append(reaction.user_id)
            channel = self.bot.get_channel(reaction.channel_id)

            if len(reaction_data.ping_id) == 0:
                pass
            elif len(set(reaction_data.ping_id) & set(member_role_ids)) == 0:
                msg = await channel.fetch_message(reaction.message_id)
                try:
                    await msg.remove_reaction(str(reaction.emoji), reaction.member)
                except discord.Forbidden:
                    await channel.send('リアクションの除去に失敗しました.')
                notify_msg = await channel.send(f"{reaction.member.mention} 権限無しのリアクションは禁止です！")
                # await self.autodel_msg(notify_msg)
                return

            if "matte" in reaction.emoji.name:
                await self.aggregation_mng.set_value_to_matte(message_id=message_id, val=reaction_data.matte + 1)
                msg = await channel.fetch_message(reaction.message_id)
                await msg.edit(content=msg.content + "\n待ちます")
            else:
                await self.aggregation_mng.set_value_to_sum(message_id=message_id, val=reaction_data.sum + 1)

            await self.judge_and_notice(message_id)

    @ commands.Cog.listener()
    async def on_raw_reaction_remove(self, reaction):
        """リアクションが除去されたときに、集計対象メッセージであれば-1する関数

        Args:
            reaction (discord.Reaction): reactionオブジェクト
        """
        if reaction.member is None or reaction.member.bot or reaction.guild_id is None:
            return

        if reaction_data := await self.aggregation_mng.get_aggregation(reaction.message_id):
            message_id = reaction.message_id
            guild = self.bot.get_guild(reaction_data.guild_id)
            remove_usr = guild.get_member(reaction.user_id)

            channel = self.bot.get_channel(reaction.channel_id)

            member_role_ids = [role.id for role in remove_usr.roles]
            member_role_ids.append(reaction.user_id)

            if len(set(reaction_data.ping_id) & set(member_role_ids)) == 0:
                return

            if "matte" in reaction.emoji.name:
                await self.aggregation_mng.set_value_to_matte(message_id=message_id, val=reaction_data.matte - 1)
                msg = await channel.fetch_message(reaction.message_id)
                await msg.edit(content=msg.content.replace("\n待ちます", "", 1))
            else:
                await self.aggregation_mng.unset_value_to_notified(message_id=message_id)
                await self.aggregation_mng.set_value_to_sum(message_id=message_id, val=reaction_data.sum - 1)

            await self.judge_and_notice(message_id)

    async def delete_notified(self) -> None:
        """リアクション集計が終了してから3日以上たった時に削除する関数
        """
        notified_aggregation = await self.aggregation_mng.get_notified_aggregation()

        if notified_aggregation is None:
            return

        now = datetime.now()

        for reaction in notified_aggregation:
            elapsed_time = now - reaction.notified_at
            if elapsed_time.days >= 3:
                await self.aggregation_mng.remove_aggregation(reaction.message_id)
                await self.change_delete_msg(reaction.channel_id, reaction.message_id)

    async def remind(self) -> None:
        """リマインドを行う関数"""

        # 12h, 24h, 以後24h間隔が個人的には理想です

        all_aggregation = await self.aggregation_mng.get_all_aggregation()

        if all_aggregation is None:
            return

        now = datetime.now()

        for reaction in all_aggregation:
            if reaction.sum >= reaction.target_value:
                continue

            elapsed_time = now - reaction.created_at
            if reaction.remind == "" or reaction.remind is None:  # 要修正
                if elapsed_time.total_seconds() >= 12 * 3600:
                    await self.send_remind(reaction, elapsed_time.days, elapsed_time)
            else:
                if elapsed_time.days != reaction.remind:
                    await self.send_remind(reaction, reaction.remind + 1, elapsed_time)

    async def send_remind(self, reaction: ReactionParameter, val: int, elapsed_time: timedelta) -> None:
        """リマインドを送信する関数

        Args:
            reaction (ReactionParameter): リアクション集計
        """
        channel = self.bot.get_channel(reaction.channel_id)
        url = self.c.get_msgurl_from_reaction(reaction)
        guild = self.bot.get_guild(reaction.guild_id)
        roles = [
            self.c.return_member_or_role(
                guild, id) for id in reaction.ping_id]
        if len(roles) == 0:
            roles_mention = 'None'
            roles_name = 'None'
        else:
            roles_mention = ' '.join(
                [member.mention for member in roles])
            roles_name = ' '.join([member.name for member in roles])

        auth = self.c.return_member_or_role(guild, reaction.author_id)
        reaction_sum = reaction.sum
        reaction_cnt = reaction.target_value

        days = elapsed_time.days
        minutes, seconds = divmod(elapsed_time.seconds, 60)
        hours, minutes = divmod(minutes, 60)
        embed = discord.Embed(title="リマインドします")
        embed.add_field(
            name="詳細",
            value=f"ID : {reaction.message_id} by : {auth}\nprogress : {reaction_sum}/{reaction_cnt} [link.]({url})",
            inline=False)
        embed.set_footer(
            text=f"対象 : {roles_name} 経過時間 : {days} days, {hours} hours {minutes} minutes")
        if roles_mention != "None":
            await channel.send(f"{roles_mention}")
        await channel.send(embed=embed)
        await self.aggregation_mng.set_value_to_remind(reaction.message_id, val)
        await asyncio.sleep(0.3)

    async def delete_expired_aggregation(self) -> None:
        """14日前から集計してる集計を削除する関数
        """
        all_aggregation = await self.aggregation_mng.get_all_aggregation()

        if all_aggregation is None:
            return

        now = datetime.now()

        for reaction in all_aggregation:
            elapsed_time = now - reaction.created_at
            if elapsed_time.days >= 14:
                await self.aggregation_mng.remove_aggregation(reaction.message_id)
                await self.change_delete_msg(reaction.channel_id, reaction.message_id)

    @ tasks.loop(minutes=1.0)
    async def reaction_reminder(self) -> None:
        await self.delete_notified()
        await self.remind()

    @reaction_reminder.before_loop
    async def before_printer(self):
        print('reaction waiting...')
        await self.bot.wait_until_ready()

    @reaction_reminder.error
    async def error(self, arg):
        print(arg)
        logging.warning(arg)


def setup(bot):
    bot.add_cog(ReactionAggregator(bot))
