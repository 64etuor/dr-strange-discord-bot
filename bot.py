"""
봇 핵심 클래스 모듈
"""
import discord
from discord.ext import commands
import datetime
import asyncio

from message_utils import MessageUtility
from time_utils import TimeUtility
from webhook_service import WebhookService
from verification_service import VerificationService
from vacation_service import VacationService
from tasks import TaskManager
from commands import CommandSetup
from logging_utils import get_logger

logger = get_logger()

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
            
        # 슬래시 명령어만 사용하므로 빈 문자열로 설정
        self.bot = commands.Bot(command_prefix="", intents=intents)
        
        # 서비스 초기화 (데이터베이스 매니저 공유)
        self.webhook_service = WebhookService(self.config)
        self.vacation_service = VacationService(self.config, self.time_util, self.config.vacation_manager)
        self.verification_service = VerificationService(
            self.config, self.bot, self.message_util, self.time_util, self.webhook_service,
            self.vacation_service, self.config.verification_manager
        )
        
        # 태스크 관리자 초기화
        self.task_manager = TaskManager(self.bot, self.config, self.verification_service)
        
        # 명령어 핸들러 초기화
        self.command_handler = CommandSetup(
            self.bot, self.config, self.verification_service, self.task_manager, 
            self.time_util, self.vacation_service
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
                
            # 허용된 채널에서만 인증 처리
            if message.channel.id in self.config.ALLOWED_CHANNELS:
                try:
                    if self.message_util.is_verification_message(message.content):
                        await self.verification_service.process_verification_message(message)
                except Exception as e:
                    logger.error(f"메시지 처리 중 오류: {e}", exc_info=True)
            
            # 슬래시 명령어만 사용하므로 process_commands 호출하지 않음
    
    async def _sync_commands(self):
        """슬래시 명령어 동기화"""
        try:
            # 먼저 Cog를 추가
            await self.command_handler.add_cogs_if_needed()
            
            logger.info("슬래시 명령어 동기화 시작...")
            synced = await self.bot.tree.sync()
            logger.info(f"{len(synced)} 개의 슬래시 명령어 동기화 완료")
        except Exception as e:
            logger.error(f"슬래시 명령어 동기화 중 오류 발생: {e}")
    
    def run(self):
        """봇 실행"""
        try:
            if not self.config.DISCORD_TOKEN:
                raise ValueError("Discord Bot Token is missing. Please check environment variable DISCORD_TOKEN.")
                
            logger.info("Starting bot...")
            logger.info(f"Allowed channels: {self.config.ALLOWED_CHANNELS}")
            logger.info(f"Intents status:")
            logger.info(f"- members: {self.bot.intents.members}")
            logger.info(f"- message_content: {self.bot.intents.message_content}")
            logger.info(f"- guilds: {self.bot.intents.guilds}")
            logger.info(f"- reactions: {self.bot.intents.reactions}")
            
            self.bot.run(self.config.DISCORD_TOKEN)
        except Exception as e:
            logger.error(f"Bot error: {str(e)}", exc_info=True)
        finally:
            # 봇 종료 시 정리 작업 수행
            try:
                # 안전하게 웹훅 서비스 정리
                if hasattr(self, 'webhook_service'):
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self.webhook_service.cleanup())
                        loop.close()
                    except Exception as e:
                        logger.error(f"웹훅 서비스 정리 중 오류: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"종료 처리 중 오류: {e}", exc_info=True) 