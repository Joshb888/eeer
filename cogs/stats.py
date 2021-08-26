import datetime
import time

import discord
from discord.ext import commands

start_time = time.time()


def setup(bot):
    bot.add_cog(Stats(bot))


class Stats:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def stats(self, ctx):
        current_time = time.time()
        difference = int(round(current_time - start_time))
        uptime = "{:0>8}".format(str(datetime.timedelta(seconds=difference)))

        guilds = len(self.bot.guilds)
        users = len(self.bot.users)
        voicechannels = len(self.bot.lavalink.players)
        latency = f'{int(self.bot.latency * 1000)}ms'

        embed = discord.Embed(
            description='📈 Groovys Statistics\n\n'
                        f'**Guilds** {guilds}\n'
                        f'**Playing** {voicechannels}\n'
                        f'**Users** {users}\n'
                        f'**Latency** {latency}\n'
                        f'**Uptime** {uptime}\n',
            color=0x2C2F33
        ).set_thumbnail(url=ctx.me.avatar_url)

        return await ctx.send(embed=embed)
