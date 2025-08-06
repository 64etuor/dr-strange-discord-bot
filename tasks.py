"""
봇 태스크 스케줄링 모듈
"""
import datetime
from discord.ext import tasks
import threading
from logging_utils import get_logger

logger = get_logger()

class TaskManager:
    """태스크 관리 클래스 (스레드 안전 싱글톤)"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TaskManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, bot=None, config=None, verification_service=None):
        # 스레드 안전한 초기화 체크
        if not hasattr(self, '_initialized'):
            with self._lock:
                if not hasattr(self, '_initialized'):
                    self._initialize(bot, config, verification_service)
    
    def _initialize(self, bot, config, verification_service):
        """내부 초기화 메서드"""
        self.bot = bot
        self.config = config
        self.verification_service = verification_service
        self.daily_check_task = None
        self.yesterday_check_task = None
        self._tasks_started = False
        self._tasks_setup = False
        self._initialized = True
        logger.info("TaskManager 초기화 완료")
    
    def is_initialized(self):
        """초기화 상태 확인"""
        return hasattr(self, '_initialized') and self._initialized
    
    def setup_tasks(self):
        """태스크 설정"""
        if not self.is_initialized():
            logger.error("TaskManager가 초기화되지 않았습니다.")
            return
            
        if self._tasks_setup:
            logger.warning("Tasks are already set up")
            return
            
        try:
            @tasks.loop(time=datetime.time(
                hour=self.config.UTC_DAILY_CHECK_HOUR,
                minute=self.config.DAILY_CHECK_MINUTE,
                tzinfo=datetime.timezone.utc
            ))
            async def check_daily_verification():
                await self.verification_service.check_daily_verification()
            
            @check_daily_verification.before_loop
            async def before_daily_check():
                await self.bot.wait_until_ready()
                logger.info("Daily verification check task ready")
            
            @tasks.loop(time=datetime.time(
                hour=self.config.UTC_YESTERDAY_CHECK_HOUR,
                minute=self.config.YESTERDAY_CHECK_MINUTE,
                tzinfo=datetime.timezone.utc
            ))
            async def check_yesterday_verification():
                await self.verification_service.check_yesterday_verification()
            
            @check_yesterday_verification.before_loop
            async def before_yesterday_check():
                await self.bot.wait_until_ready()
                logger.info("Previous day verification check task ready")
            
            # 태스크 참조 저장
            self.daily_check_task = check_daily_verification
            self.yesterday_check_task = check_yesterday_verification
            self._tasks_setup = True
            
            logger.info("Task setup completed")
            
        except Exception as e:
            logger.error(f"Task setup failed: {e}", exc_info=True)
            raise
    
    def start_tasks(self):
        """태스크 시작"""
        if not self.is_initialized():
            logger.error("TaskManager가 초기화되지 않았습니다.")
            return
            
        if not self._tasks_setup:
            logger.error("Tasks가 설정되지 않았습니다. setup_tasks()를 먼저 호출하세요.")
            return
            
        if self._tasks_started:
            logger.warning("Tasks are already running")
            return
            
        try:
            if self.daily_check_task and self.yesterday_check_task:
                self.daily_check_task.start()
                self.yesterday_check_task.start()
                self._tasks_started = True
                logger.info("All tasks started successfully")
            else:
                logger.error("Tasks are not properly configured")
                
        except Exception as e:
            logger.error(f"Task start failed: {e}", exc_info=True)
            raise
    
    def stop_tasks(self):
        """태스크 중지"""
        if not self._tasks_started:
            logger.warning("Tasks are not running")
            return
            
        try:
            if self.daily_check_task:
                self.daily_check_task.cancel()
            if self.yesterday_check_task:
                self.yesterday_check_task.cancel()
            
            self._tasks_started = False
            logger.info("All tasks stopped")
            
        except Exception as e:
            logger.error(f"Task stop failed: {e}", exc_info=True)
    
    def get_task_status(self):
        """태스크 상태 반환"""
        return {
            'initialized': self.is_initialized(),
            'tasks_setup': self._tasks_setup,
            'tasks_started': self._tasks_started,
            'daily_task_running': self.daily_check_task.is_running() if self.daily_check_task else False,
            'yesterday_task_running': self.yesterday_check_task.is_running() if self.yesterday_check_task else False
        } 