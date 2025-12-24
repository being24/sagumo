import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from .utils.common import CommonUtil
from .utils.dm_notification_role_manager import DMNotificationRoleManager

c = CommonUtil()
logger = logging.getLogger("discord")


class DMNotificationRoleToggleButton(discord.ui.Button):
    def __init__(self, role: discord.Role, is_enabled: bool, guild_id: int):
        self.role = role
        self.is_enabled = is_enabled
        self.guild_id = guild_id
        self.dm_notification_mng = DMNotificationRoleManager()

        style = discord.ButtonStyle.red if is_enabled else discord.ButtonStyle.green
        label = f"{role.name} ({'ON' if is_enabled else 'OFF'})"

        super().__init__(
            style=style, label=label, custom_id=f"dm_toggle_{guild_id}_{role.id}"
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            return

        await interaction.response.defer()

        new_enabled = not self.is_enabled
        await self.dm_notification_mng.update_dm_notification_role(
            guild_id=self.guild_id,
            role_id=self.role.id,
            enable_dm=new_enabled,
        )

        self.is_enabled = new_enabled
        self.style = (
            discord.ButtonStyle.red if new_enabled else discord.ButtonStyle.green
        )
        self.label = f"{self.role.name} ({'ON' if new_enabled else 'OFF'})"

        if interaction.message and isinstance(interaction.message, discord.Message):
            await interaction.message.edit(view=self.view)


class DMNotificationConfigView(discord.ui.View):
    def __init__(self, guild_id: int, roles_data: list[tuple[discord.Role, bool]]):
        super().__init__(timeout=300)
        self.guild_id = guild_id

        for role, is_enabled in roles_data:
            button = DMNotificationRoleToggleButton(role, is_enabled, guild_id)
            self.add_item(button)

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True


class DMNotificationConfig(commands.Cog):
    """DM通知設定用Cog"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.dm_notification_mng = DMNotificationRoleManager()

    async def setup_hook(self):
        pass

    @app_commands.command(name="dm_notification_config")
    @app_commands.default_permissions()
    @app_commands.guild_only()
    async def dm_notification_config(self, interaction: discord.Interaction) -> None:
        """DM通知対象ロールを設定するコマンド"""
        if interaction.guild is None:
            await interaction.response.send_message(
                "このコマンドはサーバー内でのみ実行できます", ephemeral=True
            )
            return

        guild = interaction.guild
        roles = [
            r
            for r in guild.roles[1:]
            if len(r.members) < 30
            and "サイトメンバ" not in r.name
            and "bot" not in r.name.lower()
        ][:10]

        if not roles:
            await interaction.response.send_message(
                "対象のロールがありません", ephemeral=True
            )
            return

        existing_settings = await self.dm_notification_mng.get_dm_notification_roles(
            guild.id
        )
        existing_dict = {s.role_id: s.enable_dm for s in (existing_settings or [])}

        roles_data = []
        for role in roles:
            is_enabled = existing_dict.get(role.id, False)
            roles_data.append((role, is_enabled))

            if role.id not in existing_dict:
                await self.dm_notification_mng.register_dm_notification_role(
                    guild_id=guild.id,
                    role_id=role.id,
                    enable_dm=False,
                )

        view = DMNotificationConfigView(guild.id, roles_data)
        await interaction.response.send_message(
            "DM通知対象ロール設定\n緑: OFF (通知しない), 赤: ON (通知する)\nボタンを押して切り替え",
            view=view,
        )

    @dm_notification_config.error
    async def dm_notification_config_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        logger.error(f"Error in dm_notification_config: {error}")
        await interaction.response.send_message(
            f"エラーが発生しました: {error}", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DMNotificationConfig(bot))
