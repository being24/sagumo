# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import logging
import typing
from datetime import datetime

import discord
from discord.ext import commands, tasks
from discord.ext.menus import ListPageSource, MenuPages

from .utils.common import CommonUtil
from .utils.polling_manager import PollingManager, PollingParameter
from .utils.setting_manager import SettingManager


class Polling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.setting_mng = SettingManager()
        self.c = CommonUtil()
        self.polling_mng = PollingManager()

        self.o = '\N{HEAVY LARGE CIRCLE}'
        self.x = '\N{CROSS MARK}'
        self.num_emoji_list = [
            f'{i}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}' for i in range(10)]
        self.finish = '\N{WHITE HEAVY CHECK MARK}'

        self.polling_timer.stop()
        self.polling_timer.start()

    @commands.Cog.listener()
    async def on_ready(self):
        """on_ready時に発火する関数
        """
        await self.setting_mng.create_table()
        await self.polling_mng.create_table()

    @commands.command(description='投票を実施')
    async def poll(self, ctx, question: str, *choices_or_user_role: typing.Union[discord.Member, discord.Role, str]):
        """投票を行うコマンド.内容だけ投稿すれば賛成反対の二択に、選択肢も入れればその投票になります.\nユーザーと役職のメンションを入れるとその役職に限定できます.チェックを押すと集計します."""
        async with ctx.typing():
            if not await self.c.has_bot_user(ctx):
                return

            now = datetime.now()
            user_roles_id = []

            choices = [i for i in choices_or_user_role
                       if isinstance(i, str)]
            user_roles = [i for i in choices_or_user_role
                          if not isinstance(i, str)]

            if len(choices) == 0:
                embed = discord.Embed(title=f"{question}", color=0x37d2c0)
                embed.set_footer(
                    text=f"created_at : {now.strftime('%Y/%m/%d %H:%M')} , created_by : {ctx.author}")
                msg = await ctx.reply(embed=embed)
                await msg.add_reaction(self.o)
                await msg.add_reaction(self.x)
                await msg.add_reaction(self.finish)

            else:
                if len(choices) > 10:
                    await ctx.reply("選択肢は9個以下にしてください")
                    return

                if len(user_roles) == 0:
                    user_roles_str = "None"
                else:
                    user_roles_str = ','.join(
                        [str(user_role) for user_role in user_roles])

                content = '\n'.join([
                    f"{self.num_emoji_list[num]} {choice}" for num,
                    choice in enumerate(choices)])

                embed = discord.Embed(
                    title=f"{question}",
                    description=f"{content}",
                    color=0x37d2c0)
                embed.set_footer(
                    text=f"created_at : {now.strftime('%Y/%m/%d %H:%M')} , 対象 : {user_roles_str}")
                msg = await ctx.reply(embed=embed)

                for num in range(len(choices)):
                    await msg.add_reaction(self.num_emoji_list[num])
                await msg.add_reaction(self.finish)

            user_roles_id = [user_role.id for user_role in user_roles]

            data = PollingParameter(
                message_id=msg.id,
                author_id=ctx.author.id,
                channel_id=ctx.channel.id,
                allow_list=user_roles_id)

            await self.polling_mng.register_polling(data)

    @ commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction: discord.RawReactionActionEvent):
        if reaction.member is None or reaction.member.bot or reaction.guild_id is None:
            return
        if polling_data := await self.polling_mng.get_aggregation(reaction.message_id):
            member_role_ids = [role.id for role in reaction.member.roles]
            member_role_ids.append(reaction.user_id)
            channel = self.bot.get_channel(reaction.channel_id)

            if len(polling_data.allow_list) == 0:
                pass
            elif len(set(polling_data.allow_list) & set(member_role_ids)) == 0:
                msg = await channel.fetch_message(reaction.message_id)
                try:
                    await msg.remove_reaction(str(reaction.emoji), reaction.member)
                except discord.Forbidden:
                    await channel.send('リアクションの除去に失敗しました.')
                notify_msg = await channel.send(f"{reaction.member.mention} 権限無しのリアクションは禁止です！")
                # await self.autodel_msg(notify_msg)
                return

            msg = await channel.fetch_message(reaction.message_id)
            result = ''

            if reaction.emoji.name == self.finish and polling_data.author_id == reaction.member.id:
                for added_reaction in msg.reactions:
                    if not added_reaction.emoji == self.finish:
                        result += f"{added_reaction}:{added_reaction.count - 1}\n"

                embed = msg.embeds[0].add_field(
                    name="結果",
                    value=f"{result}",
                    inline=False)
                await msg.edit(embed=embed)
                # await msg.clear_reactions()

                await self.polling_mng.remove_aggregation(reaction.message_id)

    async def delete_expired_aggregation(self) -> None:
        """30日前から集計してる投票を削除する関数
        """
        all_aggregation = await self.polling_mng.get_all_aggregation()

        if all_aggregation is None:
            return

        now = datetime.now()

        for reaction in all_aggregation:
            elapsed_time = now - reaction.created_at
            if elapsed_time.days >= 30:
                await self.polling_mng.remove_aggregation(reaction.message_id)
                channel = self.bot.get_channel(reaction.channel_id)
                msg = await channel.fetch_message(reaction.message_id)
                await msg.clear_reactions()

    @ tasks.loop(hours=12.0)
    async def polling_timer(self) -> None:
        await self.delete_expired_aggregation()

    @polling_timer.before_loop
    async def before_printer(self):
        print('polling waiting...')
        await self.bot.wait_until_ready()

    @polling_timer.error
    async def error(self, arg):
        now = discord.utils.utcnow()
        jst_now = self.c.convert_utc_into_jst(now)
        print(jst_now, self.qualified_name, arg)
        logging.warning(arg)


def setup(bot):
    bot.add_cog(Polling(bot))
