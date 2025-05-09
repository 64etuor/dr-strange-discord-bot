"""
설정 관리 모듈
"""
import os
import csv
import logging
import pathlib
import datetime
import pytz
import yaml
from dotenv import load_dotenv

logger = logging.getLogger('verification_bot')

class ConfigManager:
    """설정 관리 클래스"""
    
    def __init__(self, config_file="config.yaml"):
        # 환경 변수 로드
        self.load_dotenv()
        
        # 기본 설정 로드
        self.load_config(config_file)
        self.load_holidays()
        
    def load_dotenv(self):
        """환경 변수 로드"""
        load_dotenv()
        
        # .env 파일에서 중요 정보 로드
        self._load_sensitive_data()
    
    def _load_sensitive_data(self):
        """중요 정보 환경 변수에서 로드"""
        # 기본 중요 정보
        self.TOKEN = os.getenv('DISCORD_TOKEN')
        self.VERIFICATION_CHANNEL_ID = int(os.getenv('VERIFICATION_CHANNEL_ID', '0'))
        self.WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
        
        # 추가적인 데이터베이스 정보 (필요한 경우)
        self.DB_HOST = os.getenv('DB_HOST', '')
        self.DB_PORT = os.getenv('DB_PORT', '')
        self.DB_NAME = os.getenv('DB_NAME', '')
        self.DB_USER = os.getenv('DB_USER', '')
        self.DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    
    def load_config(self, config_file):
        """YAML 설정 파일 로드 (없으면 기본값 사용)"""
        try:
            if pathlib.Path(config_file).exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    self._set_config_values(config)
            else:
                self._set_default_config()
                self._save_default_config(config_file)
        except Exception as e:
            logger.error(f"설정 파일 로드 중 오류: {e}")
            self._set_default_config()
    
    def _set_config_values(self, config):
        """설정 값 적용"""
        # 봇 설정
        bot_config = config.get('bot', {})
        self.BOT_PREFIX = bot_config.get('prefix', '!')
        self.BOT_INTENTS = bot_config.get('intents', {
            'message_content': True,
            'guilds': True,
            'reactions': True,
            'members': True
        })
        
        # 환경 변수 참조 (참조값이 변경된 경우)
        env_config = config.get('env', {})
        token_var = env_config.get('token_var', 'DISCORD_TOKEN')
        verification_channel_id_var = env_config.get('verification_channel_id_var', 'VERIFICATION_CHANNEL_ID')
        webhook_url_var = env_config.get('webhook_url_var', 'WEBHOOK_URL')
        
        # 환경 변수가 config.yaml에서 변경되었다면 새로운 환경 변수 값 로드
        if token_var != 'DISCORD_TOKEN':
            self.TOKEN = os.getenv(token_var, self.TOKEN)
        if verification_channel_id_var != 'VERIFICATION_CHANNEL_ID':
            channel_id = os.getenv(verification_channel_id_var, '0')
            self.VERIFICATION_CHANNEL_ID = int(channel_id)
        if webhook_url_var != 'WEBHOOK_URL':
            self.WEBHOOK_URL = os.getenv(webhook_url_var, self.WEBHOOK_URL)
        
        # 메시지 제한
        self.MAX_MESSAGE_LENGTH = config.get('message_limits', {}).get('max_length', 1900)
        self.MAX_ATTACHMENT_SIZE = config.get('message_limits', {}).get('max_attachment_size', 8 * 1024 * 1024)
        self.MESSAGE_HISTORY_LIMIT = config.get('message_limits', {}).get('history_limit', 1000)
        
        # 재시도 설정
        self.MAX_RETRY_ATTEMPTS = config.get('retry', {}).get('max_attempts', 3)
        self.WEBHOOK_TIMEOUT = config.get('retry', {}).get('webhook_timeout', 10)
        
        # 인증 키워드
        self.VERIFICATION_KEYWORDS = config.get('verification', {}).get('keywords', ["인증사진", "인증 사진"])
        
        # 시간 설정
        timezone_str = config.get('time', {}).get('timezone', 'Asia/Seoul')
        self.TIMEZONE = pytz.timezone(timezone_str)
        
        time_config = config.get('time', {})
        self.DAILY_CHECK_HOUR = time_config.get('daily_check_hour', 22)
        self.DAILY_CHECK_MINUTE = time_config.get('daily_check_minute', 0)
        self.YESTERDAY_CHECK_HOUR = time_config.get('yesterday_check_hour', 9)
        self.YESTERDAY_CHECK_MINUTE = time_config.get('yesterday_check_minute', 0)
        
        self.DAILY_START_HOUR = time_config.get('daily_start_hour', 12)
        self.DAILY_START_MINUTE = time_config.get('daily_start_minute', 0)
        self.DAILY_END_HOUR = time_config.get('daily_end_hour', 3)
        self.DAILY_END_MINUTE = time_config.get('daily_end_minute', 0)
        self.DAILY_END_SECOND = time_config.get('daily_end_second', 0)
        
        # UTC 시간 계산
        self.UTC_DAILY_CHECK_HOUR = (self.DAILY_CHECK_HOUR - 9) % 24
        self.UTC_YESTERDAY_CHECK_HOUR = (self.YESTERDAY_CHECK_HOUR - 9) % 24
        
        # 요일 이름
        self.WEEKDAY_NAMES = time_config.get('weekday_names', ['월', '화', '수', '목', '금', '토', '일'])
        
        # 공휴일 설정
        self.HOLIDAYS_FILE = config.get('holidays', {}).get('file', 'holidays.csv')
        self.SKIP_HOLIDAYS = config.get('holidays', {}).get('skip', True)
        
        # 메시지 템플릿
        self.MESSAGES = config.get('messages', self._get_default_messages())
        
        # 로깅 설정
        logging_config = config.get('logging', {})
        self.LOGGING_LEVEL = logging_config.get('level', 'INFO')
        self.LOGGING_FORMAT = logging_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.LOGGING_FILE = logging_config.get('file', None)
    
    def _set_default_config(self):
        """기본 설정값 설정"""
        defaults = self._get_default_config()
        
        # 봇 설정
        self.BOT_PREFIX = defaults['bot']['prefix']
        self.BOT_INTENTS = defaults['bot']['intents']
        
        # 메시지 제한
        self.MAX_MESSAGE_LENGTH = defaults['message_limits']['max_length']
        self.MAX_ATTACHMENT_SIZE = defaults['message_limits']['max_attachment_size']
        self.MESSAGE_HISTORY_LIMIT = defaults['message_limits']['history_limit']
        
        # 재시도 설정
        self.MAX_RETRY_ATTEMPTS = defaults['retry']['max_attempts']
        self.WEBHOOK_TIMEOUT = defaults['retry']['webhook_timeout']
        
        # 인증 키워드
        self.VERIFICATION_KEYWORDS = defaults['verification']['keywords']
        
        # 시간 설정
        self.TIMEZONE = pytz.timezone(defaults['time']['timezone'])
        
        self.DAILY_CHECK_HOUR = defaults['time']['daily_check_hour']
        self.DAILY_CHECK_MINUTE = defaults['time']['daily_check_minute']
        self.YESTERDAY_CHECK_HOUR = defaults['time']['yesterday_check_hour']
        self.YESTERDAY_CHECK_MINUTE = defaults['time']['yesterday_check_minute']
        
        self.DAILY_START_HOUR = defaults['time']['daily_start_hour']
        self.DAILY_START_MINUTE = defaults['time']['daily_start_minute']
        self.DAILY_END_HOUR = defaults['time']['daily_end_hour']
        self.DAILY_END_MINUTE = defaults['time']['daily_end_minute']
        self.DAILY_END_SECOND = defaults['time']['daily_end_second']
        
        # UTC 시간 계산
        self.UTC_DAILY_CHECK_HOUR = (self.DAILY_CHECK_HOUR - 9) % 24
        self.UTC_YESTERDAY_CHECK_HOUR = (self.YESTERDAY_CHECK_HOUR - 9) % 24
        
        # 요일 이름
        self.WEEKDAY_NAMES = defaults['time']['weekday_names']
        
        # 공휴일 설정
        self.HOLIDAYS_FILE = defaults['holidays']['file']
        self.SKIP_HOLIDAYS = defaults['holidays']['skip']
        
        # 메시지 템플릿
        self.MESSAGES = defaults['messages']
        
        # 로깅 설정
        self.LOGGING_LEVEL = defaults['logging']['level']
        self.LOGGING_FORMAT = defaults['logging']['format']
        self.LOGGING_FILE = defaults['logging']['file']
    
    def _get_default_config(self):
        """기본 설정값을 딕셔너리로 반환"""
        return {
            'bot': {
                'prefix': '!',
                'intents': {
                    'message_content': True,
                    'guilds': True,
                    'reactions': True,
                    'members': True
                }
            },
            'env': {
                'token_var': 'DISCORD_TOKEN',
                'verification_channel_id_var': 'VERIFICATION_CHANNEL_ID',
                'webhook_url_var': 'WEBHOOK_URL'
            },
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
                'keywords': ["인증사진", "인증 사진", "샤따", "샷다운", "인증", "사진"]
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
                'file': 'holidays.csv',
                'skip': True
            },
            'messages': self._get_default_messages(),
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': None
            }
        }
    
    def _save_default_config(self, config_file):
        """기본 설정을 YAML 파일로 저장"""
        try:
            config = self._get_default_config()
            
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            
            logger.info(f"기본 설정 파일 저장: {config_file}")
        except Exception as e:
            logger.error(f"설정 파일 저장 중 오류: {e}")

    def load_holidays(self):
        """공휴일 CSV 파일 로드"""
        self.HOLIDAYS = set()
        
        try:
            holidays_path = pathlib.Path(self.HOLIDAYS_FILE)
            if not holidays_path.exists():
                logger.warning(f"Holidays file not found: {self.HOLIDAYS_FILE}")
                return
                
            with open(self.HOLIDAYS_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date_str = row.get('date', '').strip()
                    if date_str:
                        # YYYY-MM-DD 형식의 날짜를 세트에 추가
                        self.HOLIDAYS.add(date_str)
                        
            logger.info(f"Loaded {len(self.HOLIDAYS)} holidays from {self.HOLIDAYS_FILE}")
        except Exception as e:
            logger.error(f"Error loading holidays: {str(e)}")
    
    def is_holiday(self, date):
        """주어진 날짜가 공휴일인지 확인"""
        date_str = date.strftime('%Y-%m-%d')
        return date_str in self.HOLIDAYS 

    def _get_default_messages(self):
        """기본 메시지 템플릿"""
        return {
            'verification_success': "{name}, Your time has been recorded. The bill comes due. Always!",
            'verification_error': "Verification Error occurred. Please try again.",
            'attach_image_request': "Please attach an image.",
            'daily_check': ("⚠️ 아직 오늘의 인증을 하지 않은 멤버들이에요:\n{members}\n"
                              "자정까지 2시간 남았어요! 오늘의 기록 인증을 올리는 것 잊지 마세요! 💪"),
            'yesterday_check': "⚠️ 어제 인증을 하지 않은 멤버(들)입니다:\n{members}\n벌칙을 수행해 주세요!",
            'all_verified': ("🎉 모든 멤버가 인증을 완료했네요!\n"
                           "💪 여러분의 꾸준한 노력이 멋져요. 내일도 힘내세요! 💫"),
            'permission_error': "❌ 관리자만 사용할 수 있는 명령어입니다.",
            'bot_permission_error': "Bot doesn't have permission to add reactions.",
            'vacation_registered': "🏖️ {date} 날짜가 휴가로 등록되었습니다. 해당 날짜에는 인증 체크에서 제외됩니다.",
            'vacation_already_registered': "⚠️ {date} 날짜는 이미 휴가로 등록되어 있습니다.",
            'vacation_future_only': "❌ 과거 날짜는 휴가로 등록할 수 없습니다.",
            'vacation_invalid_format': "❌ 날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요.",
            'vacation_all_canceled': "✅ 모든 휴가({count}개)가 취소되었습니다.",
            'vacation_none_registered': "ℹ️ 등록된 휴가가 없습니다."
        } 