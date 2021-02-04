# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import asyncio
import typing
from datetime import datetime

import discord
from discord.ext import commands, tasks
from discord.ext.menus import ListPageSource, MenuPages

from .utils.reaction_aggregation_manager import AggregationManager
from .utils.setting_manager import SettingManager
from .utils.confirm import Confirm


def has_some_role():
    async def predicate(ctx):
        if len(ctx.author.roles) > 1:
            return True
    return commands.check(predicate)


class ReactionList(ListPageSource):
    def __init__(self, ctx, data):
        self.ctx = ctx
        super().__init__(data, per_page=10)

    @staticmethod
    def get_msgurl_from_reaction(reaction) -> str:
        """msgurlをリアクションから生成する関数

        Args:
            reaction (ReactionParameter): リアクションオブジェクト

        Returns:
            str: discordのURL
        """
        url = f'https://discord.com/channels/{reaction.guild_id}/{reaction.channel_id}/{reaction.msg_id}'
        return url

    @staticmethod
    def return_member_or_role(
            ctx, id: int) -> typing.Union[discord.Member, discord.Role]:
        """メンバーか役職オブジェクトを返す関数

        Args:
            ctx (discord.ext.commands.context.Context): いつもの
            id (int): 役職かメンバーのID

        Returns:
            typing.Union[discord.Member, discord.Role]: discord.Memberかdiscord.Role
        """
        user_or_role = ctx.guild.get_role(id)
        if user_or_role is None:
            user_or_role = ctx.guild.get_member(id)

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
                [f'{self.return_member_or_role(self.ctx, id).mention}' for id in reaction.ping_id])

            if reaction.matte:
                matte = " **待って！**"
            else:
                matte = ""

            reaction_author = self.ctx.guild.get_member(reaction.author_id)

            embed.add_field(
                name=f"{num+offset}番目",
                value=f"**ID** : {reaction.msg_id} by : {reaction_author.mention} progress : {reaction.sum}/{reaction.target_value}{matte}\n\
                    target : {target} time : {time} [link.]({url})",
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

        if not self.bot.loop.is_running():
            self.reaction_reminder.start()

    @staticmethod
    async def autodel_msg(msg: discord.Message, second: int = 5):
        """渡されたメッセージを指定秒数後に削除する関数

        Args:
            msg (discord.Message): 削除するメッセージオブジェクト
            second (int, optional): 秒数. Defaults to 5.
        """
        try:
            await msg.delete(delay=second)
        except discord.Forbidden:
            pass

    async def is_bot_user(self, guild: discord.Guild, command_user: discord.Member) -> bool:
        """そのサーバーのBOT_user役職を持っているか判定する関数

        Args:
            guild (discord.Guild): サーバーのギルドオブジェクト
            command_user (discord.Member): コマンド使用者のメンバーオブジェクト

        Returns:
            bool: 入ってたらTrue、入ってなかったらFalse

        Memo:
            管理者は使用者の権限も持つことにする
        """
        guild_DB = await self.setting_mng.get_guild(guild.id)
        bot_user_role = guild.get_role(guild_DB.bot_user_id)
        bot_manager_role = guild.get_role(guild_DB.bot_manager_id)

        if any([role in command_user.roles for role in [
               bot_manager_role, bot_user_role]]):
            return True
        else:
            return False

    async def is_bot_manager(self, guild: discord.Guild, command_user: discord.Member) -> bool:
        """そのサーバーのBOT_manager役職を持っているか判定する関数

        Args:
            guild (discord.Guild): サーバーのギルドオブジェクト
            command_user (discord.Member): コマンド使用者のメンバーオブジェクト

        Returns:
            bool: 入ってたらTrue、入ってなかったらFalse
        """
        guild_DB = await self.setting_mng.get_guild(guild.id)
        bot_manager_role = guild.get_role(guild_DB.bot_manager_id)
        if bot_manager_role in command_user.roles:
            return True
        else:
            return False

    @commands.Cog.listener()
    async def on_ready(self):
        """on_ready時に発火する関数
        """
        await self.aggregation_mng.create_table()
        await self.setting_mng.create_table()

    async def judge_and_notice(self, msg_id):
        if self.reaction_dict[msg_id]["cnt"] <= self.reaction_dict[msg_id][
                "reaction_sum"] and self.reaction_dict[msg_id]["matte"] == 0:
            channel = self.bot.get_channel(
                self.reaction_dict[msg_id]["channel"])
            mention = self.reaction_dict[msg_id]["author"]
            url = self.reaction_dict[msg_id]["url"]
            roles = self.reaction_dict[msg_id]["role"]
            roles = [channel.guild.get_role(i).name for i in roles]
            roles = ' '.join(roles)

            if len(roles) == 0:
                roles = 'None'
            else:
                roles = ' '.join(roles)

            embed = discord.Embed(title="規定数のリアクションがたまりました")
            embed.add_field(name="終了した集計のリンク", value=f"{url}", inline=False)
            embed.set_footer(text=f"対象の役職 : {roles}")

            await channel.send(f"{mention}")
            await channel.send(embed=embed)

            self.reaction_dict.pop(msg_id, None)
            # self.dump_json(self.reaction_dict)
        else:
            # self.dump_json(self.reaction_dict)
            pass

    @commands.command(aliases=['s_init'], description='沙雲の管理用役職を登録するコマンド')
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

    @commands.command(aliases=['cnt'], description='リアクション集計コマンド')
    @has_some_role()
    async def count(self, ctx, target_value: int = 0, *role_or_members: typing.Union[discord.Role, discord.Member]):
        """リアクション集計を行うコマンド"""
        if not await self.is_bot_user(ctx.guild, ctx.author):
            notify_msg = await ctx.send(f'{ctx.author.mention}\nコマンドの使用権限を持っていません')
            await self.autodel_msg(notify_msg)
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
            msg_id=msg.id,
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
        if isinstance(error, commands.BadArgument):
            notify_msg = await ctx.send(f'{ctx.author.mention}\n引数エラーです\n順番が間違っていませんか？')
            await self.autodel_msg(notify_msg)
        else:
            raise ValueError

    @ commands.command(aliases=['lsre', 'ls'], description='集計中一覧')
    async def list_reaction(self, ctx):
        """集計中のリアクション一覧を表示するコマンド"""
        if not await self.is_bot_manager(ctx.guild, ctx.author):
            notify_msg = await ctx.send(f'{ctx.author.mention}\nコマンドの使用権限を持っていません')
            await self.autodel_msg(notify_msg)
            return

        reaction_list_of_guild = await self.aggregation_mng.get_guild_list(ctx.guild.id)

        if reaction_list_of_guild is None:
            await ctx.send("集計中のリアクションはありません")
        else:
            menu = MenuPages(source=ReactionList(ctx, reaction_list_of_guild),
                             delete_message_after=True,
                             timeout=60.0)
            await menu.start(ctx)

    @ commands.command(aliases=['rm'], description='集計を中止するコマンド')
    async def remove(self, ctx, msg_id: int):
        """DBから情報を削除し、集計を中止するコマンド"""
        if not await self.is_bot_manager(ctx.guild, ctx.author):
            notify_msg = await ctx.send(f'{ctx.author.mention}\nコマンドの使用権限を持っていません')
            await self.autodel_msg(notify_msg)
            return

        if await self.aggregation_mng.is_exist(msg_id):
            confirm = await Confirm(f'ID : {msg_id}のリアクション集計を終了し、削除しますか？').prompt(ctx)
            if confirm:
                await self.aggregation_mng.remove_aggregation(msg_id)
                await ctx.reply(f"ID : {msg_id}は{ctx.author}により削除されました")
            else:
                notify_msg = await ctx.send(f"ID : {msg_id}の削除を中止しました")
                await self.autodel_msg(notify_msg)
        else:
            notify_msg = await ctx.send(f"ID : {msg_id}はリアクション集計対象ではありません")
            await self.autodel_msg(notify_msg)

    @ commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction):
        if reaction_data := await self.aggregation_mng.get_aggregation(reaction.message_id):
            msg_id = reaction.message_id

            member_role_ids = [role.id for role in reaction.member.roles]
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
                if not reaction_data.matte:
                    await self.aggregation_mng.set_value_to_matte(msg_id=msg_id, tf=True)
                    msg = await channel.fetch_message(reaction.message_id)
                    await msg.edit(content=msg.content + "\n待ちます")
            else:
                await self.aggregation_mng.set_value_to_sum(msg_id=msg_id, val=reaction_data.sum + 1)

            # await self.judge_and_notice(msg_id)

    @ commands.Cog.listener()
    async def on_raw_reaction_remove(self, reaction):
        return
        remove_usr = self.bot.get_user(reaction.user_id)
        if remove_usr.bot:
            return
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

    async def remind(self, msg_id, elapsed_time) -> None:
        if self.reaction_dict[msg_id]["matte"] > 0:
            return

        try:
            reminded = self.reaction_dict[msg_id]["reminded"]
        except KeyError:
            reminded = 0

        if reminded > 0:
            return

        channel = self.bot.get_channel(
            self.reaction_dict[msg_id]["channel"])
        url = self.reaction_dict[msg_id]["url"]
        roles = self.reaction_dict[msg_id]["role"]

        if len(roles) == 0:
            roles_mention = 'None'
            roles_name = 'None'
        else:
            roles_mention = [channel.guild.get_role(i).mention for i in roles]
            roles_mention = ' '.join(roles_mention)

            roles_name = [channel.guild.get_role(i).name for i in roles]
            roles_name = ' '.join(roles_name)

        auth = self.reaction_dict[msg_id]["author"]
        reaction_sum = self.reaction_dict[msg_id]["reaction_sum"]
        reaction_cnt = self.reaction_dict[msg_id]["cnt"]

        embed = discord.Embed(title="上記、リマインドします")
        embed.add_field(
            name="詳細",
            value=f"ID : {msg_id} by : {auth} 経過時間 : {elapsed_time} progress : {reaction_sum}/{reaction_cnt}\n{url}",
            inline=False)
        embed.set_footer(text=f"対象の役職 : {roles_name} ID : {msg_id}")

        await channel.send(f"{roles_mention}")
        await channel.send(embed=embed)

        self.reaction_dict[msg_id]['reminded'] = 1
        # self.dump_json(self.reaction_dict)

    @ tasks.loop(seconds=10.0)
    async def reaction_reminder(self) -> None:
        await self.bot.wait_until_ready()

        today = datetime.today()
        now_M = today.strftime('%M')

        if now_M == '61':
            for i in self.reaction_dict.keys():
                start_time = datetime.strptime(
                    self.reaction_dict[i]['time'], '%Y-%m-%d %H:%M:%S')
                elapsed_time = today - start_time
                if elapsed_time.days >= 3:
                    await self.remind(i, elapsed_time)

                await asyncio.sleep(0.3)


def setup(bot):
    bot.add_cog(ReactionAggregator(bot))
