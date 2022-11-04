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
            callback=self.react,
        )
        self.bot.tree.add_command(self.ctx_menu)

    @app_commands.command(name="proxy_transmission", description="代理投稿を行うコマンド")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def proxy_transmission(self, interaction: discord.Interaction):
        class ProxyModal(Modal, title="代理投稿を行います"):
            answer = TextInput(label="Input", style=discord.TextStyle.paragraph)

            async def on_submit(self, interaction: discord.Interaction):
                if not isinstance(interaction.channel, discord.TextChannel):
                    await interaction.response.send_message("テキストチャンネル限定です", ephemeral=True)
                    return
                await interaction.response.send_message("代理投稿を行いました", ephemeral=True)
                await interaction.channel.send(self.answer.value)

        await interaction.response.send_modal(ProxyModal())

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def react(self, interaction: discord.Interaction, message: discord.Message):
        if self.bot.user is None:
            self.logger.info("bot.userがNoneです")
            return

        if self.bot.user.id != message.author.id:
            await interaction.response.send_message("自分のメッセージのみ編集できます", ephemeral=True)
            return

        class EditModal(Modal, title="編集を行います"):
            answer = TextInput(label="Input", style=discord.TextStyle.paragraph, default=message.content)

            async def on_submit(self, interaction: discord.Interaction):
                if not isinstance(interaction.channel, discord.TextChannel):
                    await interaction.response.send_message("テキストチャンネル限定です", ephemeral=True)
                    return
                await interaction.response.send_message("投稿の編集を行いました", ephemeral=True)
                # await interaction.channel.send(self.answer.value)
                await message.edit(content=self.answer.value)

        await interaction.response.send_modal(EditModal())


async def setup(bot):
    await bot.add_cog(MyModal(bot))
