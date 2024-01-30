import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks
from zoneinfo import ZoneInfo

from .utils.common import CommonUtil
from .utils.polling_manager import PollingManager, PollingParameter
from .utils.setting_manager import SettingManager

c = CommonUtil()
logger = logging.getLogger("discord")
polling_mng = PollingManager()

num_emoji_list = [
    f"{i}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}" for i in range(10)
]
finish = "\N{WHITE HEAVY CHECK MARK}"


class NotSameUserError(Exception):
    """Interactionの実行者とappコマンドの実行者が異なる場合のエラー"""

    pass


class Select(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(
            placeholder="対象を選択してください", min_values=0, max_values=25
        )

    async def callback(self, interaction: discord.Interaction):
        if self.view is None:
            return
        # select menuを無効にする
        for item in self.view.children:
            item.disabled = True
        await self.view.message.edit(view=self.view)

        if isinstance(interaction.message, discord.Message):
            await c.delete_after(interaction.message)

        now = discord.utils.utcnow()
        poll_time_stamp = f"<t:{int(now.timestamp())}:f>"

        role_names = [role.name for role in self.values]
        role_names = ", ".join(role_names)

        content = "\n".join(
            f"{num_emoji_list[num]} : {option}" for num, option in enumerate(options)
        )

        embed = discord.Embed(title=f"{question_}", description=content, color=0x37D2C0)
        embed.set_footer(text=f"対象 : {role_names}")
        embed.add_field(name="投票開始", value=f"{poll_time_stamp}", inline=False)

        await interaction.response.send_message(
            embed=embed,
            allowed_mentions=discord.AllowedMentions(
                everyone=False, users=False, roles=True, replied_user=False
            ),
        )

        msg = await interaction.original_response()

        for num in range(len(options)):
            await msg.add_reaction(num_emoji_list[num])
        await msg.add_reaction(finish)

        user_roles_id = [role.id for role in self.values]

        data = PollingParameter(
            message_id=msg.id,
            author_id=interaction.user.id,
            channel_id=interaction.message.channel.id,
            created_at=now,
            allow_list=user_roles_id,
        )

        await polling_mng.register_polling(data)


class SelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(Select())

    async def on_timeout(self):
        # タイムアウトしたら消す
        for item in self.children:
            item.disabled = True  # type: ignore
        try:
            await self.message.edit(view=self)  # type: ignore
        except discord.NotFound:
            print("not found")
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # 実行者と選択者が違ったらFalseを返す
        if interaction.message is None:
            return False

        if interaction.message.interaction is None:
            return False

        if interaction.user != interaction.message.interaction.user:
            raise NotSameUserError("実行者と選択者が違います")

        return True

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ):
        if isinstance(error, NotSameUserError):
            await interaction.response.send_message(
                "実行者と選択者が違います", ephemeral=True
            )
            return
        if not isinstance(interaction.channel, discord.abc.Messageable):
            return
        await interaction.channel.send(f"エラーが発生しました。{error}")

    async def wait(self):
        print("wait")


class Polling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.setting_mng = SettingManager()

        self.o = "\N{HEAVY LARGE CIRCLE}"
        self.x = "\N{CROSS MARK}"

        self.polling_timer.stop()
        self.polling_timer.start()

    async def setup_hook(self):
        # self.bot.tree.copy_global_to(guild=MY_GUILD)
        pass

    @commands.Cog.listener()
    async def on_ready(self):
        """on_ready時に発火する関数"""
        await self.setting_mng.create_table()
        await polling_mng.create_table()

        await self.bot.tree.sync()

    @app_commands.command(name="poll")
    @app_commands.guild_only()
    async def poll(
        self,
        interaction: discord.Interaction,
        question: str,
        option_1: str,
        option_2: str | None = None,
        option_3: str | None = None,
        option_4: str | None = None,
        option_5: str | None = None,
        option_6: str | None = None,
        option_7: str | None = None,
        option_8: str | None = None,
        option_9: str | None = None,
        option_10: str | None = None,
    ) -> None:
        """optionで選択肢を追加します.ロールは最後に選択してください."""

        view = SelectView()
        await interaction.response.send_message("対象を選択してください", view=view)
        view.message = await interaction.original_response()

        global question_
        global options

        question_ = question

        options = []
        options.append(option_1)
        if option_2 is not None:
            options.append(option_2)
        if option_3 is not None:
            options.append(option_3)
        if option_4 is not None:
            options.append(option_4)
        if option_5 is not None:
            options.append(option_5)
        if option_6 is not None:
            options.append(option_6)
        if option_7 is not None:
            options.append(option_7)
        if option_8 is not None:
            options.append(option_8)
        if option_9 is not None:
            options.append(option_9)
        if option_10 is not None:
            options.append(option_10)

    @poll.error
    async def poll_error(self, interaction: discord.Interaction, error: Exception):
        if isinstance(error, commands.CheckFailure):
            await interaction.response.send_message(
                "このコマンドを実行する権限がありません", ephemeral=True
            )
        if not isinstance(interaction.channel, discord.abc.Messageable):
            return

        logger.warning(f"poll error : {error}")
        await interaction.channel.send(f"エラーが発生しました。{error}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction: discord.RawReactionActionEvent):
        if reaction.member is None or reaction.member.bot or reaction.guild_id is None:
            return

        if polling_data := await polling_mng.get_aggregation(reaction.message_id):
            member_role_ids = [role.id for role in reaction.member.roles]
            member_role_ids.append(reaction.user_id)
            channel = self.bot.get_channel(reaction.channel_id)

            now = discord.utils.utcnow()
            end_time = f"<t:{int(now.timestamp())}:f>"

            if len(polling_data.allow_list) == 0:
                pass
            elif len(set(polling_data.allow_list) & set(member_role_ids)) == 0:
                msg = await channel.fetch_message(reaction.message_id)
                try:
                    await msg.remove_reaction(str(reaction.emoji), reaction.member)
                except discord.Forbidden:
                    await channel.send("リアクションの除去に失敗しました.")
                notify_msg = await channel.send(
                    f"{reaction.member.mention} 権限無しのリアクションは禁止です！"
                )
                # await self.delete_after(notify_msg)
                return

            msg = await channel.fetch_message(reaction.message_id)
            result = ""

            if (
                reaction.emoji.name == finish
                and polling_data.author_id == reaction.member.id
            ):
                for added_reaction in msg.reactions:
                    if not added_reaction.emoji == finish:
                        result += f"{added_reaction}:{added_reaction.count - 1}\n"

                embed = msg.embeds[0].add_field(
                    name="結果", value=f"{result}", inline=False
                )

                embed = msg.embeds[0].add_field(
                    name="終了日時",
                    value=f"{end_time}",
                    inline=False,
                )
                await msg.edit(embed=embed)
                # await msg.clear_reactions()

                await polling_mng.remove_aggregation(reaction.message_id)

    @commands.Cog.listener()
    async def on_message(self, _: discord.Message):
        if not self.polling_timer.is_running():
            logger.warning("polling_timer is not running!")
            self.polling_timer.start()

    async def delete_expired_aggregation(self) -> None:
        """30日前から集計してる投票を削除する関数"""
        all_aggregation = await polling_mng.get_all_aggregation()

        if all_aggregation is None:
            return

        now = discord.utils.utcnow()

        for reaction in all_aggregation:
            elapsed_time = now - reaction.created_at
            if elapsed_time.days >= 30:
                await polling_mng.remove_aggregation(reaction.message_id)
                channel = self.bot.get_channel(reaction.channel_id)
                if channel is None:
                    continue
                msg = await channel.fetch_message(reaction.message_id)
                await msg.clear_reactions()

    @tasks.loop(hours=12.0)
    async def polling_timer(self) -> None:
        await self.delete_expired_aggregation()

    @polling_timer.before_loop
    async def before_printer(self):
        print("polling waiting...")
        await self.bot.wait_until_ready()

    @polling_timer.error
    async def error(self, arg):
        now = discord.utils.utcnow()
        jst_now = now.astimezone(ZoneInfo("Asia/Tokyo"))
        logging.warning(f"{jst_now} polling_timer error : {arg}")


async def setup(bot):
    await bot.add_cog(Polling(bot))
