"""
봇 핵심 클래스 모듈
"""
import discord
from discord.ext import commands
import datetime as dt
from datetime import datetime, time, timedelta, timezone
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
        
        # 봇 설정
        intents = discord.Intents.all()
        intents.message_content = True
        intents.guilds = True
        intents.reactions = True
        intents.members = True 
        self.bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
        
        # 휴가 관리를 위한 딕셔너리 추가 - 위치 변경!
        self.vacation_users = {}
        
        # Bot 객체에 vacation_users 속성 추가 (중요!)
        self.bot.vacation_users = self.vacation_users
        
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
            now = datetime.now()
            now_utc = datetime.now(timezone.utc)
            now_kst = self.time_util.now()
            
            logger.info("=== Time Debug ===")
            logger.info(f"Server time: {now}")
            logger.info(f"UTC time: {now_utc}")
            logger.info(f"KST time: {now_kst}")
            logger.info("================")
            
            # 태스크 설정 및 시작
            self.task_manager.setup_tasks()
            self.task_manager.start_tasks()
            
            logger.info(f'Logged in as {self.bot.user}')
        
        @self.bot.event
        async def on_message(message):
            if message.author == self.bot.user:
                return
                
            try:
                # 인증 채널에서만 인증 및 휴가 메시지 처리 (중요!)
                if message.channel.id == self.config.VERIFICATION_CHANNEL_ID:
                    await self._process_message(message)
            except Exception as e:
                logger.error(f"메시지 처리 중 오류: {e}", exc_info=True)
            
            await self.bot.process_commands(message)
    
    async def _process_message(self, message):
        """메시지 처리 로직 (채널 ID 체크 없이)"""
        if self.message_util.is_verification_message(message.content):
            await self.verification_service.process_verification_message(message)
        elif self.message_util.is_vacation_message(message.content):
            await self.verification_service.process_vacation_request(message)

    def run(self):
        """봇 실행"""
        try:
            if not self.config.TOKEN:
                raise ValueError("Discord Bot Token is missing. Please check .env file.")
                
            logger.info("Starting bot...")
            logger.info(f"Channel ID configured: {self.config.VERIFICATION_CHANNEL_ID}")
            logger.info(f"Intents status:")
            logger.info(f"- members: {self.bot.intents.members}")
            logger.info(f"- message_content: {self.bot.intents.message_content}")
            logger.info(f"- guilds: {self.bot.intents.guilds}")
            
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

    def cleanup_old_vacation_data(self):
        """만료된 휴가 데이터 정리"""
        today = datetime.now().date()
        expired_entries = []
        
        # 만료된 휴가 항목 찾기
        for user_id, (start_date, end_date) in self.vacation_users.items():
            if end_date < today - timedelta(days=7):  # 일주일 이상 지난 데이터
                expired_entries.append(user_id)
        
        # 만료된 항목 삭제
        for user_id in expired_entries:
            del self.vacation_users[user_id]
        
        if expired_entries:
            logger.info(f"{len(expired_entries)}개의 만료된 휴가 데이터 정리 완료")
            self._save_vacation_data()  # 변경사항 저장 

    def check_permissions(self, channel):
        """필요한 권한이 있는지 확인"""
        if not channel or not isinstance(channel, discord.TextChannel):
            logger.error(f"올바른 채널이 아닙니다: {channel}")
            return False
        
        permissions = channel.permissions_for(channel.guild.me)
        required_permissions = [
            "read_message_history",
            "view_channel", 
            "send_messages",
            "add_reactions",
            "embed_links"
        ]
        
        missing = []
        for perm in required_permissions:
            if not getattr(permissions, perm, False):
                missing.append(perm)
        
        if missing:
            logger.error(f"필요한 권한이 없습니다: {', '.join(missing)}")
            return False
        
        return True 