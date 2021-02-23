# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import os
from functools import partial, wraps

import discord
from discord.ext import commands
from discord.ext.commands.core import is_owner
from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session


def async_wrap(func):
    @wraps(func)
    async def run(*args, loop=None, executor=None, **kwargs):
        if loop is None:
            loop = asyncio.get_event_loop()
        pfunc = partial(func, *args, **kwargs)
        return await loop.run_in_executor(executor, pfunc)
    return run


class DiscordTweet(commands.Cog):
    def __init__(self, bot) -> None:
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

    def log_tweet(self, ctx):
        error_content = f'tweeted\nmessage_content: {ctx.message.content}\nmessage_author : {ctx.message.author}\n{ctx.message.jump_url}'
        logging.error(error_content, exc_info=True)

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
            return 0
        else:  # 正常投稿出来なかった場合
            logging.warning("Failed. : %d" % res.status_code)
            return res.status_code

    @commands.command()
    @is_owner()
    async def tweet(self, ctx, content: str):
        # 権限チェック
        self.log_tweet(ctx)
        result = await self.async_tweet(content)
        print(result)


def setup(bot):
    bot.add_cog(DiscordTweet(bot))


"""
if __name__ == "__main__":
    DT = DiscordTweet()
    async_tweet = async_wrap(DiscordTweet.tweet)

    result = asyncio.run(async_tweet(DT, "asyncio test"))
"""
