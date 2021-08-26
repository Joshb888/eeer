from discord.ext import commands

from utilities import checks


def setup(bot):
    bot.add_cog(Shuffle(bot))


class Shuffle:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @checks.premium_only(2)
    async def shuffle(self, ctx):
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.is_playing:
            return await ctx.send('🚫 | I\'m not playing.')

        player.shuffle = not player.shuffle

        await ctx.send('🔀 | Shuffle ' + ('enabled' if player.shuffle else 'disabled'))
