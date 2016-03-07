import asyncio
import random

import irc3
from irc3.plugins.command import command


@irc3.plugin
class Plugin(object):

    def __init__(self, bot):
        self.bot = bot

        with open('dictionary.txt') as file:
            self.words = list(file)

    @irc3.event(irc3.rfc.JOIN)
    def say_hi(self, mask, channel, **kw):
        """Introduce self when I join a channel."""

        if mask.nick == self.bot.nick:
            self.bot.privmsg(channel, 'I like Grabble!')
            self.announce_word(channel)

    @command
    def play(self, mask, target, args):
        """
        Play Grabble.

        %%play
        """

        self.bot.privmsg(target, '\\\\play')

    def announce_word(self, channel):
        p = ['great', 'fantastic', 'amazing', 'lovely', 'nice', 'excellent']
        word = random.choice(self.words)
        sentence = "Do you know what's a {} word? {}".format(random.choice(p),
                                                             word)
        self.bot.privmsg(channel, sentence)

        delay = random.randint(0, 24 * 60 * 60)
        self.bot.loop.call_later(delay, self.announce_word, channel)
