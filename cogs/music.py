import json
import logging
import re
from threading import Timer

import discord
import lavalink

from utilities import checks

time_rx = re.compile('[0-9]+')
url_rx = re.compile("https?://(?:www\.)?.+")


class Music:
    def __init__(self, bot):
        self.bot = bot

        if not hasattr(bot, 'lavalink'):
            lavalink.Client(bot=bot, host=bot.get_config()['lavalink']['host'],
                            ws_port=bot.get_config()['lavalink']['port'],
                            password=bot.get_config()['lavalink']['password'], loop=self.bot.loop,
                            log_level=logging.INFO)
        self.bot.lavalink.register_hook(self.track_hook)

    async def track_hook(self, event):
        if isinstance(event, lavalink.Events.TrackStartEvent):
            await event.player.set_volvoume(100)
            c = event.player.fetch('channel')
            if c:
                c = self.bot.get_channel(c)
                if c:
                    embed = discord.Embed(
                        color=0x2C2F33,
                        title='🎶 Now Playing',
                        description=f'{event.track.title} ({event.track.author})'
                    )
                    embed.set_thumbnail(url=event.track.thumbnail)
                    await c.send(embed=embed)
        elif isinstance(event, lavalink.Events.QueueEndEvent):
            if self.bot.is_updating():
                return
            c = event.player.fetch('channel')
            if c:
                c = self.bot.get_channel(c)
                if c:
                    await c.send('✅ | The queue has ended! Why not queue more songs?')
            Timer(function=self.disconnect, interval=300.0, args=event.player).start()
        elif isinstance(event, lavalink.Events.TrackEndEvent):
            loop_queue_status = await event.player.loop_queue
            if loop_queue_status:
                # Ignore reason 'REPLACED' to do not requeue songs again after they got skipped
                if event.reason == 'FINISHED':
                    track = await self.decode_base64_track(event.track)
                    event.player.add(requester=self.bot.user.id, track=track)
                    if not event.player.is_playing:
                        await event.player.play()

    @staticmethod
    async def check_connect(context, player):
        if not player.is_connected:
            if not context.author.voice or not context.author.voice.channel:
                return await context.send('🚫 | Join a voice channel!')

            permissions = context.author.voice.channel.permissions_for(context.me)

            if not permissions.connect or not permissions.speak:
                return await context.send('🚫 | Missing permissions `CONNECT` and/or `SPEAK`.')

            player.store('channel', context.channel.id)
            await player.connect(context.author.voice.channel.id)
        else:
            if not context.author.voice or not context.author.voice.channel or player.connected_channel.id \
                    != context.author.voice.channel.id:
                return await context.send('🚫 | Join my voice channel!')

    async def decode_base64_track(self, track):
        headers = {
            "Authorization": self.bot.get_config()['lavalink']['password'],
            "Content-Type": "application/json"
        }
        params = f'["{track}"]'
        lavalink_host = self.bot.get_config()['lavalink']['host']
        lavalink_port = 2333
        async with self.bot.session.post(f'http://{lavalink_host}:{lavalink_port}/decodetracks', data=params,
                                         headers=headers) as track_response:
            track_raw = await track_response.text()
            track = json.loads(track_raw)[0]
            return track

    def disconnect(self, player):
        if not player.current and player.channel_id != '486765249488224277':
            self.bot.loop.create_task(player.disconnect())

    @staticmethod
    async def get_tracks(bot, query, ctx):
        query = query.strip('<>')

        if not url_rx.match(query):
            query = f'ytsearch:{query}'

        results = await bot.lavalink.get_tracks(query)

        if not results or not results['tracks']:
            return await ctx.send('🚫 | Nothing found!')
        return results

    @staticmethod
    async def get_player(bot, guild_id=None, ctx=None):
        if ctx is None:
            player = bot.lavalink.players.get(guild_id)
        elif guild_id is None:
            player = bot.lavalink.players.get(ctx.guild.id)
        else:
            return -1
        guild = await bot.guild_cache.get(guild_id)
        await player.set_volume(guild.volume)
        return player

    @staticmethod
    async def enqueue_songs(player, results, ctx, start=None):
        if len(player.queue) >= 20:
            patreon_type = await checks.get_premium_type(ctx.author.id, ctx.bot.postgre_client.get_pool())
            if patreon_type is None or patreon_type < 2:
                return await ctx.send(
                    '🚫 | **The queue reached a total length of 20 or more songs!**\n\n'
                    'If you want to add more than 20 songs to the queue you need to donate at '
                    'https://patreon.com/rxsto\n'
                    'If you already are a patron register at https://premium.groovybot.gq/ '
                )

        track = results['tracks'][0]

        duration = track['info']['length']

        if duration > 3600000:
            patreon_type = await checks.get_premium_type(ctx.author.id, ctx.bot.postgre_client.get_pool())
            if patreon_type is None or patreon_type < 2:
                return await ctx.send(
                    '🚫 | **This song is longer than 1 hour!**\n\n'
                    'If you want to add songs which are longer than 1 hour to the queue you need to donate at '
                    'https://patreon.com/rxsto\n'
                    'If you already are a patron register at https://premium.groovybot.gq/ '
                )

        success_message = f'🎶 **Track enqueued:** {track["info"]["title"]}'
        await ctx.send(success_message)
        if start is None:
            player.add(requester=ctx.author.id, track=track)
        else:
            player.queue.insert(0, lavalink.AudioTrack().build(track, ctx.author.id))

    async def on_voice_state_update(self, member, before, after):
        if before.channel is None:
            return
        if member.guild.me not in before.channel.members:
            return
        if after.channel is None or after.channel.id != before.channel.id:
            channel = before.channel
            player = await self.get_player(bot=self.bot, guild_id=member.guild.id)
            if len(before.channel.members) == 1 and player.is_connected:
                Timer(60.0 * 5, self.run_check, [player, channel]).start()

    def run_check(self, player, channel):
        if len(channel.members) == 1 and player.is_connected:
            self.bot.loop.create_task(player.disconnect())


def setup(bot):
    bot.add_cog(Music(bot))
