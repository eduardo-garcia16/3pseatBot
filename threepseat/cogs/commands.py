import discord
import json
import os
import random

from discord.ext import commands
from typing import Any, Callable, List, Optional

from threepseat.bot import Bot
from threepseat.utils import is_admin, GuildDatabase


class Commands(commands.Cog):
    """Extension for custom commands.

    Adds the following commands:
      - `?command add [name] [command text]
      - `?command remove [name]
    """
    def __init__(self,
                 bot: Bot,
                 commands_file: str,
                 guild_admin_permission: bool = True,
                 bot_admin_permission: bool = True,
                 everyone_permission: bool = False
    ) -> None:
        """
        Args:
            bot (Bot): bot that loaded this cog
            commands_file (str): path to store database
            guild_admin_permission (bool): can guild admins start polls
            bot_admin_permission (bool): can bot admin start polls
            everyone_permission (bool): allow everyone to start polls
        """
        self.bot = bot
        self.guild_admin_permission = guild_admin_permission
        self.bot_admin_permission = bot_admin_permission
        self.everyone_permission = everyone_permission
        self.db = GuildDatabase(commands_file)

        # Register all commands on startup
        tables = self.db.tables()
        for table in tables.values():
            for name, text in table.items():
                self.bot.add_command(self.make_command(name, text))

    def has_permission(self, member: discord.Member) -> bool:
        """Does a member have permission to edit commands"""
        if self.everyone_permission:
            return True
        if is_admin(member) or self.bot.is_bot_admin(member):
            return True
        return False

    async def add(self, ctx: commands.Context, name: str, text: str) -> None:
        """Add a new command to the guild

        Sends a message to `ctx.channel` on success or failure.

        Args:
            ctx (Context): context from command call
            name (str): name of command
            text (str): text of command
        """
        if not self.has_permission(ctx.message.author):
            await self.bot.message_guild(
                '{}, you do not have permission to add a command'.format(
                    ctx.message.author.mention),
                ctx.channel)
            return

        # Save to database
        self._set_command(ctx.guild, name, text)
        # Remove first in case this command already exists
        self.bot.remove_command(name)
        # Register with bot
        self.bot.add_command(self.make_command(name, text))

        await self.bot.message_guild(
                'added command {}{}'.format(self.bot.command_prefix, name),
                ctx.channel)

    async def remove(self, ctx: commands.Context, name: str) -> None:
        """Remove a command from the guild

        Sends a message to `ctx.channel` on success or failure.

        Args:
            ctx (Context): context from command call
            name (str): name of command to remove
        """
        if not self.has_permission(ctx.message.author):
            await self.bot.message_guild(
                '{}, you do not have permission to remove a command'.format(
                    ctx.message.author.mention),
                ctx.channel)
            return

        # Remove from bot
        self.bot.remove_command(name)
        # Remove from database
        self._remove_command(ctx.guild, name)

        await self.bot.message_guild(
                'removed command {}{}'.format(self.bot.command_prefix, name),
                ctx.channel)

    def make_command(self, name: str, text: str) -> commands.Command:
        async def _command(_ctx: commands.Context):
            _text = self._get_command(_ctx.guild, name)
            if _text is None:
                await self.bot.message_guild(
                    'this command is not available in this guild',
                    _ctx.channel)
            else:
                await self.bot.message_guild(_text, _ctx.channel)

        return commands.Command(_command, name=name, cog=self)

    def _get_command(self, guild: discord.Guild, name: str) -> Optional[str]:
        """Get command text from database"""
        return self.db.value(guild, name)

    def _remove_command(self, guild: discord.Guild, name: str) -> None:
        """Remove command text from database"""
        return self.db.clear(guild, name)

    def _set_command(self, guild: discord.Guild, name: str, text: str) -> None:
        """Set command in dataset"""
        self.db.set(guild, name, text)

    @commands.group(name='commands', pass_context=True, brief='?help commands for more info')
    async def _commands(self, ctx: commands.Context) -> None:
        pass

    @_commands.command(name='add', pass_context=True, brief='add a command')
    async def _add(self, ctx: commands.Context, name: str, *, text: str) -> None:
        await self.add(ctx, name, text)

    @_commands.command(name='remove', pass_context=True, brief='remove a command')
    async def _remove(self, ctx: commands.Context, name: str) -> None:
        await self.remove(ctx, name)