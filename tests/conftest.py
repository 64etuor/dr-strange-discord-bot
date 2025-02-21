import pytest
import asyncio
import discord
from unittest.mock import MagicMock, AsyncMock
from index import VerificationBot

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def bot():
    """봇 객체를 직접 반환하는 fixture"""
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    
    # AsyncMock 사용하여 비동기 메서드 모킹
    bot = MagicMock(spec=VerificationBot)
    bot.on_message = AsyncMock()
    bot.get_channel = MagicMock()
    bot.check_yesterday_verification = AsyncMock()
    return bot

@pytest.fixture
def mock_channel():
    channel = MagicMock()
    channel.id = 1342318912645234689
    channel.send = AsyncMock()  # send도 비동기 메서드
    return channel

@pytest.fixture
def mock_message(mock_channel):
    message = MagicMock()
    message.channel = mock_channel
    message.author.bot = False
    message.add_reaction = AsyncMock()  # add_reaction도 비동기 메서드
    return message 