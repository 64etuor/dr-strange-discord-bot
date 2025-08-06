"""
설정 관리 모듈 - config.yaml 기반
"""
import pathlib
import pytz
import yaml
import os
from dotenv import load_dotenv
from db import DatabaseManager, HolidayManager, VacationManager, VerificationManager
from db.migration import DataMigration
from logging_utils import configure_logging, get_logger

# 로거 초기화
logger = configure_logging()

class ConfigManager:
    """config.yaml 기반 설정 관리 클래스"""
    
    def __init__(self, config_file="config.yaml"):
        self.config_file = config_file
        
        # .env 파일 로드
        load_dotenv()
        
        # 설정 파일 로드
        self.load_config()
        
        # 데이터베이스 매니저 초기화
        self.db_manager = DatabaseManager()
        self.holiday_manager = HolidayManager(self.db_manager)
        self.vacation_manager = VacationManager(self.db_manager)
        self.verification_manager = VerificationManager(self.db_manager)
        
        # 공휴일 로드
        self.load_holidays()
        
        # 인증 설정 검증
        self.validate_config()
    
    def load_config(self):
        """config.yaml 파일 로드"""
        try:
            if not pathlib.Path(self.config_file).exists():
                raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {self.config_file}")
                
            with open(self.config_file, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.info(f"설정 파일 내용 길이: {len(content)}")
                config = yaml.safe_load(content)
                
                if config is None:
                    raise ValueError("YAML 파일이 비어있거나 파싱할 수 없습니다.")
                    
                self._set_config_values(config)
                
            logger.info(f"설정 파일 로드 완료: {self.config_file}")
        except Exception as e:
            logger.error(f"설정 파일 로드 중 오류: {e}")
            raise
    
    def _set_config_values(self, config):
        """설정값 적용"""
        # 상수 정의
        DEFAULT_MAX_ATTACHMENT_SIZE = 8 * 1024 * 1024  # 8MB
        
        # 봇 설정
        bot_config = config.get('bot', {})
        self.BOT_INTENTS = bot_config.get('intents', {
            'message_content': True,
            'guilds': True,
            'reactions': True,
            'members': True
        })
        
        # 인증 설정 (환경 변수에서 토큰과 webhook URL 로드)
        self.DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', '')
        self.WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
        self.RAG_WEBHOOK_URL = os.getenv('RAG_WEBHOOK_URL', '')
        
        # 허용된 채널 ID (환경 변수에서 로드, 없으면 기본값)
        allowed_channels_str = os.getenv('ALLOWED_CHANNELS', '1401808594055335967')
        self.ALLOWED_CHANNELS = [int(channel_id.strip()) for channel_id in allowed_channels_str.split(',')]
        
        # 디버깅용 로그
        logger.info(f"환경 변수 로드 - DISCORD_TOKEN: {'설정됨' if self.DISCORD_TOKEN else '설정되지 않음'}")
        logger.info(f"환경 변수 로드 - ALLOWED_CHANNELS: {self.ALLOWED_CHANNELS}")
        logger.info(f"환경 변수 로드 - DISCORD_TOKEN 길이: {len(self.DISCORD_TOKEN) if self.DISCORD_TOKEN else 0}")
        logger.info(f"환경 변수 로드 - DISCORD_TOKEN 시작: {self.DISCORD_TOKEN[:10] if self.DISCORD_TOKEN else 'None'}")
        
        # 하위 호환성을 위한 별칭
        self.TOKEN = self.DISCORD_TOKEN
        
        # 인증 키워드
        verification_config = config.get('verification', {})
        self.VERIFICATION_KEYWORDS = verification_config.get('keywords', [
            "인증", "TODO", "계획", "인증사진", "투두"
        ])
        
        # 메시지 제한
        message_limits = config.get('message_limits', {})
        self.MAX_MESSAGE_LENGTH = message_limits.get('max_length', 1900)
        self.MAX_ATTACHMENT_SIZE = message_limits.get('max_attachment_size', DEFAULT_MAX_ATTACHMENT_SIZE)
        self.MESSAGE_HISTORY_LIMIT = message_limits.get('history_limit', 1000)
        self.MAX_MENTIONS_PER_CHUNK = message_limits.get('max_mentions_per_chunk', 20)
        
        # 재시도 설정
        retry_config = config.get('retry', {})
        self.MAX_RETRY_ATTEMPTS = retry_config.get('max_attempts', 3)
        self.WEBHOOK_TIMEOUT = retry_config.get('webhook_timeout', 10)
        
        # 시간 설정
        time_config = config.get('time', {})
        timezone_str = time_config.get('timezone', 'Asia/Seoul')
        self.TIMEZONE = pytz.timezone(timezone_str)
        
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
        self.WEEKDAY_NAMES = time_config.get('weekday_names', 
            ['월', '화', '수', '목', '금', '토', '일'])
        
        # 공휴일 설정
        holidays_config = config.get('holidays', {})
        self.HOLIDAYS_FILE = holidays_config.get('file', 'holidays.csv')
        self.SKIP_HOLIDAYS = holidays_config.get('skip', True)
        
        # 메시지 템플릿
        self.MESSAGES = config.get('messages', {
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
        })
        
        # 로깅 설정
        logging_config = config.get('logging', {})
        self.LOGGING_LEVEL = logging_config.get('level', 'INFO')
        self.LOGGING_FORMAT = logging_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.LOGGING_FILE = logging_config.get('file', None)
    
    def load_holidays(self):
        """공휴일 데이터베이스 로드 (CSV 백업 지원)"""
        try:
            # 먼저 데이터베이스에서 공휴일 수 확인
            holiday_count = self.holiday_manager.get_holiday_count()
            
            if holiday_count == 0:
                # 데이터베이스가 비어있으면 CSV에서 마이그레이션 시도
                logger.info("데이터베이스에 공휴일 데이터가 없습니다. CSV에서 마이그레이션을 시도합니다.")
                migration = DataMigration(self.db_manager)
                migration.migrate_holidays_from_csv(self.HOLIDAYS_FILE)
                holiday_count = self.holiday_manager.get_holiday_count()
            
            # 하위 호환성을 위해 HOLIDAYS 집합 생성
            holidays_list = self.holiday_manager.get_holidays()
            self.HOLIDAYS = {holiday['date'] for holiday in holidays_list}
            
            logger.info(f"데이터베이스에서 {holiday_count}개의 공휴일을 로드했습니다.")
            
        except Exception as e:
            logger.error(f"공휴일 로드 중 오류: {str(e)}")
            # 오류 발생 시 빈 집합으로 초기화
            self.HOLIDAYS = set()
    
    def is_holiday(self, date):
        """주어진 날짜가 공휴일인지 확인"""
        return self.holiday_manager.is_holiday(date)
    
    def validate_config(self):
        """필수 설정 검증"""
        if not self.DISCORD_TOKEN:
            raise ValueError("Discord Bot Token이 설정되지 않았습니다. 환경 변수 DISCORD_TOKEN을 확인하세요.")
        if not self.ALLOWED_CHANNELS:
            raise ValueError("인증을 허용할 채널이 설정되지 않았습니다. 환경 변수 ALLOWED_CHANNELS를 확인하세요.")
        
        logger.info("설정 검증 완료")
        return True