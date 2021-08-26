from discord.ext import commands

from cogs.music import Music
from utilities import checks


def setup(bot):
    bot.add_cog(Playtop(bot))


class Playtop:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['pt', 'addtop'])
    @checks.dj_only()
    async def playtop(self, ctx, *, query=None):
        await self.run_command(ctx, query, False)

    @commands.command(aliases=['ps', 'addskip'])
    @checks.dj_only()
    async def playskip(self, ctx, query=None):
        await self.run_command(ctx, query, True)

    async def run_command(self, ctx, query, force):
        player = await Music.get_player(ctx=ctx, bot=self.bot, guild_id=None)

        if query is None:
            return await ctx.send('🚫 | Please specify a query!')

        check = await Music.check_connect(ctx, player)
        if check is not None:
            return

        results = await Music.get_tracks(self.bot, query, ctx)

        if results['loadType'] == "PLAYLIST_LOADED":
            return await ctx.send('🚫 | You cannot add a playlist to the top of the queue!')
        else:
            await Music.enqueue_songs(player, results, ctx, 0)

        if not player.is_playing and player.queue:
            await player.play()
        elif force:
            await player.skip()
