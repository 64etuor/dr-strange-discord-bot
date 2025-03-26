"""
봇 태스크 스케줄링 모듈
"""
import datetime
from discord.ext import tasks
import logging

logger = logging.getLogger('verification_bot')

class TaskManager:
    """태스크 관리 클래스 (싱글톤)"""
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, bot=None, config=None, verification_service=None):
        if not hasattr(self, 'initialized'):
            self.bot = bot
            self.config = config
            self.verification_service = verification_service
            self.daily_check_task = None
            self.yesterday_check_task = None
            self._tasks_started = False
            self.initialized = True
    
    def setup_tasks(self):
        """태스크 설정"""
        if self._tasks_started:
            logger.warning("Tasks are already set up and running")
            return
            
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
    
    def start_tasks(self):
        """태스크 시작"""
        if self._tasks_started:
            logger.warning("Tasks are already running")
            return
            
        if self.daily_check_task and self.yesterday_check_task:
            self.daily_check_task.start()
            self.yesterday_check_task.start()
            self._tasks_started = True
            logger.info("All tasks started") 