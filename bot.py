"""
봇 핵심 클래스 모듈
"""
import discord
from discord.ext import commands
import datetime
import asyncio
import logging

from message_utils import MessageUtility
from time_utils import TimeUtility
from webhook_service import WebhookService
from verification_service import VerificationService
from tasks import TaskManager
from commands import CommandHandler

logger = logging.getLogger('verification_bot')

class VerificationBot:
    """인증 봇 클래스"""
    
    def __init__(self, config):
        self.config = config
        
        # 유틸리티 초기화
        self.time_util = TimeUtility(self.config)
        self.message_util = MessageUtility(self.config)
        
        # 봇 설정 - YAML 설정에서 로드
        intents = discord.Intents.default()
        
        # 인텐트 설정 적용
        if self.config.BOT_INTENTS.get('message_content', True):
            intents.message_content = True
        if self.config.BOT_INTENTS.get('guilds', True):
            intents.guilds = True
        if self.config.BOT_INTENTS.get('reactions', True):
            intents.reactions = True
        if self.config.BOT_INTENTS.get('members', True):
            intents.members = True
            
        # 설정에서 프리픽스 로드
        self.bot = commands.Bot(command_prefix=self.config.BOT_PREFIX, intents=intents)
        
        # 서비스 초기화
        self.webhook_service = WebhookService(self.config)
        self.verification_service = VerificationService(
            self.config, self.bot, self.message_util, self.time_util, self.webhook_service
        )
        
        # 태스크 관리자 초기화
        self.task_manager = TaskManager(self.bot, self.config, self.verification_service)
        
        # 명령어 핸들러 초기화
        self.command_handler = CommandHandler(
            self.bot, self.config, self.verification_service, self.task_manager, self.time_util
        )
        
        # 이벤트 핸들러 등록
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """이벤트 핸들러 등록"""
        
        @self.bot.event
        async def on_ready():
            await self.webhook_service.initialize()
            
            # 시간 디버깅
            now = datetime.datetime.now()
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            now_kst = self.time_util.now()
            
            logger.info("=== Time Debug ===")
            logger.info(f"Server time: {now}")
            logger.info(f"UTC time: {now_utc}")
            logger.info(f"KST time: {now_kst}")
            logger.info("================")
            
            # 태스크 설정 및 시작
            self.task_manager.setup_tasks()
            self.task_manager.start_tasks()
            
            # 슬래시 명령어 동기화
            await self._sync_commands()
            
            logger.info(f'Logged in as {self.bot.user}')
        
        @self.bot.event
        async def on_message(message):
            if message.author == self.bot.user:
                return
                
            try:
                if self.message_util.is_verification_message(message.content):
                    await self.verification_service.process_verification_message(message)
            except Exception as e:
                logger.error(f"메시지 처리 중 오류: {e}", exc_info=True)
            
            await self.bot.process_commands(message)
    
    async def _sync_commands(self):
        """슬래시 명령어 동기화"""
        try:
            logger.info("슬래시 명령어 동기화 시작...")
            synced = await self.bot.tree.sync()
            logger.info(f"{len(synced)} 개의 슬래시 명령어 동기화 완료")
        except Exception as e:
            logger.error(f"슬래시 명령어 동기화 중 오류 발생: {e}")
    
    def run(self):
        """봇 실행"""
        try:
            if not self.config.TOKEN:
                raise ValueError("Discord Bot Token is missing. Please check .env file.")
                
            logger.info("Starting bot...")
            logger.info(f"Command prefix: {self.config.BOT_PREFIX}")
            logger.info(f"Channel ID configured: {self.config.VERIFICATION_CHANNEL_ID}")
            logger.info(f"Intents status:")
            logger.info(f"- members: {self.bot.intents.members}")
            logger.info(f"- message_content: {self.bot.intents.message_content}")
            logger.info(f"- guilds: {self.bot.intents.guilds}")
            logger.info(f"- reactions: {self.bot.intents.reactions}")
            
            self.bot.run(self.config.TOKEN)
        except Exception as e:
            logger.error(f"Bot error: {str(e)}", exc_info=True)
        finally:
            # 비동기 정리 함수를 동기적으로 호출
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.webhook_service.cleanup())
            else:
                loop.run_until_complete(self.webhook_service.cleanup()) 