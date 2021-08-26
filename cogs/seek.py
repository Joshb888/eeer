from discord.ext import commands
from lavalink import Utils

from cogs.music import time_rx
from utilities import checks


def setup(bot):
    bot.add_cog(Seek(bot))


class Seek:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['forward'])
    @checks.dj_only()
    async def seek(self, ctx, time):
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.is_playing:
            return await ctx.send('🚫 | I\'m not playing.')

        seconds = time_rx.search(time)

        if not seconds:
            return await ctx.send('🚫 | You need to specify the amount of seconds to seek!')

        seconds = int(seconds.group()) * 1000

        if time.startswith('-'):
            seconds *= -1

        track_time = player.position + seconds

        await player.seek(track_time)

        await ctx.send(f'✅ | Seeked to **{Utils.format_time(track_time)}**')
