import logging

import discord
from discord.ext import commands

from cogs.utils.reaction_aggregation_manager import ReactionParameter

from .setting_manager import SettingManager


# TODO: migrate from tzlocal to zoneinfo
class CommonUtil:
    def __init__(self):
        self.setting_mng = SettingManager()

    async def is_bot_user(self, guild: discord.Guild, command_user: discord.Member) -> bool:
        """そのサーバーのBOT_user役職を持っているか判定する関数

        Args:
            guild (discord.Guild): サーバーのギルドオブジェクト
            command_user (discord.Member): コマンド使用者のメンバーオブジェクト

        Returns:
            bool: 入ってたらTrue、入ってなかったらFalse

        Memo:
            管理者は使用者の権限も持つことにする
        """
        guild_db = await self.setting_mng.get_guild(guild.id)
        if guild_db is None:
            return False
        bot_user_role = guild.get_role(guild_db.bot_user_id)
        bot_manager_role = guild.get_role(guild_db.bot_manager_id)

        if any([role in command_user.roles for role in [bot_manager_role, bot_user_role]]):
            return True
        else:
            return False

    async def is_bot_manager(self, guild: discord.Guild, command_user: discord.Member) -> bool:
        """そのサーバーのBOT_manager役職を持っているか判定する関数

        Args:
            guild (discord.Guild): サーバーのギルドオブジェクト
            command_user (discord.Member): コマンド使用者のメンバーオブジェクト

        Returns:
            bool: 入ってたらTrue、入ってなかったらFalse
        """
        guild_db = await self.setting_mng.get_guild(guild.id)
        if guild_db is None:
            return False
        bot_manager_role = guild.get_role(guild_db.bot_manager_id)
        if bot_manager_role in command_user.roles:
            return True
        else:
            return False

    @staticmethod
    async def delete_after(msg: discord.Message | discord.InteractionMessage, second: int = 5):
        """渡されたメッセージを指定秒数後に削除する関数

        Args:
            msg (discord.Message): 削除するメッセージオブジェクト
            second (int, optional): 秒数. Defaults to 5.
        """
        if isinstance(msg, discord.InteractionMessage):
            try:
                await msg.delete(delay=second)
            except discord.Forbidden:
                logging.error("メッセージの削除に失敗しました。Forbidden")
        else:
            try:
                await msg.delete(delay=second)
            except discord.Forbidden:
                logging.error("メッセージの削除に失敗しました。Forbidden")

    @staticmethod
    def get_msg_url_from_reaction(reaction: ReactionParameter) -> str:
        """msg_urlをリアクションから生成する関数

        Args:
            reaction (ReactionParameter): リアクションオブジェクト

        Returns:
            str: discordのURL
        """
        url = f"https://discord.com/channels/{reaction.guild_id}/{reaction.channel_id}/{reaction.message_id}"
        return url

    @staticmethod
    def return_member_or_role(guild: discord.Guild, id: int) -> discord.Role | discord.Member:
        """メンバーか役職オブジェクトを返す関数

        Args:
            guild (discord.guild): discord.pyのguildオブジェクト
            id (int): 役職かメンバーのID

        Returns:
            typing.Union[discord.Member, discord.Role]: discord.Memberかdiscord.Role
        """
        user_or_role = guild.get_role(id)
        if user_or_role is None:
            user_or_role = guild.get_member(id)

        if user_or_role is None:
            raise ValueError(f"IDが不正です。ID:{id}")

        return user_or_role

    async def has_bot_user(self, guild: discord.Guild | None, command_user: discord.Member | discord.User) -> bool:
        """bot_userかどうか判定する関数

        Args:
            guild (discord.Guild): サーバーのギルドオブジェクト
            command_user (discord.Member): コマンド使用者のメンバーオブジェクト

        Returns:
            bool: BOT_userならTrue、そうでなければFalse
        """

        if isinstance(command_user, discord.User):
            return False

        if not isinstance(guild, discord.Guild):
            return False

        if not await self.is_bot_user(guild, command_user):
            return False
        else:
            return True

    async def has_bot_manager(self, guild: discord.Guild | None, command_user: discord.Member | discord.User) -> bool:
        """bot_managerかどうか判定する関数

        Args:
            guild (discord.Guild): サーバーのギルドオブジェクト
            command_user (discord.Member): コマンド使用者のメンバーオブジェクト

        Returns:
            bool: BOT_userならTrue、そうでなければFalse
        """

        if isinstance(command_user, discord.User):
            return False

        if not isinstance(guild, discord.Guild):
            return False

        if not await self.is_bot_manager(guild, command_user):
            return False
        else:
            return True
