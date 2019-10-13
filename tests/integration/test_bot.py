"""Integration tests for Songlink bot."""
from unittest import mock

from aiogram import types
from aiogram.types import Chat, ChatType, ContentType, Message, User
from aiogram.utils.exceptions import MessageCantBeDeleted
from pytest import mark

from group_songlink_bot.bot import SonglinkBot


def make_mock_message(
    text: str, method_mocks: dict = None, chat_type: ChatType = ChatType.GROUP
) -> mock.Mock:
    """Make a mock message with given text.

    :param text: text of the message
    :param method_mocks: dict of message's method mocks if needed
        {'reply': reply_mock, 'delete': delete_mock, ...}
    :param chat_type: chat type.  See `aiogram.types.ChatType` enum
    :return: mock message
    """
    message = mock.Mock(spec=Message)
    message.content_type = ContentType.TEXT
    message.text = text
    message.from_user = mock.Mock(spec=User)
    message.from_user.username = 'test_user'
    message.chat = mock.Mock(spec=Chat)
    message.chat.type = chat_type
    types.User.set_current(message.from_user)
    types.Chat.set_current(message.chat)
    if method_mocks:
        for method_name, callback in method_mocks.items():
            setattr(message, method_name, callback)
    return message


@mark.usefixtures('loop')
class TestSonglinkBot:
    """Integration tests for Songlink bot."""

    @mark.parametrize('text', ['/start', '/help'])
    async def test_sends_welcome_message(self, bot: SonglinkBot, text):
        """Send a welcome message with supported platforms list in reply to
        /start or /help command.
        """

        async def reply_mock_fn(text, parse_mode):
            assert parse_mode == 'HTML'
            assert text == (
                'Hi!\n'
                "I'm a SongLink Bot. You can message me a link to a "
                'supported music streaming platform and I will respond with '
                'links from all the platforms. If you invite me to a group '
                'chat I will do the same as well as trying to delete original '
                'message (you must promote me to admin to enable this '
                'behavior).\n'
                'Supported platforms: Deezer | Google Music | SoundCloud.\n'
                'Powered by great <a href="https://song.link/">SongLink</a> '
                '(thank you guys!).'
            )

        reply_mock = mock.Mock(side_effect=reply_mock_fn)
        message = make_mock_message(
            text=text, method_mocks={'reply': reply_mock}
        )
        await bot._dp.message_handlers.notify(message)
        assert reply_mock.called

    async def test_replies_to_group_message(self, bot: SonglinkBot):
        """Send reply to a group message."""

        async def reply_mock_fn(text, parse_mode):
            """Message.reply method mock."""
            assert parse_mode == 'HTML'
            assert text == (
                '@test_user wrote: checkout this one: [1]\n'
                '\n'
                '1. Test Artist - Test Title\n'
                '<a href="https://www.test.com/test">Deezer</a> | '
                '<a href="https://www.test.com/test">Google Music</a>'
            )

        async def delete_mock_fn():
            """Message.delete method mock."""
            pass

        reply_mock = mock.Mock(side_effect=reply_mock_fn)
        delete_mock = mock.Mock(side_effect=delete_mock_fn)
        message = make_mock_message(
            text='checkout this one: https://www.deezer.com/track/65760860',
            method_mocks={'reply': reply_mock, 'delete': delete_mock},
        )
        await bot._dp.message_handlers.notify(message)
        assert reply_mock.called
        assert delete_mock.called

    async def test_replies_to_private_message(self, bot: SonglinkBot):
        """Send reply to a private message."""

        async def reply_mock_fn(text, parse_mode):
            """Message.reply method mock."""
            assert parse_mode == 'HTML'
            assert text == (
                '1. Test Artist - Test Title\n'
                '<a href="https://www.test.com/test">Deezer</a> | '
                '<a href="https://www.test.com/test">Google Music</a>'
            )

        reply_mock = mock.Mock(side_effect=reply_mock_fn)
        message = make_mock_message(
            text='checkout this one: https://www.deezer.com/track/65760860',
            method_mocks={'reply': reply_mock},
            chat_type=ChatType.PRIVATE,
        )
        await bot._dp.message_handlers.notify(message)
        assert reply_mock.called

    async def test_skips_message_with_skip_mark(
        self, caplog, bot: SonglinkBot
    ):
        """Skip message if skip mark present."""

        message = make_mock_message(text=f'test message {bot.SKIP_MARK}')
        await bot._dp.message_handlers.notify(message)
        assert 'Message is skipped due to skip mark' in caplog.text

    async def test_logs_if_no_song_links_in_message(
        self, caplog, bot: SonglinkBot
    ):
        """Log and do not reply if message has no song links."""

        message = make_mock_message(text=f'test message without song links')
        await bot._dp.message_handlers.notify(message)
        assert 'No songs found in message' in caplog.text

    async def test_logs_if_cannot_delete_message(
        self, caplog, bot: SonglinkBot
    ):
        """Log if cannot delete the message."""

        async def reply_mock_fn(text, parse_mode):
            """Message.reply method mock."""

        async def delete_mock_fn():
            """Message.delete method mock."""
            raise MessageCantBeDeleted(message='Test exception')

        reply_mock = mock.Mock(side_effect=reply_mock_fn)
        delete_mock = mock.Mock(side_effect=delete_mock_fn)
        message = make_mock_message(
            text='checkout this one: https://www.deezer.com/track/65760860',
            method_mocks={'reply': reply_mock, 'delete': delete_mock},
        )

        await bot._dp.message_handlers.notify(message)
        assert 'Cannot delete message' in caplog.text