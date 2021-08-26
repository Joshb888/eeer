import math

import discord
from discord.ext import commands


def setup(bot):
    bot.add_cog(Queue(bot))


class Queue:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['q'])
    async def queue(self, ctx, page: int = 1):
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.is_playing:
            return await ctx.send('🚫 | There\'s nothing in the queue! Why not queue something?')

        items_per_page = 10
        pages = math.ceil(len(player.queue) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue_list = ''
        queue_list += f'**[Now playing].** {self.format_song(player.current)}'
        for i, track in enumerate(player.queue[start:end], start=start):
            queue_list += f'**{i + 1}.** {self.format_song(track)}'

        embed = discord.Embed(
            color=0x2C2F33,
            description=f'🎶 **Queue** - `{len(player.queue)}` tracks\n\n{queue_list}'
        )
        embed.set_footer(text=f'Page {page}/{pages}')
        await ctx.send(embed=embed)

    def format_song(self, track):
        return f'[{track.title}]({track.uri}) {self.bot.get_user(track.requester).mention}\n'
