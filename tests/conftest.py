"""
pytest 공통 픽스처 및 설정
"""
import os
import sys
import pytest
import tempfile
import yaml
import discord
import datetime
import pytz
from unittest.mock import MagicMock, AsyncMock
import csv
import warnings

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config_manager import ConfigManager
from time_utils import TimeUtility
from message_utils import MessageUtility
from webhook_service import WebhookService
from verification_service import VerificationService

# 경고 필터 설정
def pytest_configure(config):
    # 모든 DeprecationWarning 무시 (discord.player 관련)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    # 비동기 코루틴 경고 무시
    warnings.filterwarnings("ignore", category=RuntimeWarning, message="coroutine.*was never awaited")
    
    # 리소스 경고 무시
    warnings.filterwarnings("ignore", category=ResourceWarning)

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
        
        yield config_path

@pytest.fixture(scope="session")
def temp_holiday_file():
    """테스트용 임시 공휴일 파일 생성"""
    # 임시 디렉토리에 파일 생성
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        writer = csv.writer(f)
        writer.writerow(['date'])
        writer.writerow(['2023-01-01'])
        writer.writerow(['2023-05-05'])
        writer.writerow(['2023-08-15'])
        writer.writerow(['2023-12-25'])
        writer.writerow(['2025-01-01'])  # test_should_skip_check를 위해 추가
        holiday_file = f.name
    
    yield holiday_file
    
    # 테스트 후 파일 삭제
    os.unlink(holiday_file)

@pytest.fixture
def config_manager(temp_config_file, temp_holiday_file):
    """설정 관리자 픽스처"""
    # 환경 변수 설정
    os.environ['DISCORD_TOKEN'] = 'test_token'
    os.environ['VERIFICATION_CHANNEL_ID'] = '123456789'
    os.environ['WEBHOOK_URL'] = 'https://test.webhook.url'
    
    # 설정 관리자 생성
    config = ConfigManager(config_file=temp_config_file)
    
    # 임시 공휴일 파일 경로 설정
    config.HOLIDAYS_FILE = temp_holiday_file
    config.load_holidays()  # 공휴일 다시 로드
    
    return config

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
    context_manager = AsyncMock()
    context_manager.__aenter__.return_value = response
    
    session.post = AsyncMock(return_value=context_manager)
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
def mock_channel():
    """채널 모의 객체"""
    channel = AsyncMock(spec=discord.TextChannel)
    return channel

@pytest.fixture
def mock_bot():
    """Mocked 디스코드 봇"""
    bot = MagicMock()
    bot.get_channel = MagicMock()
    return bot

@pytest.fixture
def verification_service(mock_config, mock_discord_client, message_util, mock_time_util, mock_webhook_service):
    """VerificationService 객체"""
    from verification_service import VerificationService
    mock_discord_client.vacation_users = {}
    return VerificationService(
        mock_config, mock_discord_client, message_util, mock_time_util, mock_webhook_service
    )

@pytest.fixture
def test_kst_time():
    """테스트용 KST 시간"""
    # 2023-05-01 15:00:00 KST (평일, 월요일)
    return datetime.datetime(2023, 5, 1, 15, 0, 0, tzinfo=pytz.timezone('Asia/Seoul'))

@pytest.fixture
def mock_discord_client():
    """Discord 클라이언트 모의 객체"""
    client = MagicMock()
    client.guilds = []
    return client

@pytest.fixture
def mock_config(temp_holiday_file):
    """설정 모의 객체"""
    config = MagicMock()
    config.TOKEN = "test_token"
    config.VERIFICATION_CHANNEL_ID = 123456
    config.WEBHOOK_URL = "https://example.com/webhook"
    config.HOLIDAY_FILE = temp_holiday_file
    config.VERIFICATION_KEYWORDS = ["인증사진", "인증 사진"]
    config.MAX_ATTACHMENT_SIZE = 8 * 1024 * 1024
    config.MAX_MESSAGE_LENGTH = 2000
    config.MESSAGE_HISTORY_LIMIT = 1000
    config.SKIP_HOLIDAYS = True
    config.SKIP_WEEKENDS = True
    config.HOLIDAYS = set(["2023-01-01", "2023-05-05", "2023-08-15", "2023-12-25"])
    
    config.DAILY_CHECK_HOUR = 22
    config.DAILY_CHECK_MINUTE = 0
    config.YESTERDAY_CHECK_HOUR = 9
    config.YESTERDAY_CHECK_MINUTE = 0
    
    config.UTC_DAILY_CHECK_HOUR = 13
    config.UTC_YESTERDAY_CHECK_HOUR = 0
    
    config.DAILY_START_HOUR = 12
    config.DAILY_START_MINUTE = 0
    config.DAILY_END_HOUR = 3
    config.DAILY_END_MINUTE = 0
    config.DAILY_END_SECOND = 0
    
    config.MESSAGES = {
        "verification_success": "{name}님의 인증이 완료되었습니다.",
        "attach_image_request": "이미지를 첨부해주세요.",
        "verification_error": "인증 중 오류가 발생했습니다.",
        "bot_permission_error": "봇에 필요한 권한이 없습니다.",
        "all_verified": "모든 멤버가 인증을 완료했습니다.",
        "unverified_daily": "{members}님, 오늘 인증을 완료해주세요.",
        "unverified_yesterday": "{members}님, 어제 인증을 하지 않았습니다.",
        "unverified_friday": "{members}님, 금요일 인증을 하지 않았습니다.",
        "permission_error": "이 명령어를 사용할 권한이 없습니다."
    }
    
    config.is_holiday = lambda date: date.strftime('%Y-%m-%d') in config.HOLIDAYS
    config.load_holidays = MagicMock()
    
    return config

@pytest.fixture
def mock_time_util():
    """시간 유틸리티 모의 객체"""
    from time_utils import TimeUtility
    time_util = MagicMock(spec=TimeUtility)
    
    # 현재 시간 설정
    now = datetime.datetime(2023, 1, 10, 15, 0)  # 2023년 1월 10일 15시 (평일)
    time_util.now.return_value = now
    
    # 주말 체크
    time_util.is_weekend.return_value = False
    
    # 날짜 범위 설정
    time_util.get_today_range.return_value = (
        datetime.datetime(2023, 1, 10, 12, 0),
        datetime.datetime(2023, 1, 11, 3, 0)
    )
    
    time_util.should_skip_check.return_value = False
    
    return time_util

@pytest.fixture
def mock_message_util(mock_config):
    """메시지 유틸리티 모의 객체"""
    from message_utils import MessageUtility
    return MessageUtility(mock_config)

@pytest.fixture
def mock_webhook_service():
    """웹훅 서비스 모의 객체"""
    webhook_service = AsyncMock()
    webhook_service.send_webhook.return_value = True
    webhook_service.initialize = AsyncMock()
    webhook_service.cleanup = AsyncMock()
    return webhook_service

@pytest.fixture
def mock_verification_service(mock_config, mock_discord_client, mock_message_util, mock_time_util, mock_webhook_service):
    """VerificationService 모의 객체"""
    from verification_service import VerificationService
    mock_discord_client.vacation_users = {}
    return VerificationService(
        mock_config, mock_discord_client, mock_message_util, mock_time_util, mock_webhook_service
    ) 