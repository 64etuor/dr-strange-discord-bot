import logging
import datetime
import discord
from discord.ext import commands, tasks
from config import Config, Messages
from utils import MessageUtils, VerificationUtils
import os
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VerificationBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    async def setup_hook(self):
        """봇 초기 설정 및 태스크 시작"""
        self.check_yesterday_verification.start()
        logger.info("Bot setup completed")

    async def on_ready(self):
        """봇이 준비되었을 때 실행"""
        logger.info(f"Logged in as {self.user.name}")
        logger.info(f"Bot ID: {self.user.id}")

    @tasks.loop(time=datetime.time(
        hour=Config.Time.get_utc_hour(Config.Time.YESTERDAY_CHECK_HOUR),
        minute=Config.Time.YESTERDAY_CHECK_MINUTE
    ))
    async def check_yesterday_verification(self):
        """전날 인증 확인 및 미인증자 처리"""
        logger.info("Starting daily verification check")
        
        try:
            channel = self.get_channel(int(os.getenv('VERIFICATION_CHANNEL_ID')))
            if not channel:
                logger.error("Verification channel not found")
                return

            now = datetime.datetime.now(Config.Time.TIMEZONE)
            yesterday = now - datetime.timedelta(days=1)
            yesterday_weekday = yesterday.weekday()

            # 토요일(5)이나 일요일(6)의 인증은 체크하지 않음
            if yesterday_weekday in [5, 6]:
                logger.info(f"Weekend verification check skipped ({['월','화','수','목','금','토','일'][yesterday_weekday]}요일)")
                return

            # 시간 범위 설정
            yesterday_start = yesterday.replace(
                hour=Config.Time.DAILY_START_HOUR,
                minute=Config.Time.DAILY_START_MINUTE,
                second=0,
                microsecond=0
            )
            yesterday_end = yesterday.replace(
                hour=Config.Time.DAILY_END_HOUR,
                minute=Config.Time.DAILY_END_MINUTE,
                second=Config.Time.DAILY_END_SECOND,
                microsecond=999999
            )

            # 미인증 멤버 확인
            _, unverified_members = await VerificationUtils.get_unverified_members(
                channel, yesterday_start, yesterday_end
            )

            if unverified_members:
                mention_chunks = MessageUtils.chunk_mentions(unverified_members)
                
                for chunk in mention_chunks:
                    try:
                        message = (Messages.UNVERIFIED_FRIDAY if now.weekday() == 0 
                                 else Messages.UNVERIFIED_DAILY)
                        await channel.send(message.format(members=chunk))
                    except discord.HTTPException as e:
                        logger.error(f"Failed to send message: {e}")
            else:
                try:
                    await channel.send(Messages.ALL_VERIFIED_YESTERDAY)
                    logger.info("All members verified yesterday")
                except discord.HTTPException as e:
                    logger.error(f"Failed to send all verified message: {e}")

        except Exception as e:
            logger.error(f"Error in verification check: {e}", exc_info=True)

    @check_yesterday_verification.before_loop
    async def before_verification_check(self):
        """태스크 시작 전 봇이 준비될 때까지 대기"""
        await self.wait_until_ready()
        logger.info("Verification check task is ready")

    async def on_message(self, message: discord.Message):
        """메시지 수신 시 처리"""
        if message.author.bot:
            return

        # 인증 채널 메시지 처리
        if message.channel.id == int(os.getenv('VERIFICATION_CHANNEL_ID')):
            if not message.attachments:
                try:
                    await message.channel.send(Messages.ATTACH_IMAGE_REQUEST)
                except discord.HTTPException as e:
                    logger.error(f"Failed to send message: {e}")
                return

            if any(VerificationUtils.is_valid_image(attach) for attach in message.attachments):
                try:
                    await message.add_reaction("✅")
                except discord.HTTPException as e:
                    logger.error(f"Failed to add reaction: {e}")

        await self.process_commands(message)

# 봇 실행
def run_bot():
    """봇 실행 함수"""
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    
    bot = VerificationBot(
        command_prefix="!",
        intents=intents,
        help_command=None
    )
    
    try:
        load_dotenv()
        bot.run(os.getenv('BOT_TOKEN'))
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}", exc_info=True)

if __name__ == "__main__":
    run_bot()