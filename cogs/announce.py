# !/usr/bin/env python3

import discord
from discord.ext import commands

from cogs.utils.common import CommonUtil

from .utils.confirm import Confirm


class AnnounceManager(commands.Cog):
    """
    アナウンス用のcog
    """

    def __init__(self, bot):
        self.bot = bot
        self.c = CommonUtil()

    @commands.group(name='announce', description='アナウンスを行います',
                    invoke_without_command=True, hidden=True)
    @commands.has_permissions(ban_members=True)
    async def announce(self, ctx: commands.Context, message: str):
        """アナウンスを行うコマンド"""
        if ctx.invoked_subcommand is None:
            await ctx.send(message)
            notify_msg = await ctx.reply('送信しました')
            await self.c.autodel_msg(notify_msg)
            await self.c.autodel_msg(ctx.message)

    @announce.command(name='edit', description='アナウンスを編集します')
    async def announce_edit(self, ctx: commands.Context, target_id: int):
        """アナウンスを編集するコマンド"""

        # process_commandで分割しちゃってるので再取得
        raw_msg = await ctx.channel.fetch_message(ctx.message.id)
        # 内容だけ取り出す
        content = raw_msg.content[raw_msg.content.find(f'{target_id}') + len(f'{target_id}') + 1:]

        # 対象を取得
        msg = await ctx.fetch_message(target_id)

        # BOTのメッセージじゃなければ弾く
        if msg.author.id != self.bot.application_id:
            notify_msg = await ctx.reply('このメッセージは編集できません')
            await self.c.autodel_msg(notify_msg)
            return

        # 編集
        confirm = await Confirm(f'ID : {target_id}を編集しましか？').prompt(ctx)
        if confirm:
            await msg.edit(content=content)
            notify_msg = await ctx.reply(f"ID : {target_id}は{ctx.author}により編集されました")
        else:
            notify_msg = await ctx.send(f"ID : {target_id}の編集を中止しました")

        await self.c.autodel_msg(notify_msg)
        await self.c.autodel_msg(ctx.message)


def setup(bot):
    bot.add_cog(AnnounceManager(bot))
