"""
인증 흐름 통합 테스트
"""
import pytest
import datetime
import pytz
import discord
from unittest.mock import patch, AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_daily_verification_check(verification_service, mock_channel):
    """일일 인증 체크 통합 테스트"""
    # 채널 및 관련 메서드 모킹
    verification_service.bot.get_channel = MagicMock(return_value=mock_channel)
    
    # mock_channel이 TextChannel 타입으로 인식되도록 설정
    mock_channel.__class__ = discord.TextChannel
    
    # 필요한 메서드 직접 모킹
    verification_service.get_verification_data = AsyncMock(return_value=(set([1, 2]), [MagicMock(), MagicMock()]))
    verification_service.send_unverified_messages = AsyncMock()
    
    # time_util의 메서드 모킹
    test_time = datetime.datetime(2023, 5, 1, 15, 0, 0, tzinfo=pytz.timezone('Asia/Seoul'))
    verification_service.time_util.should_skip_check = MagicMock(return_value=False)
    verification_service.time_util.now = MagicMock(return_value=test_time)
    verification_service.time_util.get_today_range = MagicMock(return_value=(
        test_time.replace(hour=12, minute=0),
        test_time
    ))
    
    # 테스트 실행
    await verification_service.check_daily_verification()
    
    # 검증
    verification_service.bot.get_channel.assert_called_once_with(verification_service.config.VERIFICATION_CHANNEL_ID)
    verification_service.get_verification_data.assert_called_once()
    verification_service.send_unverified_messages.assert_called_once()

@pytest.mark.asyncio
async def test_daily_verification_skip_weekend(verification_service):
    """주말 인증 체크 건너뛰기 테스트"""
    # 주말 시간으로 설정
    test_time = datetime.datetime(2023, 5, 6, 15, 0, 0, tzinfo=pytz.timezone('Asia/Seoul'))  # 토요일
    verification_service.time_util.now = MagicMock(return_value=test_time)
    verification_service.time_util.should_skip_check = MagicMock(return_value=True)
    
    # 테스트 실행
    await verification_service.check_daily_verification()
    
    # 검증 - 채널 체크를 하지 않았는지 확인
    verification_service.bot.get_channel.assert_not_called()

@pytest.mark.asyncio
async def test_yesterday_verification_check(verification_service, mock_channel):
    """전일 인증 체크 통합 테스트"""
    # 필요한 모킹 설정
    verification_service.bot.get_channel = MagicMock(return_value=mock_channel)
    verification_service.get_verification_data = AsyncMock(return_value=(set([1, 2]), [MagicMock(), MagicMock()]))
    verification_service.send_unverified_messages = AsyncMock()
    
    # mock_channel이 TextChannel 타입으로 인식되도록 설정
    mock_channel.__class__ = discord.TextChannel
    
    # 평일(화요일) 시간으로 설정
    test_time = datetime.datetime(2023, 5, 2, 9, 0, 0, tzinfo=pytz.timezone('Asia/Seoul'))
    verification_service.time_util.now = MagicMock(return_value=test_time)
    verification_service.time_util.should_skip_check = MagicMock(return_value=False)
    verification_service.time_util.get_check_date_range = MagicMock(return_value=(
        test_time - datetime.timedelta(days=1),
        test_time
    ))
    
    # 테스트 실행
    await verification_service.check_yesterday_verification()
    
    # 검증
    verification_service.bot.get_channel.assert_called_once_with(verification_service.config.VERIFICATION_CHANNEL_ID)
    verification_service.get_verification_data.assert_called_once()
    verification_service.send_unverified_messages.assert_called_once() 