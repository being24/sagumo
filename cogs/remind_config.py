import logging

import discord
from discord import app_commands
from discord.ext import commands

from .utils.common import CommonUtil
from .utils.reaction_aggregation_manager import AggregationManager
from .utils.setting_manager import SettingManager

c = CommonUtil()
logger = logging.getLogger("discord")

HOUR_CHOICES = (20, 21, 22)


async def app_has_bot_manager(interaction: discord.Interaction) -> bool:
    return await c.has_bot_manager(interaction.guild, interaction.user)


class RemindHourSelect(discord.ui.Select):
    def __init__(self, guild_id: int, current_hour: int):
        self.guild_id = guild_id
        self.setting_mng = SettingManager()
        self.aggregation_mng = AggregationManager()

        options = [
            discord.SelectOption(
                label=f"{hour}時",
                value=str(hour),
                default=(hour == current_hour),
            )
            for hour in HOUR_CHOICES
        ]
        super().__init__(placeholder="リマインド時刻を選択", options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            return

        # Selectのcallbackにもコマンド実行者と同じ認可を再適用する
        # (dm_notification_config.pyのボタンcallbackには認可がなく、
        # 誰でも操作できる既知の穴があるため、それを踏襲しない)
        if not await c.has_bot_manager(interaction.guild, interaction.user):
            await interaction.response.send_message(
                "この操作を行う権限がありません", ephemeral=True
            )
            return

        await interaction.response.defer()

        new_hour = int(self.values[0])
        offset = new_hour - 21
        await self.setting_mng.set_remind_hour_offset(self.guild_id, offset)
        await self.aggregation_mng.reschedule_unfinished_by_new_hour(
            self.guild_id, new_hour, discord.utils.utcnow()
        )

        for option in self.options:
            option.default = option.value == str(new_hour)

        if interaction.message and isinstance(interaction.message, discord.Message):
            await interaction.message.edit(
                content=f"リマインド時刻を{new_hour}時に設定しました", view=self.view
            )


class RemindConfigView(discord.ui.View):
    def __init__(self, guild_id: int, current_hour: int, author_id: int):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.add_item(RemindHourSelect(guild_id, current_hour))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "このメニューはコマンド実行者のみ操作できます", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        pass


class RemindConfig(commands.Cog):
    """リマインド時刻設定用Cog"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.setting_mng = SettingManager()

    @app_commands.command(name="remind_time_config")
    @app_commands.check(app_has_bot_manager)
    @app_commands.guild_only()
    async def remind_time_config(self, interaction: discord.Interaction) -> None:
        """リアクション集計のリマインド時刻を設定するコマンド"""
        if interaction.guild is None:
            await interaction.response.send_message(
                "このコマンドはサーバー内でのみ実行できます", ephemeral=True
            )
            return

        offset = await self.setting_mng.get_remind_hour_offset(interaction.guild.id)
        current_hour = 21 + offset

        view = RemindConfigView(interaction.guild.id, current_hour, interaction.user.id)
        await interaction.response.send_message(
            f"現在のリマインド時刻: {current_hour}時\n変更する場合は選択してください",
            view=view,
        )

    @remind_time_config.error
    async def remind_time_config_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        logger.error(f"Error in remind_time_config: {error}")
        await interaction.response.send_message(
            f"エラーが発生しました: {error}", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RemindConfig(bot))
