import discord
from discord.ext import commands
from loguru import logger

from prisma.enums import CaseType
from tux.bot import Tux
from tux.database.controllers.case import CaseController
from tux.utils import checks
from tux.utils.flags import SnippetBanFlags, generate_usage

from . import ModerationCogBase


class SnippetBan(ModerationCogBase):
    def __init__(self, bot: Tux) -> None:
        super().__init__(bot)
        self.case_controller = CaseController()
        self.snippet_ban.usage = generate_usage(self.snippet_ban, SnippetBanFlags)

    async def is_snippetbanned(self, guild_id: int, user_id: int) -> bool:
        """
        Check if a user is snippet banned.

        Parameters
        ----------
        guild_id : int
            The ID of the guild to check in.
        user_id : int
            The ID of the user to check.

        Returns
        -------
        bool
            True if the user is snippet banned, False otherwise.
        """
        ban_cases = await self.db.case.get_all_cases_by_type(guild_id, CaseType.SNIPPETBAN)
        unban_cases = await self.db.case.get_all_cases_by_type(guild_id, CaseType.SNIPPETUNBAN)

        ban_count = sum(case.case_user_id == user_id for case in ban_cases)
        unban_count = sum(case.case_user_id == user_id for case in unban_cases)

        return ban_count > unban_count

    @commands.hybrid_command(
        name="snippetban",
        aliases=["sb"],
    )
    @commands.guild_only()
    @checks.has_pl(3)
    async def snippet_ban(
        self,
        ctx: commands.Context[Tux],
        member: discord.Member,
        reason: str | None = None,
        *,
        flags: SnippetBanFlags,
    ) -> None:
        """
        Ban a user from creating snippets.

        Parameters
        ----------
        ctx : commands.Context[Tux]
            The context object.
        member : discord.Member
            The member to snippet ban.
        reason : str | None
            The reason for the snippet ban.
        flags : SnippetBanFlags
            The flags for the command. (silent: bool)
        """

        assert ctx.guild
        await ctx.defer(ephemeral=True)

        if await self.is_snippetbanned(ctx.guild.id, member.id):
            await ctx.send("User is already snippet banned.", ephemeral=True)
            return

        if not await self.check_conditions(ctx, member, ctx.author, "snippet ban"):
            return

        final_reason: str = reason if reason is not None else "No reason provided"
        silent: bool = flags.silent

        try:
            case = await self.db.case.insert_case(
                case_user_id=member.id,
                case_moderator_id=ctx.author.id,
                case_type=CaseType.SNIPPETBAN,
                case_reason=final_reason,
                guild_id=ctx.guild.id,
            )

        except Exception as e:
            logger.error(f"Failed to ban {member}. {e}")
            await ctx.send(f"Failed to ban {member}. {e}", ephemeral=True)
            return

        dm_sent = await self.send_dm(ctx, silent, member, final_reason, "snippet banned")
        await self.handle_case_response(ctx, CaseType.SNIPPETBAN, case.case_number, final_reason, member, dm_sent)


async def setup(bot: Tux) -> None:
    await bot.add_cog(SnippetBan(bot))
