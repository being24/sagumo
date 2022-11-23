import asyncio
import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ext.menus import ListPageSource, MenuPages
from sqlalchemy.sql.elements import Null

from .utils.common import CommonUtil

from .utils.reaction_aggregation_manager import AggregationManager, ReactionParameter
from .utils.setting_manager import SettingManager

c = CommonUtil()
logger = logging.getLogger("discord")

target_value_dict = {}


async def app_has_bot_manager(interaction: discord.Interaction) -> bool:
    return await c.has_bot_manager(interaction.guild, interaction.user)


async def app_has_bot_user(interaction: discord.Interaction) -> bool:
    return await c.has_bot_user(interaction.guild, interaction.user)


async def context_has_bot_manager(ctx: commands.Context) -> bool:
    return await c.has_bot_manager(ctx.guild, ctx.author)


class NotSameUserError(Exception):
    """Interactionの実行者とappコマンドの実行者が異なる場合のエラー"""

    pass


class ReactionList(ListPageSource):
    def __init__(self, ctx: commands.Context, data):
        self.ctx = ctx
        super().__init__(data, per_page=10)

    async def write_page(self, menu, fields: list[ReactionParameter] = []):
        offset = (menu.current_page * self.per_page) + 1
        len_data = len(self.entries)

        embed = discord.Embed(title="集計中のリアクションは以下の通りです", description=f"本サーバーでは{len_data}件集計中", color=0x0088FF)
        if self.ctx.guild is None or self.ctx.guild.me.avatar is None:
            return
        embed.set_thumbnail(url=self.ctx.guild.me.avatar.replace(format="png").url)

        embed.set_footer(text=f"{offset:,} - {min(len_data, offset+self.per_page-1):,} of {len_data:,} records.")

        for num, reaction in enumerate(fields):
            # USTのreaction.created_atをJSTに変換
            created_at = reaction.created_at.astimezone(ZoneInfo("Asia/Tokyo"))

            time = created_at.strftime("%Y-%m-%d %H:%M:%S")

            url = c.get_msg_url_from_reaction(reaction)

            target = " ".join([f"{c.return_member_or_role(self.ctx.guild, id).mention}" for id in reaction.ping_id])

            if reaction.matte:
                matte = " **待って！**"
            else:
                matte = ""

            reaction_author = self.ctx.guild.get_member(reaction.author_id)
            if reaction_author is None:
                author_mention = "不明"
            else:
                author_mention = reaction_author.mention

            if target == "":
                val = f"**ID** : {reaction.message_id} by : {author_mention} progress : {reaction.sum}/{reaction.target_value}{matte}\ntime : {time} [link.]({url})"
            else:
                val = f"**ID** : {reaction.message_id} by : {author_mention} progress : {reaction.sum}/{reaction.target_value}{matte}\ntarget: {target} time : {time} [link.]({url})"

            embed.add_field(name=f"{num+offset}番目", value=f"{val}", inline=False)

        return embed

    async def format_page(self, menu, entries):
        """
        fields = []

        for entry in entries:
            fields.append((entry.brief, syntax(entry)))
        """
        return await self.write_page(menu, entries)


class Select(discord.ui.MentionableSelect):
    def __init__(self):
        super().__init__(placeholder="対象を選択してください", min_values=0, max_values=25)
        self.aggregation_mng = AggregationManager()

    async def callback(self, interaction: discord.Interaction):
        # select menuを無効にする
        for item in self.view.children:
            item.disabled = True
        await self.view.message.edit(view=self.view)

        target_value = target_value_dict.pop(self.custom_id)
        if target_value is None:
            logger.warn("target_value is None")
            return

        if interaction.guild is None:
            logger.warn("guild is None")
            return

        # self.valuesから自分自身を除いたidのリストを作成
        insert_roles_ids = [
            role_or_member.id for role_or_member in self.values if role_or_member.id != interaction.guild.me.id
        ]

        first_msg = f"リアクション集計を行います: 目標リアクション数 : **{target_value}**"

        if len(insert_roles_ids) > 0:
            mid_msg = f"指定された役職/ユーザー : {' '.join([role_or_member.mention for role_or_member in self.values])}\n"
        else:
            mid_msg = ""

        insert_roles_str = ",".join([str(id) for id in insert_roles_ids])

        last_msg = "本メッセージにリアクションをつけてください"

        await interaction.response.send_message(f"{first_msg}\n{mid_msg}{last_msg}")
        msg = await interaction.original_response()

        now = discord.utils.utcnow()

        if interaction.guild is None:
            logger.warn("interaction.guild is None")
            return

        if interaction.channel is None:
            logger.warn("interaction.channel is None")
            return

        if self.view is None:
            logger.warn("self.view is None")
            return

        await self.aggregation_mng.register_aggregation(
            message_id=msg.id,
            command_id=self.view.message.id,
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            target_value=target_value,
            author_id=interaction.user.id,
            created_at=now,
            ping_id=insert_roles_str,
        )


class SelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(Select())

    async def on_timeout(self):
        # タイムアウトしたら消す
        for item in self.children:
            item.disabled = True  # type: ignore
        await self.message.edit(view=self)  # type: ignore

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # 実行者と選択者が違ったらFalseを返す
        if interaction.message is None:
            return False

        if interaction.message.interaction is None:
            return False

        if interaction.user != interaction.message.interaction.user:
            raise NotSameUserError("実行者と選択者が違います")

        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        if isinstance(error, NotSameUserError):
            await interaction.response.send_message("実行者と選択者が違います", ephemeral=True)
            return
        if not isinstance(interaction.channel, discord.TextChannel):
            return
        await interaction.channel.send(f"エラーが発生しました。{error}")

    async def wait(self):
        print("wait")


class Confirm(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="はい", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("はい", ephemeral=True)
        self.value = True
        self.stop()

    @discord.ui.button(label="いいえ", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("いいえ", ephemeral=True)
        self.value = False
        self.stop()


class ReactionAggregator(commands.Cog):
    """
    リアクション集計のカテゴリ
    """

    def __init__(self, bot):
        self.bot: commands.Bot = bot

        self.setting_mng = SettingManager()
        self.aggregation_mng = AggregationManager()

        self.reaction_reminder.stop()
        self.reaction_reminder.start()

    async def setup_hook(self):
        # self.bot.tree.copy_global_to(guild=MY_GUILD)
        pass

    async def start_paginating(self, ctx: commands.Context, reaction_list_of_guild):
        if reaction_list_of_guild is None:
            await ctx.send("集計中のリアクションはありません")
        else:
            menu = MenuPages(source=ReactionList(ctx, reaction_list_of_guild), delete_message_after=True, timeout=60.0)
            await menu.start(ctx)

    async def change_delete_msg(self, channel_id: int, message_id: int) -> None:
        """集計終了時元メッセージを変更する関数

        Args:
            channel_id (int): チャンネルID
            message_id (int): メッセージID
        """
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return
        if isinstance(channel, discord.Thread):
            if channel.archived:
                return
        if not isinstance(channel, discord.TextChannel):
            return
        try:
            msg = await channel.fetch_message(message_id)
            # await msg.clear_reactions()
            await msg.edit(content="集計終了しました")
        except discord.Forbidden:
            pass
        except discord.NotFound:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        """on_ready時に発火する関数"""
        await self.aggregation_mng.create_table()
        await self.setting_mng.create_table()

        await self.bot.tree.sync()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.reaction_reminder.is_running():
            logger.warning("reaction_reminder is not running!")
            self.reaction_reminder.start()

    async def judge_and_notice(self, message_id: int):
        reaction_data = await self.aggregation_mng.get_aggregation(message_id)
        if reaction_data is None:
            return

        if reaction_data.target_value == reaction_data.sum and reaction_data.matte == 0:
            channel = self.bot.get_channel(reaction_data.channel_id)
            guild = self.bot.get_guild(reaction_data.guild_id)
            if channel is None or guild is None:
                logger.warning(
                    f"channel or guild is None. channel_id: {reaction_data.channel_id}, guild_id: {reaction_data.guild_id}"
                )
                return

            if not isinstance(channel, discord.TextChannel):
                return

            command_msg = await channel.fetch_message(reaction_data.command_id)

            url = c.get_msg_url_from_reaction(reaction_data)

            roles = [c.return_member_or_role(guild, id).name for id in reaction_data.ping_id]

            if len(roles) == 0:
                roles = "None"
            else:
                roles = " ".join(roles)

            now = discord.utils.utcnow()

            await self.aggregation_mng.set_value_to_notified(reaction_data.message_id, now)

            embed = discord.Embed(title="規定数のリアクションがたまりました")
            embed.add_field(name="終了した集計のリンク", value=f"{url}", inline=False)
            embed.add_field(name="集計完了時間", value=f"{now.strftime('%Y-%m-%d %H:%M:%S')}", inline=False)
            embed.set_footer(text=f"target : {roles}")

            author = guild.get_member(reaction_data.author_id)
            if author is None:
                author_mention = "None"
            else:
                author_mention = author.mention

            await command_msg.reply(f"{author_mention}", embed=embed)

            msg = await channel.fetch_message(reaction_data.message_id)
            await msg.edit(content=msg.content + "\n\t終了しました")

        elif reaction_data.notified_at is not Null and reaction_data.target_value > reaction_data.sum:
            channel = self.bot.get_channel(reaction_data.channel_id)

            if not isinstance(channel, discord.TextChannel):
                return

            msg = await channel.fetch_message(reaction_data.message_id)
            await msg.edit(content=msg.content.replace("\n\t終了しました", ""))

    @app_commands.command(name="count")
    @app_commands.check(app_has_bot_manager)
    @app_commands.guild_only()
    async def count(self, interaction: discord.Interaction, target_value: int):
        """リアクション集計を開始するコマンド

        Args:
            target_value (int): 集計するリアクションの数
        """

        if target_value <= 0:
            await interaction.response.send_message("引数を正しく入力してください")
            return
        view = SelectView()
        await interaction.response.send_message("対象を選択してください", view=view)

        view.message = await interaction.original_response()  # type: ignore
        target_value_dict[view.children[0].custom_id] = target_value  # type: ignore

    @count.error
    async def count_error(self, interaction: discord.Interaction, error: Exception):
        if isinstance(error, commands.CheckFailure):
            await interaction.response.send_message("このコマンドを実行する権限がありません", ephemeral=True)
        if not isinstance(interaction.channel, discord.TextChannel):
            return
        await interaction.channel.send(f"エラーが発生しました。{error}")

    @app_commands.command(name="list_reaction")
    @app_commands.check(app_has_bot_user)
    @app_commands.guild_only()
    async def list_reaction(self, interaction: discord.Interaction, all: bool = False):
        """集計中のリアクション一覧を表示するコマンド

        Args:
            all (bool, optional): 終了済みの集計も表示するかどうか. Defaults to False.
        """
        if interaction.guild is None:
            logger.warn("guild is None @list_reaction")
            return

        reaction_list_of_guild = await self.aggregation_mng.get_guild_list(interaction.guild.id)

        if reaction_list_of_guild is None:
            await interaction.response.send_message("集計中のリアクションはありません")
            return

        if not all:
            reaction_list_of_guild = [reaction for reaction in reaction_list_of_guild if reaction.notified_at is None]

        if len(reaction_list_of_guild) == 0:
            await interaction.response.send_message("集計中のリアクションはありません")
            return

        await interaction.response.send_message("リアクション集計一覧を表示します")
        message = await interaction.original_response()
        # await c.delete_after(message, 1)

        ctx: commands.Context = await self.bot.get_context(message)
        await self.start_paginating(ctx, reaction_list_of_guild)

    @list_reaction.error
    async def list_reaction_error(self, interaction: discord.Interaction, error: Exception):
        if isinstance(error, commands.CheckFailure):
            await interaction.response.send_message("このコマンドを実行する権限がありません", ephemeral=True)
        if not isinstance(interaction.channel, discord.TextChannel):
            return
        await interaction.channel.send(f"エラーが発生しました。{error}")

    @app_commands.command(name="remove_reaction")
    @app_commands.check(app_has_bot_manager)
    @app_commands.guild_only()
    async def remove_reaction(self, interaction: discord.Interaction, message_id_str: str):
        """リアクション集計を削除するコマンド

        Args:
            interaction (discord.Interaction): interaction
            message_id (str): 削除するリアクション集計のメッセージID
        """

        message_id = 0
        if message_id_str.isdecimal():
            message_id = int(message_id_str)

        if message_id == 0:
            await interaction.response.send_message("引数を正しく入力してください")
            return

        if await self.aggregation_mng.is_exist(message_id):
            if interaction.channel is None:
                logger.warn("interaction.channel is None @remove_reaction")
                return

            view = Confirm()
            await interaction.response.send_message(f"ID : {message_id}のリアクション集計を終了し、削除しますか？", view=view)
            await view.wait()
            if view.value is None:
                await interaction.followup.send("タイムアウトしました")
            elif view.value:
                await self.aggregation_mng.remove_aggregation(message_id)
                await interaction.followup.send(f"ID : {message_id}は{interaction.user}により削除されました")
                await self.change_delete_msg(interaction.channel.id, message_id)
            else:
                await interaction.followup.send(f"ID : {message_id}の削除を中止しました")
                notify_msg = await interaction.original_response()
                await c.delete_after(notify_msg)

        else:
            await interaction.response.send_message(f"ID : {message_id}はリアクション集計対象ではありません")
            notify_msg = await interaction.original_response()
            await c.delete_after(notify_msg)

    @remove_reaction.error
    async def remove_reaction_error(self, interaction: discord.Interaction, error: Exception):
        if isinstance(error, commands.CheckFailure):
            await interaction.response.send_message("このコマンドを実行する権限がありません", ephemeral=True)
        if not isinstance(interaction.channel, discord.TextChannel):
            return
        await interaction.channel.send(f"エラーが発生しました。{error}")

    @app_commands.command(name="add_role")
    @app_commands.check(app_has_bot_manager)
    @app_commands.guild_only()
    async def add_role(self, interaction: discord.Interaction, add_role: discord.Role, has_role: discord.Role):
        """特定の役職持ちに特定のリアクションを付与するコマンド

        Args:
            interaction (discord.Interaction): interaction
            add_role (discord.Role): 対象に付与する役職
            has_role (discord.Role): この役職を持っている人に付与する
        """

        target_members = [member for member in has_role.members if add_role not in member.roles]

        if len(target_members) == 0:
            await interaction.response.send_message("対象者はいません")
            return

        await interaction.response.send_message(
            f"{len(target_members)}人に{add_role.name}を付与します",
        )

        msg = await interaction.original_response()

        if interaction.guild is None:
            logger.warn("guild is None @add_role")
            return

        for member in target_members:
            try:
                await member.add_roles(add_role, reason=f"{interaction.guild.me}による自動付与")
                msg = await interaction.followup.send(f"{member.name}に{add_role.name}を付与しました", ephemeral=True)
                if msg is not None:
                    await c.delete_after(msg)
                await asyncio.sleep(0.3)
            except discord.Forbidden:
                msg = await interaction.followup.send(f"{member.name}への{add_role}に失敗しました。権限不足です")
                if msg is not None:
                    await c.delete_after(msg)
            except BaseException as e:
                msg = await interaction.followup.send(f"{member.name}への{add_role}に失敗しました。{e}")
                if msg is not None:
                    await c.delete_after(msg)

        await interaction.followup.send("付与が完了しました")

    @add_role.error
    async def add_role_error(self, interaction: discord.Interaction, error: Exception):
        if isinstance(error, commands.CheckFailure):
            await interaction.response.send_message("このコマンドを実行する権限がありません", ephemeral=True)
        if not isinstance(interaction.channel, discord.TextChannel):
            return
        await interaction.channel.send(f"エラーが発生しました。{error}")

    @app_commands.command(name="register_manage_role")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def register_manage_role(
        self, interaction: discord.Interaction, bot_manager: discord.Role, bot_user: discord.Role
    ):
        """bot管理者とbot使用者を登録するコマンド、順番注意

        Args:
            interaction (discord.Interaction): interaction
            bot_manager (discord.Role): 沙雲の管理権限を持たせる役職
            bot_user (discord.Role): 沙雲の使用権限を持たせる役職
        """

        if interaction.guild is None:
            logger.warn("guild is None @sagumo_initialization")
            return

        if await self.setting_mng.is_exist(interaction.guild.id):
            await self.setting_mng.update_guild(
                guild_id=interaction.guild.id, bot_manager_id=bot_manager.id, bot_user_id=bot_user.id
            )
            await interaction.response.send_message(
                f"{interaction.guild}のbot管理者に{bot_manager.mention}を、bot操作者に{bot_user.mention}に更新しました",
                allowed_mentions=discord.AllowedMentions.none(),
            )
        else:
            await self.setting_mng.register_guild(
                guild_id=interaction.guild.id, bot_manager_id=bot_manager.id, bot_user_id=bot_user.id
            )
            await interaction.response.send_message(
                f"{interaction.guild}のbot管理者に{bot_manager.mention}を、bot操作者に{bot_user.mention}を登録しました",
                allowed_mentions=discord.AllowedMentions.none(),
            )

    @register_manage_role.error
    async def register_manage_role_error(self, interaction: discord.Interaction, error: Exception):
        if isinstance(error, commands.CheckFailure):
            await interaction.response.send_message("このコマンドを実行する権限がありません", ephemeral=True)
        if not isinstance(interaction.channel, discord.TextChannel):
            return
        await interaction.channel.send(f"エラーが発生しました。{error}")

    @app_commands.command(name="show_manage_role")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def show_manage_role(self, interaction: discord.Interaction):
        """bot管理者とbot使用者を表示するコマンド

        Args:
            interaction (discord.Interaction): interaction
        """
        if interaction.guild is None:
            logger.warn("guild is None @sagumo_initialization")
            return

        if guild_setting := await self.setting_mng.get_guild(interaction.guild.id):
            bot_manager = c.return_member_or_role(guild=interaction.guild, id=guild_setting.bot_manager_id)
            bot_user = c.return_member_or_role(guild=interaction.guild, id=guild_setting.bot_user_id)

            await interaction.response.send_message(
                f"{interaction.guild}のbot管理者は{bot_manager.mention}、bot操作者は{bot_user.mention}です",
                allowed_mentions=discord.AllowedMentions.none(),
            )

        else:
            await interaction.response.send_message(f"{interaction.guild}のbot管理者とbot操作者は登録されていません")

    @show_manage_role.error
    async def show_manage_role_error(self, interaction: discord.Interaction, error: Exception):
        if isinstance(error, commands.CheckFailure):
            await interaction.response.send_message("このコマンドを実行する権限がありません", ephemeral=True)
        if not isinstance(interaction.channel, discord.TextChannel):
            return
        await interaction.channel.send(f"エラーが発生しました。{error}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction: discord.RawReactionActionEvent):
        """リアクションが追加されたときに、集計対象メッセージであれば+1する関数

        Args:
            reaction (discord.Reaction): reactionオブジェクト
        """
        if reaction.member is None or reaction.member.bot or reaction.guild_id is None:
            return
        if reaction_data := await self.aggregation_mng.get_aggregation(reaction.message_id):
            message_id = reaction.message_id

            member_role_ids = [role.id for role in reaction.member.roles]
            member_role_ids.append(reaction.user_id)
            channel = self.bot.get_channel(reaction.channel_id)

            if not isinstance(channel, discord.TextChannel):
                return

            if len(reaction_data.ping_id) == 0:
                pass
            elif len(set(reaction_data.ping_id) & set(member_role_ids)) == 0:
                msg = await channel.fetch_message(reaction.message_id)
                try:
                    await msg.remove_reaction(str(reaction.emoji), reaction.member)
                except discord.Forbidden:
                    await channel.send("リアクションの除去に失敗しました.")
                notify_msg = await channel.send(f"{reaction.member.mention} 権限無しのリアクションは禁止です！")
                # await self.delete_after(notify_msg)
                return

            if "matte" in reaction.emoji.name:
                await self.aggregation_mng.set_value_to_matte(message_id=message_id, val=reaction_data.matte + 1)
                msg = await channel.fetch_message(reaction.message_id)
                await msg.edit(content=msg.content + "\n待ちます")
            else:
                await self.aggregation_mng.set_value_to_sum(message_id=message_id, val=reaction_data.sum + 1)

            await self.judge_and_notice(message_id)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, reaction: discord.RawReactionActionEvent):
        """リアクションが除去されたときに、集計対象メッセージであれば-1する関数

        Args:
            reaction (discord.Reaction): reactionオブジェクト
        """
        if reaction.guild_id is None:
            return

        if reaction_data := await self.aggregation_mng.get_aggregation(reaction.message_id):
            message_id = reaction.message_id
            guild = self.bot.get_guild(reaction_data.guild_id)
            if guild is None:
                logger.warn("guild is None @on_raw_reaction_remove")
                return

            remove_usr = guild.get_member(reaction.user_id)
            if remove_usr is None:
                logger.warn("remove_usr is None @on_raw_reaction_remove")
                return

            channel = self.bot.get_channel(reaction.channel_id)
            if not isinstance(channel, discord.TextChannel):
                logger.warn("channel is not TextChannel @on_raw_reaction_remove")
                return

            member_role_ids = [role.id for role in remove_usr.roles]
            member_role_ids.append(reaction.user_id)

            if len(reaction_data.ping_id) == 0:
                pass
            elif len(set(reaction_data.ping_id) & set(member_role_ids)) == 0:
                return

            if "matte" in reaction.emoji.name:
                await self.aggregation_mng.set_value_to_matte(message_id=message_id, val=reaction_data.matte - 1)
                msg = await channel.fetch_message(reaction.message_id)
                await msg.edit(content=msg.content.replace("\n待ちます", "", 1))
            else:
                await self.aggregation_mng.unset_value_to_notified(message_id=message_id)
                await self.aggregation_mng.set_value_to_sum(message_id=message_id, val=reaction_data.sum - 1)

            await self.judge_and_notice(message_id)

    async def delete_notified(self) -> None:
        """リアクション集計が終了してから3日以上たった時に削除する関数"""
        notified_aggregation = await self.aggregation_mng.get_notified_aggregation()

        if notified_aggregation is None:
            return

        now = discord.utils.utcnow()

        for reaction in notified_aggregation:
            if reaction.notified_at is None:
                continue
            elapsed_time = now - reaction.notified_at
            if elapsed_time.days >= 3:
                await self.aggregation_mng.remove_aggregation(reaction.message_id)
                await self.change_delete_msg(reaction.channel_id, reaction.message_id)

    async def remind(self) -> None:
        """リマインドを行う関数"""

        # 12h, 24h, 以後24h間隔が個人的には理想です

        all_aggregation = await self.aggregation_mng.get_all_aggregation()

        if all_aggregation is None:
            return

        now = discord.utils.utcnow()

        for reaction in all_aggregation:
            if reaction.sum >= reaction.target_value:
                continue

            elapsed_time = now - reaction.created_at
            if reaction.remind == "" or reaction.remind is None:  # 要修正
                if elapsed_time.total_seconds() >= 12 * 3600:
                    await self.send_remind(reaction, elapsed_time.days, elapsed_time)
            else:
                if elapsed_time.days != reaction.remind:
                    await self.send_remind(reaction, reaction.remind + 1, elapsed_time)

    async def send_remind(self, reaction: ReactionParameter, val: int, elapsed_time: timedelta) -> None:
        """リマインドを送信する関数

        Args:
            reaction (ReactionParameter): リアクション集計
        """
        channel = self.bot.get_channel(reaction.channel_id)
        if not isinstance(channel, discord.TextChannel):
            logger.warn("channel is not TextChannel @send_remind")
            return
        url = c.get_msg_url_from_reaction(reaction)
        guild = self.bot.get_guild(reaction.guild_id)
        if guild is None:
            logger.warn("guild is None @send_remind")
            return

        roles = [c.return_member_or_role(guild, id) for id in reaction.ping_id]
        if len(roles) == 0:
            roles_mention = "None"
            roles_name = "None"
        else:
            roles_mention = " ".join([member.mention for member in roles])
            roles_name = " ".join([member.name for member in roles])

        auth = c.return_member_or_role(guild, reaction.author_id)
        reaction_sum = reaction.sum
        reaction_cnt = reaction.target_value

        days = elapsed_time.days
        minutes, seconds = divmod(elapsed_time.seconds, 60)
        hours, minutes = divmod(minutes, 60)
        embed = discord.Embed(title="リマインドします")
        embed.add_field(
            name="詳細",
            value=f"ID : {reaction.message_id} by : {auth}\nprogress : {reaction_sum}/{reaction_cnt} [link.]({url})",
            inline=False,
        )
        embed.set_footer(text=f"対象 : {roles_name} 経過時間 : {days} days, {hours} hours {minutes} minutes")
        if roles_mention != "None":
            await channel.send(f"{roles_mention}")
        await channel.send(embed=embed)
        await self.aggregation_mng.set_value_to_remind(reaction.message_id, val)
        await asyncio.sleep(0.3)

    async def delete_expired_aggregation(self) -> None:
        """14日前から集計してる集計を削除する関数"""
        all_aggregation = await self.aggregation_mng.get_all_aggregation()

        if all_aggregation is None:
            return

        now = discord.utils.utcnow()

        for reaction in all_aggregation:
            elapsed_time = now - reaction.created_at
            if elapsed_time.days >= 14:
                await self.aggregation_mng.remove_aggregation(reaction.message_id)
                await self.change_delete_msg(reaction.channel_id, reaction.message_id)

    @tasks.loop(minutes=1.0)
    async def reaction_reminder(self) -> None:
        await self.delete_notified()
        await self.remind()

    @reaction_reminder.before_loop
    async def before_printer(self):
        print("reaction waiting...")
        await self.bot.wait_until_ready()

    @reaction_reminder.error
    async def error(self, error) -> None:
        logger.warning(error)


async def setup(bot):
    await bot.add_cog(ReactionAggregator(bot))
