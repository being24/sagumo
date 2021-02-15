# !/usr/bin/env python3
# -*- coding: utf-8 -*-


from datetime import datetime
import typing

import discord
from discord.ext import commands, tasks
from discord.ext.menus import ListPageSource, MenuPages

from .utils.common import CommonUtil
from .utils.setting_manager import SettingManager


class Polling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.setting_mng = SettingManager()
        self.c = CommonUtil()

        self.o = '\N{HEAVY LARGE CIRCLE}'
        self.x = '\N{CROSS MARK}'
        self.num_emoji_list = [
            f'{i}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}' for i in range(10)]
        self.finish = '\N{WHITE HEAVY CHECK MARK}'

        if not self.bot.loop.is_running():
            pass
            # self.reaction_reminder.start()

    @commands.Cog.listener()
    async def on_ready(self):
        """on_ready時に発火する関数
        """
        await self.setting_mng.create_table()

    @commands.command()
    async def poll(self, ctx, question: str, *choices_or_user_role: typing.Union[discord.Member, discord.Role, str]):
        async with ctx.typing():
            if not await self.c.is_bot_user(ctx.guild, ctx.author):
                notify_msg = await ctx.send(f'{ctx.author.mention}\nコマンドの使用権限を持っていません')
                await self.c.autodel_msg(notify_msg)
                return

            now = datetime.now()

            if len(choices_or_user_role) == 0:
                embed = discord.Embed(title=f"{question}", color=0x37d2c0)
                embed.set_footer(
                    text=f"created_at : {now.strftime('%Y/%m/%d %H:%M')} , created_by : {ctx.author}")
                msg = await ctx.reply(embed=embed)
                await msg.add_reaction(self.o)
                await msg.add_reaction(self.x)
                await msg.add_reaction(self.finish)

            else:
                choices = [i for i in choices_or_user_role
                           if isinstance(i, str)]
                user_roles = [i for i in choices_or_user_role
                              if not isinstance(i, str)]

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


def setup(bot):
    bot.add_cog(Polling(bot))
