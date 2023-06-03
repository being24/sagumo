import logging

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput

from .utils.common import CommonUtil


class MyModal(commands.Cog, name="Modal管理用cog"):
    """
    Modal管理
    """

    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.c = CommonUtil()

        self.logger = logging.getLogger("discord")

        self.ctx_menu = app_commands.ContextMenu(
            name="edit message",
            callback=self.edit_message,
        )
        self.bot.tree.add_command(self.ctx_menu)

    @app_commands.command(name="proxy_transmission", description="代理投稿を行うコマンド")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def proxy_transmission(self, interaction: discord.Interaction):
        """代理投稿を行うコマンド"""

        class ProxyModal(Modal, title="代理投稿を行います"):
            answer = TextInput(label="Input", style=discord.TextStyle.paragraph)

            async def on_submit(self, interaction: discord.Interaction):
                if not isinstance(interaction.channel, discord.abc.Messageable):
                    await interaction.response.send_message("テキストチャンネル限定です", ephemeral=True)
                    return
                await interaction.response.send_message("代理投稿を行いました", ephemeral=True)
                try:
                    await interaction.channel.send(self.answer.value)
                except discord.Forbidden:
                    await interaction.response.send_message("メッセージの送信に失敗しました。Forbidden", ephemeral=True)
                except discord.HTTPException:
                    await interaction.response.send_message("メッセージの送信に失敗しました。HTTPException", ephemeral=True)

        await interaction.response.send_modal(ProxyModal())

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def edit_message(self, interaction: discord.Interaction, message: discord.Message):
        if self.bot.user is None:
            self.logger.info("bot.userがNoneです")
            return

        if self.bot.user.id != message.author.id:
            await interaction.response.send_message("自分のメッセージのみ編集できます", ephemeral=True)
            return

        class EditModal(Modal, title="編集を行います"):
            answer = TextInput(label="Input", style=discord.TextStyle.paragraph, default=message.content)

            async def on_submit(self, interaction: discord.Interaction):
                if not isinstance(interaction.channel, discord.abc.Messageable):
                    await interaction.response.send_message("テキストチャンネル限定です", ephemeral=True)
                    return
                await interaction.response.send_message("投稿の編集を行いました", ephemeral=True)
                # await interaction.channel.send(self.answer.value)
                await message.edit(content=self.answer.value)

        await interaction.response.send_modal(EditModal())

    @app_commands.command(name="disposition_record")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def disposition_record(self, interaction: discord.Interaction, user: discord.User):
        """処分記録を行うコマンド

        Args:
            interaction (discord.Interaction): interaction
            user_id (int): 処分対象のユーザーID
        """
        # try:
        #     user = await self.bot.fetch_user(user_id)
        # except discord.NotFound:
        #     await interaction.response.send_message("ユーザーが見つかりませんでした", ephemeral=True)
        #     return
        if user is None:
            await interaction.response.send_message("ユーザーが見つかりませんでした", ephemeral=True)
            return

        class ProxyModal(Modal, title="処分記録を投稿します"):
            desc = TextInput(label="概要", style=discord.TextStyle.paragraph)
            corresponding_part = TextInput(label="該当箇所", style=discord.TextStyle.paragraph)
            discussion_part = TextInput(label="議論箇所", style=discord.TextStyle.paragraph)
            deal = TextInput(label="対応", style=discord.TextStyle.paragraph)

            async def on_submit(self, interaction: discord.Interaction):
                if not isinstance(interaction.channel, discord.abc.Messageable):
                    await interaction.response.send_message("テキストチャンネル限定です", ephemeral=True)
                    return

                today = discord.utils.utcnow().strftime("%Y/%m/%d")
                embed = discord.Embed(
                    title=f"{today}", description=f"desc : {self.desc.value}", color=discord.Color.red()
                )
                embed.add_field(name="・該当箇所", value=self.corresponding_part.value, inline=False)
                embed.add_field(name="・議論箇所", value=self.discussion_part.value, inline=False)
                embed.add_field(name="・対応", value=self.deal.value, inline=False)
                embed.set_author(name=f"{user.name} ID:{user.id}", icon_url=user.display_avatar)

                await interaction.channel.send(embed=embed)

                await interaction.response.send_message("処分記録を行いました", delete_after=5, ephemeral=True)

            async def on_error(self, interaction: discord.Interaction, error: Exception):
                if isinstance(error, discord.Forbidden):
                    await interaction.response.send_message("メッセージの送信に失敗しました。Forbidden", ephemeral=True)
                elif isinstance(error, discord.HTTPException):
                    await interaction.response.send_message("メッセージの送信に失敗しました。HTTPException", ephemeral=True)

        await interaction.response.send_modal(ProxyModal())

    @disposition_record.error
    async def disposition_record_error(self, interaction: discord.Interaction, error):
        if not isinstance(interaction.channel, discord.abc.Messageable):
            self.logger.info(f"{interaction.channel}はメッセージ送信できないチャンネルです{error}")
            return

        if isinstance(error, commands.CheckFailure):
            await interaction.channel.send("このコマンドを実行する権限がありません")

        await interaction.channel.send(f"エラーが発生しました。{error}")


async def setup(bot):
    await bot.add_cog(MyModal(bot))
