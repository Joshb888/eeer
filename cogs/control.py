from threading import Timer

import discord
import lavalink
from discord.errors import NotFound
from discord.ext import commands

from utilities import checks


class Control:
    def __init__(self, user, guild, message, player, channel_id, bot, voice_channel_id=None):
        self.user = user
        self.guild = guild
        self.message = message
        self.channel_id = channel_id
        self.player = player
        self.voice_channel_id = voice_channel_id
        self.bot = bot

    async def handle_reaction(self, reaction):
        emoji = reaction.emoji
        if emoji == '⏯':
            resume_response = '✅ | Successfully resumed the music!' if self.player.paused else \
                '✅ | Successfully paused music!'
            await self.player.set_pause(not self.player.paused)
            await self.send_response(resume_response)
        elif emoji == '⏭':
            await self.player.skip()
            await self.send_response('✅ | Successfully skipped current song!')
        elif emoji == '⏹':
            self.player.queue.clear()
            await self.player.stop()
            await self.send_response('✅ | Successfully stopped the music!')
        elif emoji == '🔂':
            repeat_response = '✅ | Successfully enabled loop mode!' if not self.player.repeat else \
                '✅ | Successfully disabled loop mode!'
            self.player.repeat = not self.player.repeat
            await self.send_response(repeat_response)
        elif emoji == '🔁':
            loop_queue_status = await self.player.toggle_loop_queue
            response = '✅ | Successfully enabled loopqueue mode!' if not loop_queue_status else \
                '✅ | Successfully disabled loopqueue mode!'
            await self.send_response(response)
        elif emoji == '🔀':
            shuffle_response = '✅ | Successfully enabled shuffle mode!' if not self.player.shuffle else \
                '✅ | Successfully disabled shuffle mode!'
            self.player.shuffle = not self.player.shuffle
            await self.send_response(shuffle_response)
        elif emoji == '🔄':
            await self.player.seek(0)
            await self.send_response('✅ | Successfully reset the current progress!')
        elif emoji == '🔊':
            if self.player.volume == 150:
                return await self.send_response('🚫 | The volume is already at the maximum!')
            elif self.player.volume >= 490:
                await self.player.set_volume(150)
            else:
                await self.player.set_volume(self.player.volume + 10)
            await self.send_response(f'✅ | Successfully set volume to `{self.player.volume}`!')
        elif emoji == '🔉':
            if self.player.volume == 0:
                return await self.send_response('🚫 | The volume is already at the minimum!')
            elif self.player.volume <= 10:
                await self.player.set_volume(0)
            else:
                await self.player.set_volume(self.player.volume - 10)
            await self.send_response(f'✅ | Successfully set volume to `{self.player.volume}`!')
        await self.update_message(False)

    async def send_response(self, response):
        async with self.channel.typing():
            message = await self.channel.send(response)

        def del_message():
            try:
                self.bot.loop.create_task(message.delete())
            except NotFound:
                pass

        Timer(2, del_message)

    async def update_message(self, loop):
        if self.player.current is None:
            if self.message:
                try:
                    return await self.message.delete()
                except NotFound:
                    return
            del self
            return
        pos = lavalink.Utils.format_time(self.player.position)
        if self.player.current.stream:
            dur = 'LIVE'
        else:
            dur = lavalink.Utils.format_time(self.player.current.duration)
        play_type = '⏸' if self.player.paused else '▶'
        loop_type = '🔂' if self.player.repeat else ''
        loopqueue_type = '🔁' if await self.player.loop_queue else ''
        shuffle_type = '🔀' if self.player.shuffle else ''

        song = self.player.current

        desc = f'🎶 **{song.title}** (**{song.author}**)\n\n' \
               f'{play_type}{loop_type}{loopqueue_type}{shuffle_type} ' \
               f'{self.get_percentage(self.player.position, song.duration)} **[{pos} / {dur}]**'

        embed = discord.Embed(
            color=0x2C2F33,
            description=desc
        )

        try:
            await self.message.edit(embed=embed)
        except NotFound:
            pass
        if loop:
            def up_message():
                if self.message:
                    self.bot.loop.create_task(self.update_message(True))

            Timer(5.0, up_message).start()

    @property
    def whitelisted_members(self):
        out = list({})
        for member in self.voice_channel.members:
            out.append(member.id)
        return out

    @property
    def channel(self):
        return self.guild.get_channel(self.channel_id)

    @property
    def voice_channel(self):
        return self.guild.get_channel(self.voice_channel_id)

    @staticmethod
    def get_percentage(progress, full):
        percent = round(progress / full, 2)
        bar = ''
        for x in range(0, 15):
            if int(percent * 15) == x:
                bar += '🔘'
            else:
                bar += '▬'
        return bar


class ControlCommand:
    def __init__(self, bot):
        self.bot = bot
        self.map = dict({})
        self.reacts = ['⏯', '⏭', '⏹', '🔂', '🔁', '🔀', '🔄', '🔉', '🔊']

    @commands.command(aliases=['cp', 'panel'])
    @checks.dj_only()
    async def control(self, ctx):
        if ctx.guild.id in self.map.keys():
            msg = await ctx.send('🚫 | You are already using an instance of the control panel on this guild! '
                                 'Dou you want to reset it?')
            await msg.add_reaction('✅')
            await msg.add_reaction('❌')

            def check(r, u):
                return u.id == ctx.author.id and r.message.id == msg.id

            reaction, user = await self.bot.wait_for('reaction_add', check=check)
            if reaction.emoji == '❌':
                return await msg.delete()
            elif reaction.emoji == '✅':
                if user.id not in self.map[ctx.guild.id].whitelisted_members:
                    return await ctx.send('🚫 | You\'re not allowed to use this command')
                else:
                    await msg.delete()
                    if self.map[ctx.guild.id].message is not None:
                        await self.map[ctx.guild.id].message.delete()

        permissions = ctx.author.voice.channel.permissions_for(ctx.me)
        if not permissions.manage_messages:
            return await ctx.send(':no_entry_sign: Please give me the `MESSAGE_MANAGE` permission to use that command')

        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.is_playing:
            return await ctx.send('🚫 | I\'m not playing.')

        embed = discord.Embed(
            title=f'Control Panel - Loading',
            color=0x2C2F33,
            description='<a:groovyloading:487681291010179072> Please wait while the control panel is loading ...'
        )

        msg = await ctx.send(embed=embed)

        for react in self.reacts:
            await msg.add_reaction(react)

        panel = Control(ctx.message.author, ctx.guild, msg, player, ctx.channel.id, self.bot, ctx.guild.me.voice.channel.id)
        self.map[ctx.guild.id] = panel
        await panel.update_message(True)

    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        if reaction.message.guild.id not in self.map:
            return
        user_panel = self.map[reaction.message.guild.id]
        if user_panel.message.id != reaction.message.id:
            return
        await reaction.message.remove_reaction(reaction.emoji, user)
        if reaction.emoji not in self.reacts:
            return
        if user.id not in user_panel.whitelisted_members:
            return
        await user_panel.handle_reaction(reaction)

    async def on_message_delete(self, message):
        if message.guild.id in self.map.keys():
            user_panel = self.map[message.guild.id]
            if user_panel.message.id == message.id:
                del self.map[message.guild.id]


def setup(bot):
    bot.add_cog(ControlCommand(bot))
