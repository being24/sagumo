# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import time
import traceback
import typing
from datetime import datetime

import discord
import discosnow as ds
from discord.ext import commands, tasks

from .utils.common import CommonUtil
from .utils.setting_manager import SettingManager


class Admin(commands.Cog, name='管理用コマンド群'):
    """
    管理用のコマンドです
    """

    def __init__(self, bot):
        self.bot = bot
        self.c = CommonUtil()

        self.master_path = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))

        self.setting_mng = SettingManager()

        self.auto_backup.stop()
        self.auto_backup.start()

    async def cog_check(self, ctx):
        return ctx.guild and await self.bot.is_owner(ctx.author)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """on_guild_join時に発火する関数
        """
        embed = discord.Embed(
            title="サーバーに参加しました",
            description=f"SCP-JP用utility-bot {self.bot.user.display_name}",
            color=0x2fe48d)
        embed.set_author(
            name=f"{self.bot.user.name}",
            icon_url=f"{self.bot.user.avatar_url}")
        embed.add_field(
            name="Tips",
            value="はじめに `/s_init @bot管理者役職 @bot使用者役職`で各役職を登録してください",
            inline=True)
        await guild.system_channel.send(embed=embed)

    @commands.command(aliases=['re'], hidden=True)
    async def reload(self, ctx, cogname: typing.Optional[str] = "ALL"):
        if cogname == "ALL":
            reloaded_list = []
            for cog in os.listdir(self.master_path + "/cogs"):
                if cog.endswith(".py"):
                    try:
                        cog = cog[:-3]
                        self.bot.unload_extension(f'cogs.{cog}')
                        self.bot.load_extension(f'cogs.{cog}')
                        reloaded_list.append(cog)
                    except Exception:
                        traceback.print_exc()
            await ctx.reply(f"{reloaded_list}をreloadしました", mention_author=False)
        else:
            try:
                self.bot.unload_extension(f'cogs.{cogname}')
                self.bot.load_extension(f'cogs.{cogname}')
                await ctx.reply(f"{cogname}をreloadしました", mention_author=False)
            except Exception as e:
                print(e)
                await ctx.reply(e, mention_author=False)

    @commands.command(aliases=['st'], hidden=True)
    async def status(self, ctx, word: str):
        try:
            await self.bot.change_presence(activity=discord.Game(name=word))
            await ctx.reply(f"ステータスを{word}に変更しました", mention_author=False)
        except BaseException:
            pass

    @commands.command(aliases=['p'], hidden=False, description='疎通確認')
    async def ping(self, ctx):
        """Pingによる疎通確認を行うコマンド"""
        start_time = time.time()
        mes = await ctx.reply("Pinging....")
        await mes.edit(content="pong!\n" + str(round(time.time() - start_time, 3) * 1000) + "ms")

    @commands.command(aliases=['wh'], hidden=True)
    async def where(self, ctx):
        await ctx.reply("現在入っているサーバーは以下です", mention_author=False)
        server_list = [i.name.replace('\u3000', ' ')
                       for i in ctx.bot.guilds]
        await ctx.reply(f"{server_list}", mention_author=False)

    @commands.command(aliases=['mem'], hidden=True)
    async def num_of_member(self, ctx):
        await ctx.reply(f"{ctx.guild.member_count}", mention_author=False)

    @commands.command(hidden=True)
    async def back_up(self, ctx):
        SQLite_files = [
            filename for filename in os.listdir(self.master_path + "/data")
            if filename.endswith(".sqlite")]

        my_files = [discord.File(f'{self.master_path}/data/{i}')
                    for i in SQLite_files]

        await ctx.send(files=my_files)

    @commands.command(hidden=True)
    async def restore_one(self, ctx):
        if ctx.message.attachments is None:
            await ctx.send('ファイルが添付されていません')

        for attachment in ctx.message.attachments:
            await attachment.save(f"{self.master_path}/data/{attachment.filename}")
            await ctx.send(f'{attachment.filename}を追加しました')

    @commands.command(hidden=True)
    async def restore(self, ctx):
        async for message in ctx.channel.history(limit=100):
            if message.author.id == self.bot.user.id:
                if len(message.attachments) != 0:
                    attachments_name = ' '.join(
                        [i.filename for i in message.attachments])
                    msg_time = ds.snowflake2time(
                        message.id).strftime('%m-%d %H:%M')
                    await ctx.send(f'{msg_time}の{attachments_name}を取り込みます')
                    for attachment in message.attachments:
                        await attachment.save(f"{self.master_path}/data/{attachment.filename}")
                    break

    @tasks.loop(minutes=1.0)
    async def auto_backup(self):
        now = datetime.now()
        now_HM = now.strftime('%H:%M')

        if now_HM == '04:05':
            channel = self.bot.get_channel(745128369170939965)

            json_files = [
                filename for filename in os.listdir(
                    self.master_path +
                    "/data")if filename.endswith(".json")]

            sql_files = [
                filename for filename in os.listdir(
                    self.master_path +
                    "/data")if filename.endswith(".sqlite3")]

            # json_files.extend(sql_files)
            my_files = [
                discord.File(f'{self.master_path}/data/{i}')for i in sql_files]

            await channel.send(files=my_files)

    @auto_backup.before_loop
    async def before_printer(self):
        print('admin waiting...')
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Admin(bot))
