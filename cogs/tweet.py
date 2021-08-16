# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import os
from datetime import datetime
from functools import partial, wraps

import discord
from discord.ext import commands, tasks
from discord.ext.menus import ListPageSource, MenuPages
from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session

from .utils.common import CommonUtil
from .utils.confirm import Confirm
from .utils.tweet_manager import TweetManager, TweetParameter


def async_wrap(func):
    @wraps(func)
    async def run(*args, loop=None, executor=None, **kwargs):
        if loop is None:
            loop = asyncio.get_event_loop()
        pfunc = partial(func, *args, **kwargs)
        return await loop.run_in_executor(executor, pfunc)
    return run


def is_in_guild():
    def predicate(ctx):
        return ctx.guild.id in [410454762522411009, 609058923353341973]
    return commands.check(predicate)


class TweetList(ListPageSource):
    def __init__(self, ctx, data):
        self.ctx = ctx
        super().__init__(data, per_page=10)

    async def write_page(self, menu, fields=[]):
        offset = (menu.current_page * self.per_page) + 1
        len_data = len(self.entries)

        embed = discord.Embed(
            title="承認待ちのツイートは以下の通りです",
            description=f"{len_data}件待機中",
            color=0x0088ff)
        embed.set_thumbnail(url=self.ctx.guild.me.avatar.replace(format="png").url)

        embed.set_footer(
            text=f"{offset:,} - {min(len_data, offset+self.per_page-1):,} of {len_data:,} records.")

        for num, tweet in enumerate(fields):
            time = tweet.created_at.strftime('%Y-%m-%d %H:%M:%S')

            tweet_author = self.ctx.guild.get_member(tweet.author_id)

            val = f"**ID** : {tweet.message_id} by : {tweet_author.mention} content : {tweet.content} time : {time})"

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


class DiscordTweet(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
        load_dotenv(dotenv_path)

        CK = os.getenv('CONSUMER_KEY')
        CS = os.getenv('CONSUMER_SECRET')
        AT = os.getenv('ACCESS_TOKEN')
        ATS = os.getenv('ACCESS_TOKEN_SECRET')

        if any([token is None for token in [CK, CS, AT, ATS]]):
            raise FileNotFoundError("API key not found error!")

        self.twitter = OAuth1Session(CK, CS, AT, ATS)

        self.url = "https://api.twitter.com/1.1/statuses/update.json"

        self.async_tweet = async_wrap(self.send_tweet)
        self.c = CommonUtil()
        self.tweet_mng = TweetManager()
        self.finish = '\N{WHITE HEAVY CHECK MARK}'

        self.tweet_timer.stop()
        self.tweet_timer.start()

    @commands.Cog.listener()
    async def on_ready(self):
        """on_ready時に発火する関数
        """
        await self.tweet_mng.create_table()

    async def start_paginating(self, ctx, reaction_list_of_guild):
        if reaction_list_of_guild is None:
            await ctx.send("集計中のリアクションはありません")
        else:
            menu = MenuPages(source=TweetList(ctx, reaction_list_of_guild),
                             delete_message_after=True,
                             timeout=60.0)
            await menu.start(ctx)

    def log_tweet(self, ctx):
        error_content = f'tweeted\nmessage_content: {ctx.message.content}\nmessage_author : {ctx.message.author}\n{ctx.message.jump_url}'
        logging.warning(error_content, exc_info=True)

    def send_tweet(self, tweet: str) -> int:
        """tweetをする関数

        Args:
            tweet (str): 内容

        Returns:
            bool: 成否
        """
        params = {"status": tweet}

        res = self.twitter.post(self.url, params=params)  # post送信

        if res.status_code == 200:  # 正常投稿出来た場合
            return 200
        else:  # 正常投稿出来なかった場合
            return res.status_code

    @commands.command(description='ツイートを実施')
    @is_in_guild()
    async def tweet(self, ctx, content: str):
        """ツイートを行うコマンド、管理者の1名以上の承認で投稿されます"""
        if not await self.c.has_bot_manager(ctx):
            return

        self.log_tweet(ctx)

        now = datetime.now()

        embed = discord.Embed(
            title="ツイートを行います",
            description="管理者1名のリアクションで投稿します",
            color=0x37d2c0)
        embed.add_field(
            name="内容",
            value=f"{content}",
            inline=True)
        embed.set_footer(
            text=f"created_at : {now.strftime('%Y/%m/%d %H:%M')}")
        msg = await ctx.reply(embed=embed)
        await msg.add_reaction(self.finish)

        data = TweetParameter(
            message_id=msg.id,
            author_id=ctx.author.id,
            channel_id=ctx.channel.id,
            content=content)

        await self.tweet_mng.register_tweetdata(data)

    @commands.command(description='承認待ちを中止')
    @is_in_guild()
    async def remove_tweet(self, ctx, message_id: int):
        """DBから情報を削除し、承認待ちを中止するコマンド"""
        if not await self.c.has_bot_user(ctx):
            return

        if await self.tweet_mng.is_exist(message_id):
            confirm = await Confirm(f'ID : {message_id}の承認待ちを終了し、削除しますか？').prompt(ctx)
            if confirm:
                await self.tweet_mng.remove_tweetdata(message_id)
                await ctx.reply(f"ID : {message_id}は{ctx.author}により削除されました")
            else:
                notify_msg = await ctx.send(f"ID : {message_id}の削除を中止しました")
                await self.c.autodel_msg(notify_msg)
        else:
            notify_msg = await ctx.send(f"ID : {message_id}は待機していません")
            await self.c.autodel_msg(notify_msg)

    @ commands.command(aliases=['lstw', 'lst'],
                       description='待機中のツイート一覧', invoke_without_command=True)
    async def list_tweet(self, ctx):
        """待機中のツイートを表示するコマンド"""
        if not await self.c.has_bot_manager(ctx):
            return

        reaction_list_of_guild = await self.tweet_mng.get_all_tweetdata()

        if reaction_list_of_guild is None:
            await ctx.send("集計中のリアクションはありません")
            return

        if len(reaction_list_of_guild) == 0:
            await ctx.send("集計中のリアクションはありません")
            return

        await self.start_paginating(ctx, reaction_list_of_guild)

    async def delete_expired_tweet(self) -> None:
        """30日前から待機中のツイートを削除する関数
        """
        all_aggregation = await self.tweet_mng.get_all_tweetdata()

        if all_aggregation is None:
            return

        now = datetime.now()

        for reaction in all_aggregation:
            elapsed_time = now - reaction.created_at
            if elapsed_time.days >= 30:
                await self.tweet_mng.remove_tweetdata(reaction.message_id)
                channel = self.bot.get_channel(reaction.channel_id)
                if isinstance(channel, discord.Thread):
                    if channel.archived:
                        return
                msg = await channel.fetch_message(reaction.message_id)
                await msg.clear_reactions()

    @ commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction: discord.RawReactionActionEvent):
        if reaction.member is None:
            return

        if reaction.member.bot:
            return

        if reaction.guild_id is None:
            return

        if tweet_data := await self.tweet_mng.get_tweetdata(reaction.message_id):

            main_guild = self.bot.get_guild(410454762522411009)
            main_guild = self.bot.get_guild(609058923353341973)

            admin_role = discord.utils.get(
                main_guild.roles, name='サイト管理者')

            member_role_ids = [role.id for role in reaction.member.roles]
            member_role_ids.append(reaction.user_id)
            channel = self.bot.get_channel(reaction.channel_id)
            msg = await channel.fetch_message(reaction.message_id)

            if admin_role not in reaction.member.roles:
                try:
                    await msg.remove_reaction(str(reaction.emoji), reaction.member)
                except discord.Forbidden:
                    await channel.send('リアクションの除去に失敗しました.')
                notify_msg = await channel.send(f"{reaction.member.mention} 権限無しのリアクションは禁止です！")
                # await self.autodel_msg(notify_msg)
                return

            now = datetime.now()

            if reaction.emoji.name == self.finish:
                result = await self.async_tweet(tweet_data.content)
                if result != 200:
                    await msg.reply(f'ツイートに失敗しました\nerror_code : {result}')
                else:
                    embed = msg.embeds[0]
                    embed.add_field(
                        name="ツイートしました",
                        value=f"内容 : {tweet_data.content}",
                        inline=False)
                    embed.add_field(
                        name="ツイート日時",
                        value=f"{now.strftime('%Y/%m/%d %H:%M')}",
                        inline=False)
                    await msg.edit(embed=embed)
                    await msg.clear_reactions()

                    await self.tweet_mng.remove_tweetdata(reaction.message_id)

    @ tasks.loop(hours=12.0)
    async def tweet_timer(self) -> None:
        await self.delete_expired_tweet()

    @tweet_timer.before_loop
    async def before_printer(self):
        print('tweet waiting...')
        await self.bot.wait_until_ready()

    @tweet_timer.error
    async def error(self, arg):
        print(arg)
        logging.warning(arg)


def setup(bot):
    bot.add_cog(DiscordTweet(bot))


"""
if __name__ == "__main__":
    DT = DiscordTweet()
    async_tweet = async_wrap(DiscordTweet.tweet)

    result = asyncio.run(async_tweet(DT, "asyncio test"))
"""
