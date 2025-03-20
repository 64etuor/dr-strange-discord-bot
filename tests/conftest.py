"""
pytest 공통 픽스처 및 설정
"""
import os
import sys

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import tempfile
import yaml
import discord
import datetime
import pytz
from unittest.mock import MagicMock, AsyncMock, PropertyMock

# 상대 경로 대신 절대 경로 사용
from config.config_manager import ConfigManager
from utils.time_utils import TimeUtility
from utils.message_utils import MessageUtility
from services.webhook_service import WebhookService
from services.verification_service import VerificationService

@pytest.fixture
def temp_config_file():
    """임시 설정 파일 생성 픽스처"""
    # 기본 설정 데이터
    config_data = {
        'message_limits': {
            'max_length': 1900,
            'max_attachment_size': 8 * 1024 * 1024,
            'history_limit': 1000
        },
        'retry': {
            'max_attempts': 3,
            'webhook_timeout': 10
        },
        'verification': {
            'keywords': ["인증사진", "인증 사진"]
        },
        'time': {
            'timezone': 'Asia/Seoul',
            'daily_check_hour': 22,
            'daily_check_minute': 0,
            'yesterday_check_hour': 9,
            'yesterday_check_minute': 0,
            'daily_start_hour': 12,
            'daily_start_minute': 0,
            'daily_end_hour': 3,
            'daily_end_minute': 0,
            'daily_end_second': 0,
            'weekday_names': ['월', '화', '수', '목', '금', '토', '일']
        },
        'holidays': {
            'file': 'test_holidays.csv',
            'skip': True
        },
        'messages': {
            'verification_success': "{name}, Your time has been recorded. The bill comes due. Always!",
            'verification_error': "Verification Error occurred. Please try again.",
            'attach_image_request': "Please attach an image.",
            'unverified_daily': "⚠️ 아직 오늘의 인증을 하지 않은 멤버들이에요:\n{members}\n자정까지 2시간 남았어요!",
            'unverified_yesterday': "⚠️ 어제 인증을 하지 않은 멤버(들)입니다:\n{members}\n벌칙을 수행해 주세요!",
            'unverified_friday': "⚠️ 지난 주 금요일 인증을 하지 않은 멤버(들)입니다:\n{members}\n벌칙을 수행해 주세요!",
            'all_verified': "🎉 모든 멤버가 인증을 완료했네요!\n💪 여러분의 꾸준한 노력이 멋져요. 내일도 힘내세요! 💫",
            'permission_error': "❌ 관리자만 사용할 수 있는 명령어입니다.",
            'bot_permission_error': "Bot doesn't have permission to add reactions."
        }
    }
    
    # 임시 디렉토리 생성
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = os.path.join(temp_dir, "test_config.yaml")
        
        # 설정 파일 작성
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, allow_unicode=True)
        
        # 임시 holidays 파일 생성
        holidays_path = os.path.join(temp_dir, "test_holidays.csv")
        with open(holidays_path, 'w', encoding='utf-8') as f:
            f.write("index,date,holiday name\n")
            f.write("1,2025-01-01,신정(양력설)\n")
            f.write("2,2025-05-05,어린이날\n")
        
        yield config_path

@pytest.fixture
def mock_channel():
    """Mocked 디스코드 채널"""
    channel = MagicMock()
    channel.name = "test-channel"
    channel.send = AsyncMock()
    
    # TextChannel로 인식되도록 설정
    channel.__class__ = discord.TextChannel
    
    # 권한 설정
    permissions = MagicMock()
    permissions.read_message_history = True
    permissions.view_channel = True
    permissions.send_messages = True
    permissions.add_reactions = True
    
    # guild.me 설정
    guild = MagicMock()
    guild.me = MagicMock()
    channel.guild = guild
    
    # permissions_for 설정
    channel.permissions_for = MagicMock(return_value=permissions)
    
    return channel

@pytest.fixture
def temp_holidays_file():
    """임시 공휴일 파일 생성"""
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.csv') as f:
        f.write("index,date,holiday name\n")
        f.write("1,2025-01-01,신정(양력설)\n")
        f.write("2,2025-05-05,어린이날\n")
        filename = f.name
    
    yield filename
    
    # 테스트 후 파일 삭제
    os.unlink(filename)

@pytest.fixture
def config_manager(temp_config_file):
    """설정 관리자 픽스처"""
    # 환경 변수 설정
    os.environ['DISCORD_TOKEN'] = 'test_token'
    os.environ['VERIFICATION_CHANNEL_ID'] = '123456789'
    os.environ['WEBHOOK_URL'] = 'https://test.webhook.url'
    
    # 임시 공휴일 파일 생성
    holidays_file = tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.csv')
    holidays_file.write("index,date,holiday name\n")
    holidays_file.write("1,2025-01-01,신정(양력설)\n")
    holidays_file.write("2,2025-05-05,어린이날\n")
    holidays_file.close()
    
    # 설정 관리자 생성
    config = ConfigManager(config_file=temp_config_file)
    
    # 공휴일 파일 경로 직접 설정
    config.HOLIDAYS_FILE = holidays_file.name
    config.load_holidays()
    
    yield config
    
    # 테스트 후 임시 파일 삭제
    os.unlink(holidays_file.name)

@pytest.fixture
def time_util(config_manager):
    """시간 유틸리티 픽스처"""
    return TimeUtility(config_manager)

@pytest.fixture
def message_util(config_manager):
    """메시지 유틸리티 픽스처"""
    return MessageUtility(config_manager)

@pytest.fixture
def mock_session():
    """Mocked aiohttp.ClientSession"""
    session = AsyncMock()
    
    # 응답 모킹
    response = AsyncMock()
    response.status = 200
    response.text = AsyncMock(return_value="Success")
    
    # context manager 모킹
    cm = AsyncMock()
    cm.__aenter__.return_value = response
    
    session.post = AsyncMock(return_value=cm)
    session.close = AsyncMock()
    
    return session

@pytest.fixture
def webhook_service(config_manager):
    """웹훅 서비스 픽스처"""
    service = WebhookService(config_manager)
    service.initialize = AsyncMock()  # initialize 메서드 모킹
    
    # 세션 모킹
    session = AsyncMock()
    response = AsyncMock()
    response.status = 200
    response.text = AsyncMock(return_value="Success")
    
    cm = AsyncMock()
    cm.__aenter__.return_value = response
    
    session.post = AsyncMock(return_value=cm)
    service.session = session
    
    return service

@pytest.fixture
def mock_bot():
    """Mocked 디스코드 봇"""
    bot = MagicMock()
    bot.get_channel = MagicMock()
    return bot

@pytest.fixture
def verification_service(config_manager, mock_bot, message_util, time_util, webhook_service):
    """인증 서비스 픽스처"""
    return VerificationService(config_manager, mock_bot, message_util, time_util, webhook_service)

@pytest.fixture
def test_kst_time():
    """테스트용 KST 시간"""
    # 2023-05-01 15:00:00 KST (평일, 월요일)
    return datetime.datetime(2023, 5, 1, 15, 0, 0, tzinfo=pytz.timezone('Asia/Seoul')) 