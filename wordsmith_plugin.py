import asyncio
import random

import irc3
from irc3.plugins.command import command


class Game:
    def __init__(self, available_words, channel):
        self.available_words = set(available_words)
        self.channel = channel

        self.turn_count = 0
        self.free_tiles = []

        self.clear_current_words()

    def clear_current_words(self):
        self.current_words = []

    def remove_available_word(self, word):
        word = word.upper()

        try:
            self.available_words.remove(word)
            print('Removing word:', word)
        except (KeyError, ValueError):
            pass

    def add_words(self, words):
        for word in words:
            word = word.upper()

            self.remove_available_word(word)
            self.current_words.append(word)

    def next_action(self):
        if self.turn_count > 10:
            return '\\\\end'
        else:
            self.turn_count += 1
            return '\\\\turn'

    def is_word_possible(self, word, all_of=None, some_of=None):
        if all_of is None and some_of is None:
            raise ValueError('Cannot both be none.')

        all_of_tiles = list(all_of or [])
        some_of_tiles = list(some_of or [])

        for ch in word:
            if ch in all_of_tiles:
                all_of_tiles.remove(ch)
            elif '@' in all_of_tiles:
                all_of_tiles.remove('@')
            elif ch in some_of_tiles:
                some_of_tiles.remove(ch)
            elif '@' in some_of_tiles:
                some_of_tiles.remove('@')
            else:
                return False

        if all_of_tiles:  # some tiles left
            return False

        return True

    def find_new_word(self):
        print('Finding new word...')

        l = len(self.free_tiles)
        for word in self.available_words:
            if len(word) <= l:
                if self.is_word_possible(word, some_of=self.free_tiles):
                    return word

    def find_anagram(self):
        print('Finding an anagram...')

        l = len(self.free_tiles)
        for existing_word in self.current_words:
            for word in self.available_words:
                if len(word) >= len(existing_word) and len(word) <= len(existing_word) + l:
                    if self.is_word_possible(word, all_of=existing_word,
                                             some_of=self.free_tiles):
                        return word

    def find_word(self):
        word = self.find_anagram()
        if word is None:
            word = self.find_new_word()

        if word is not None:
            self.turn_count = 0
            self.remove_available_word(word)

        return word


@irc3.plugin
class Plugin(object):

    def __init__(self, bot):
        self.bot = bot

        self.game = None
        self.game_bot = None

        with open('dictionary.txt') as file:
            self.words = []
            for line in file:
                word = line.strip()
                if len(word) >= 3:
                    self.words.append(word.upper())

    @irc3.event(irc3.rfc.JOIN)
    def on_join(self, mask, channel, **kwargs):
        """Introduce self when I join a channel."""

        if mask.nick == self.bot.nick:
            self.bot.privmsg(channel, 'I like Grabble!')
            self.announce_word(channel)

    @irc3.event(irc3.rfc.PRIVMSG)
    def on_privmsg(self, mask, target, data, **kwargs):
        if self.game is None:
            return

        if target != self.game.channel:
            return

        if self.game_bot is None:
            if 'New game started!' in data or 'Game in progress!' in data:
                self.game_bot = mask.nick
            if self.game_bot is None:
                return

        if mask.nick != self.game_bot:
            return

        if 'Game ended!' in data:
            self.game = None
        elif 'Final Scores:' in data:
            pass
        elif 'Game in progress!' in data:
            self.bot.privmsg(self.game.channel, 'Great!')
        elif 'New game started!' in data:
            self.bot.privmsg(self.game.channel, 'Yay! Grabble!')
            self.bot.privmsg(self.game.channel, '\\\\turn')
        elif data.startswith('Player') and data.endswith('removed!'):
            self.bot.privmsg(self.game.channel, 'Bye bye.')
        elif 'has requested game end.' in data:
            msg = "Hmm. I don't think I'm quite ready to end yet."
            self.bot.privmsg(self.game.channel, msg)
        elif data.startswith('Flipped:'):
            characters = data[9:data.index('(')].strip()
            tiles = [x.strip() for x in characters.split()]
            self.game.free_tiles = tiles
        elif data.startswith('Current turn:'):
            player = data[13:].strip()
            print('Current player:', player)
            if player == self.bot.nick:
                self.bot.loop.call_later(3, self.speak, self.game.channel,
                                         self.game.next_action())
        elif 'is not a word!' in data:
            word = data[:data.index('is not')].strip().upper()

            try:
                self.words.remove(word)
            except (KeyError, ValueError):
                pass

            self.game.remove_available_word(word)
        elif 'is not possible to make!' in data:
            word = data[:data.index('is not')].strip().upper()

            self.game.remove_available_word(word)
        elif ';' in data:
            self.game.clear_current_words()

            players = data.split(';')
            for player in players:
                tokens = player.split(':')
                if len(tokens) < 2:
                    continue

                name = tokens[0].strip()
                words = tokens[1].strip().split()
                self.game.add_words(words)
        elif "It's {}'s go, not yours!".format(self.bot.nick) in data:
            self.bot.privmsg(self.game.channel, self.game.next_action())
        elif 'won' in data and '!' in data:  # x won y
            player = data[0:data.index(' won ')].strip()
            word = data[data.index(' won ') + 5:-1].strip()
            self.game.add_words([word])
        else:
            print('Argh!', data)

    def play_loop(self):
        if self.game is None:
            return

        word = self.game.find_word()
        if word is not None:
            self.bot.privmsg(self.game.channel, '\\' + word)

        self.bot.loop.call_later(5, self.play_loop)

    def speak(self, channel, message):
        self.bot.privmsg(channel, message)

    @command
    def play_grabble(self, mask, target, args):
        """
        Play Grabble.

        %%play_grabble
        """

        if irc3.utils.IrcString(target).is_nick:
            self.bot.privmsg(mask.nick, "You're not a channel.")

        if self.game is not None:
            self.bot.privmsg(target, "I'm already playing.")

        self.game = Game(self.words, target)
        self.bot.privmsg(target, '\\\\start')
        self.bot.loop.call_soon(self.play_loop)

    @command
    def stop_grabble(self, mask, target, args):
        """
        Stop playing Grabble.

        %%stop_grabble
        """

        if irc3.utils.IrcString(target).is_nick:
            self.bot.privmsg(mask.nick, "You're not a channel.")

        if self.game is None:
            self.bot.privmsg(target, "I'm not playing.")

        self.bot.privmsg(self.game.channel, '\\\\leave')
        self.game = None

    def announce_word(self, channel):
        p = ['great', 'fantastic', 'amazing', 'lovely', 'nice', 'excellent']
        word = random.choice(self.words)
        sentence = "Do you know what's a {} word? {}".format(random.choice(p),
                                                             word.lower())
        self.bot.privmsg(channel, sentence)

        delay = random.randint(0, 24 * 60 * 60)
        self.bot.loop.call_later(delay, self.announce_word, channel)
