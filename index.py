import discord
import aiohttp
from discord.ext import commands
import datetime
import pytz
import asyncio
import os
import logging
from dotenv import load_dotenv
from discord.ext import tasks
from typing import List, Set, Tuple, Optional
import csv
import pathlib

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('verification_bot')

# .env 파일에서 환경 변수 로드
load_dotenv()

# 설정 클래스
class Config:
    # 봇 설정
    TOKEN = os.getenv('DISCORD_TOKEN')
    VERIFICATION_CHANNEL_ID = int(os.getenv('VERIFICATION_CHANNEL_ID', '0'))
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://koreahub.us/webhook/discord')
    
    # 메시지 제한
    MAX_MESSAGE_LENGTH = 1900
    MAX_ATTACHMENT_SIZE = 8 * 1024 * 1024
    MESSAGE_HISTORY_LIMIT = 1000
    
    # 재시도 설정
    MAX_RETRY_ATTEMPTS = 3
    WEBHOOK_TIMEOUT = 10
    
    # 인증 키워드
    VERIFICATION_KEYWORDS = ["인증사진", "인증 사진", "인증"]
    
    # 시간 설정
    class Time:
        TIMEZONE = pytz.timezone('Asia/Seoul')
        
        # 체크 시간 (KST)
        DAILY_CHECK_HOUR = 22
        DAILY_CHECK_MINUTE = 0
        YESTERDAY_CHECK_HOUR = 9
        YESTERDAY_CHECK_MINUTE = 0
        
        # 인증 시간 범위 - 수정된 부분
        DAILY_START_HOUR = 12  
        DAILY_START_MINUTE = 0
        DAILY_END_HOUR = 3     
        DAILY_END_MINUTE = 0
        DAILY_END_SECOND = 0
        
        # 요일 이름
        WEEKDAY_NAMES = ['월', '화', '수', '목', '금', '토', '일']
        
        # UTC 변환
        @staticmethod
        def get_utc_hour(kst_hour):
            return (kst_hour - 9) % 24
        
        # UTC 시간
        UTC_DAILY_CHECK_HOUR = (DAILY_CHECK_HOUR - 9) % 24
        UTC_YESTERDAY_CHECK_HOUR = (YESTERDAY_CHECK_HOUR - 9) % 24

    # 공휴일 설정
    HOLIDAYS_FILE = 'holidays.csv'
    SKIP_HOLIDAYS = True  # 공휴일 체크 스킵 여부
    
    # 공휴일 목록을 저장할 변수
    HOLIDAYS = set()
    
    @classmethod
    def load_holidays(cls):
        """공휴일 CSV 파일 로드"""
        try:
            holidays_path = pathlib.Path(cls.HOLIDAYS_FILE)
            if not holidays_path.exists():
                logger.warning(f"Holidays file not found: {cls.HOLIDAYS_FILE}")
                return
                
            with open(cls.HOLIDAYS_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date_str = row.get('date', '').strip()
                    if date_str:
                        # YYYY-MM-DD 형식의 날짜를 세트에 추가
                        cls.HOLIDAYS.add(date_str)
                        
            logger.info(f"Loaded {len(cls.HOLIDAYS)} holidays from {cls.HOLIDAYS_FILE}")
        except Exception as e:
            logger.error(f"Error loading holidays: {str(e)}")
    
    @classmethod
    def is_holiday(cls, date):
        """주어진 날짜가 공휴일인지 확인"""
        date_str = date.strftime('%Y-%m-%d')
        return date_str in cls.HOLIDAYS

# 메시지 템플릿
class Messages:
    VERIFICATION_SUCCESS = "{name}, Your time has been recorded. The bill comes due. Always!"
    VERIFICATION_ERROR = "Verification Error occurred. Please try again."
    ATTACH_IMAGE_REQUEST = "Please attach an image."
    
    UNVERIFIED_DAILY = ("⚠️ 아직 오늘의 인증을 하지 않은 멤버들이에요:\n{members}\n"
                      "자정까지 2시간 남았어요! 오늘의 기록 인증을 올리는 것 잊지 마세요! 💪")
    
    UNVERIFIED_YESTERDAY = "⚠️ 어제 인증을 하지 않은 멤버(들)입니다:\n{members}\n벌칙을 수행해 주세요!"
    UNVERIFIED_FRIDAY = "⚠️ 지난 주 금요일 인증을 하지 않은 멤버(들)입니다:\n{members}\n벌칙을 수행해 주세요!"
    
    ALL_VERIFIED = ("🎉 모든 멤버가 인증을 완료했네요!\n"
                   "💪 여러분의 꾸준한 노력이 멋져요. 내일도 힘내세요! 💫")
    
    PERMISSION_ERROR = "❌ 관리자만 사용할 수 있는 명령어입니다."
    BOT_PERMISSION_ERROR = "Bot doesn't have permission to add reactions."

# 유틸리티 클래스
class Utils:
    @staticmethod
    def is_weekend(weekday: int) -> bool:
        """주말인지 확인 (토: 5, 일: 6)"""
        return weekday in [5, 6]
    
    @staticmethod
    def is_verification_message(content: str) -> bool:
        """인증 메시지인지 확인"""
        return any(keyword in content for keyword in Config.VERIFICATION_KEYWORDS)
    
    @staticmethod
    def is_valid_image(attachment: discord.Attachment) -> bool:
        """유효한 이미지인지 확인"""
        return (attachment.content_type and 
                attachment.content_type.startswith('image/') and 
                attachment.size <= Config.MAX_ATTACHMENT_SIZE)
    
    @staticmethod
    def chunk_mentions(members: List[discord.Member]) -> List[str]:
        """멤버 멘션을 Discord 메시지 길이 제한에 맞게 청크로 분할"""
        chunks = []
        current_chunk = []
        current_length = 0
        
        for member in members:
            mention = member.mention
            if current_length + len(mention) + 1 > Config.MAX_MESSAGE_LENGTH:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0
            current_chunk.append(mention)
            current_length += len(mention) + 1
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks
    
    @staticmethod
    async def get_verification_data(
        channel: discord.TextChannel,
        start_time: datetime.datetime,
        end_time: datetime.datetime
    ) -> Tuple[Set[int], List[discord.Member]]:
        """인증 데이터 가져오기"""
        verified_users: Set[int] = set()
        unverified_members: List[discord.Member] = []
        
        try:
            # 메시지 히스토리에서 인증한 사용자 확인
            async for message in channel.history(
                after=start_time,
                before=end_time,
                limit=Config.MESSAGE_HISTORY_LIMIT
            ):
                if (Utils.is_verification_message(message.content) and 
                    any(Utils.is_valid_image(attachment) for attachment in message.attachments)):
                    verified_users.add(message.author.id)
            
            # 인증하지 않은 멤버 확인
            async for member in channel.guild.fetch_members():
                if not member.bot and member.id not in verified_users:
                    unverified_members.append(member)
                    
        except discord.Forbidden:
            logger.error("Missing required permissions")
        except discord.HTTPException as e:
            logger.error(f"Error while fetching messages/members: {e}")
            
        return verified_users, unverified_members
    
    @staticmethod
    async def send_webhook(webhook_url: str, webhook_data: dict) -> bool:
        """웹훅 전송"""
        global session
        
        # 세션이 없으면 생성
        if session is None:
            session = aiohttp.ClientSession()

        try:
            # 타임아웃 설정 추가
            async with session.post(
                webhook_url, 
                json=webhook_data,
                timeout=Config.WEBHOOK_TIMEOUT
            ) as response:
                if response.status in [401, 403, 404]:
                    logger.error(f"Webhook error: Status {response.status}")
                    return False

                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    logger.warning(f"Rate limited, retrying after {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    return await Utils.send_webhook(webhook_url, webhook_data)

                # 응답 내용 로깅 추가
                response_text = await response.text()
                if response.status != 200:
                    logger.error(f"Webhook failed: Status {response.status}, Response: {response_text}")
                    return False
                
                logger.info(f"Webhook sent successfully: Status {response.status}")
                return True

        except aiohttp.ClientError as e:
            logger.error(f"Webhook request failed: {e}")
            return False
        except asyncio.TimeoutError:
            logger.error(f"Webhook request timed out after {Config.WEBHOOK_TIMEOUT} seconds")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during webhook request: {e}", exc_info=True)
            return False

    @staticmethod
    def should_skip_check(date):
        """해당 날짜의 체크를 건너뛰어야 하는지 확인 (주말 또는 공휴일)"""
        # 주말인지 확인
        if Utils.is_weekend(date.weekday()):
            return True
            
        # 공휴일인지 확인
        if Config.SKIP_HOLIDAYS and Config.is_holiday(date):
            return True
            
        return False

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.reactions = True
intents.members = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# 전역 변수
session = None

@bot.event
async def on_ready():
    global session
    if session is None:
        session = aiohttp.ClientSession()
    
    # 시간 디버깅
    now = datetime.datetime.now()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_kst = datetime.datetime.now(Config.Time.TIMEZONE)
    
    logger.info("=== Time Debug ===")
    logger.info(f"Server time: {now}")
    logger.info(f"UTC time: {now_utc}")
    logger.info(f"KST time: {now_kst}")
    logger.info("================")
   
    check_daily_verification.start()
    check_yesterday_verification.start()
    logger.info(f'Logged in as {bot.user}')


@bot.command()
async def hello(ctx):
    await ctx.send('Hello!')


@bot.command()
async def check_now(ctx):
    """테스트용: 즉시 인증 체크를 실행합니다"""
    await ctx.send("Verification check started...")
    await check_daily_verification()
    await ctx.send("Verification check completed.")


@bot.command()
async def time_check(ctx):
    """현재 봇이 인식하는 시간을 확인합니다"""
    now = datetime.datetime.now()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_kst = datetime.datetime.now(Config.Time.TIMEZONE)
    
    await ctx.send(
        "🕒 Current time information:\n"
        f"Server time: {now}\n"
        f"UTC time: {now_utc}\n"
        f"KST time: {now_kst}"
    )


@bot.command()
async def next_check(ctx):
    """다음 인증 체크 시간을 확인합니다"""
    daily_next = check_daily_verification.next_iteration
    yesterday_next = check_yesterday_verification.next_iteration
    
    await ctx.send(
        "⏰ Next verification check time:\n"
        f"Daily verification check: {daily_next.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        f"Previous day verification check: {yesterday_next.strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )


@bot.command()
async def test_check(ctx):
    """인증 체크를 즉시 테스트합니다 (관리자 전용)"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send(Messages.PERMISSION_ERROR)
        return
        
    await ctx.send("🔍 Verification test started...")
    await check_daily_verification()
    await check_yesterday_verification()
    await ctx.send("✅ Verification test completed.")


@bot.command()
async def check_settings(ctx):
    """현재 설정된 체크 시간을 확인합니다"""
    await ctx.send(
        "⚙️ Current Check Time Settings:\n"
        f"Daily Check (KST): {Config.Time.DAILY_CHECK_HOUR:02d}:{Config.Time.DAILY_CHECK_MINUTE:02d}\n"
        f"Yesterday Check (KST): {Config.Time.YESTERDAY_CHECK_HOUR:02d}:{Config.Time.YESTERDAY_CHECK_MINUTE:02d}\n"
        f"Daily Check (UTC): {Config.Time.UTC_DAILY_CHECK_HOUR:02d}:{Config.Time.DAILY_CHECK_MINUTE:02d}\n"
        f"Yesterday Check (UTC): {Config.Time.UTC_YESTERDAY_CHECK_HOUR:02d}:{Config.Time.YESTERDAY_CHECK_MINUTE:02d}\n"
        "\n📅 Verification Time Range:\n"
        f"Start: {Config.Time.DAILY_START_HOUR:02d}:{Config.Time.DAILY_START_MINUTE:02d}\n"
        f"End: {Config.Time.DAILY_END_HOUR:02d}:{Config.Time.DAILY_END_MINUTE:02d}:{Config.Time.DAILY_END_SECOND:02d}"
    )


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    try:
        if Utils.is_verification_message(message.content):
            # 반응 추가
            if message.guild and message.channel.permissions_for(message.guild.me).add_reactions:
                await message.add_reaction('✅')

            # 이미지 URL 추출
            image_urls = []
            for attachment in message.attachments:
                if Utils.is_valid_image(attachment):
                    image_urls.append(attachment.url)
            
            if not image_urls:
                await message.channel.send(Messages.ATTACH_IMAGE_REQUEST)
                return

            # 웹훅 데이터 준비
            webhook_data = {
                "author": message.author.name,
                "content": message.content,
                "image_urls": image_urls,
                "sent_at": datetime.datetime.now(Config.Time.TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
            }

            # 웹훅 전송
            if await Utils.send_webhook(Config.WEBHOOK_URL, webhook_data):
                await message.channel.send(
                    Messages.VERIFICATION_SUCCESS.format(name=message.author.name)
                )
            else:
                await message.channel.send(Messages.VERIFICATION_ERROR)

    except discord.Forbidden:
        await message.channel.send(Messages.BOT_PERMISSION_ERROR)
    except Exception as e:
        logger.error(f"An error occurred in on_message: {e}", exc_info=True)
        await message.channel.send("An error occurred in on_message.")

    await bot.process_commands(message)


async def cleanup():
    """리소스 정리"""
    if session:
        await session.close()


@bot.event
async def on_shutdown():
    await cleanup()


async def send_unverified_messages(
    channel: discord.TextChannel,
    unverified_members: List[discord.Member],
    message_template: str
) -> None:
    """미인증 멤버 메시지 전송"""
    if not unverified_members:
        try:
            await channel.send(Messages.ALL_VERIFIED)
            logger.info("모든 멤버 인증 완료 메시지 전송")
        except discord.HTTPException as e:
            logger.error(f"메시지 전송 중 오류: {e}")
        return
        
    # 멘션 청크 생성
    mention_chunks = Utils.chunk_mentions(unverified_members)
    
    # 각 청크별로 메시지 전송
    for chunk in mention_chunks:
        try:
            await channel.send(message_template.format(members=chunk))
        except discord.HTTPException as e:
            logger.error(f"메시지 전송 중 오류: {e}")


@tasks.loop(time=datetime.time(
    hour=Config.Time.UTC_DAILY_CHECK_HOUR,
    minute=Config.Time.DAILY_CHECK_MINUTE,
    tzinfo=datetime.timezone.utc
))
async def check_daily_verification():
    """일일 인증 체크"""
    try:
        current_time = datetime.datetime.now(Config.Time.TIMEZONE)
        current_date = current_time.date()
        
        # 주말이나 공휴일인 경우 체크 건너뛰기
        if Utils.should_skip_check(current_time):
            reason = "weekend" if Utils.is_weekend(current_time.weekday()) else "holiday"
            logger.info(f"Skipping daily check - it's a {reason} ({current_date})")
            return
            
        logger.info(f"Starting daily verification check (KST): {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 채널 확인
        channel = bot.get_channel(Config.VERIFICATION_CHANNEL_ID)
        if not channel or not isinstance(channel, discord.TextChannel):
            logger.error(f"Channel check failed: {Config.VERIFICATION_CHANNEL_ID}")
            return

        logger.info(f"Channel check successful: {channel.name}")

        # 권한 확인
        permissions = channel.permissions_for(channel.guild.me)
        if not all([permissions.read_message_history, permissions.view_channel, permissions.send_messages]):
            logger.error("Missing required permissions")
            return

        # 날짜 범위 설정
        now = datetime.datetime.now(Config.Time.TIMEZONE)
        if now.hour < Config.Time.DAILY_START_HOUR:
            today_start = (now - datetime.timedelta(days=1)).replace(
                hour=Config.Time.DAILY_START_HOUR,
                minute=Config.Time.DAILY_START_MINUTE,
                second=0,
                microsecond=0
            )
        else:
            today_start = now.replace(
                hour=Config.Time.DAILY_START_HOUR,
                minute=Config.Time.DAILY_START_MINUTE,
                second=0,
                microsecond=0
            )
        today_end = now

        # 인증 데이터 가져오기
        verified_users, unverified_members = await Utils.get_verification_data(
            channel, today_start, today_end
        )

        # 미인증 멤버 메시지 전송
        await send_unverified_messages(
            channel, unverified_members, Messages.UNVERIFIED_DAILY
        )

        # 처리 결과 로깅
        logger.info(f"Number of unverified members: {len(unverified_members)}")
        logger.info("Daily verification check completed")

    except Exception as e:
        logger.error(f"Error during verification check: {str(e)}", exc_info=True)
    finally:
        if 'verified_users' in locals():
            verified_users.clear()


@check_daily_verification.before_loop
async def before_check():
    await bot.wait_until_ready()
    logger.info("Daily verification check task ready")


@tasks.loop(time=datetime.time(
    hour=Config.Time.UTC_YESTERDAY_CHECK_HOUR,
    minute=Config.Time.YESTERDAY_CHECK_MINUTE,
    tzinfo=datetime.timezone.utc
))
async def check_yesterday_verification():
    """전일 인증 체크"""
    try:
        current_time = datetime.datetime.now(Config.Time.TIMEZONE)
        current_weekday = current_time.weekday()
        
        # 오늘이 주말이나 공휴일인 경우 체크 건너뛰기
        if Utils.should_skip_check(current_time):
            reason = "weekend" if Utils.is_weekend(current_time.weekday()) else "holiday"
            logger.info(f"Skipping yesterday check - today is a {reason} ({current_time.date()})")
            return
        
        # 월요일이면 금요일 체크
        if current_weekday == 0:
            check_date = current_time - datetime.timedelta(days=3)
            logger.info(f"Monday: Checking Friday's verification")
        else:
            check_date = current_time - datetime.timedelta(days=1)
            
        # 체크하는 날짜가 주말이나 공휴일인 경우 체크 건너뛰기
        if Utils.should_skip_check(check_date):
            reason = "weekend" if Utils.is_weekend(check_date.weekday()) else "holiday"
            logger.info(f"Skipping yesterday check - the target date is a {reason} ({check_date.date()})")
            return
            
        logger.info(f"Starting verification check for {check_date.strftime('%Y-%m-%d')} (KST)")

        # 채널 확인
        channel = bot.get_channel(Config.VERIFICATION_CHANNEL_ID)
        if not channel or not isinstance(channel, discord.TextChannel):
            logger.error(f"Channel check failed: {Config.VERIFICATION_CHANNEL_ID}")
            return

        # 날짜 범위 설정
        check_start = check_date.replace(
            hour=Config.Time.DAILY_START_HOUR,
            minute=Config.Time.DAILY_START_MINUTE,
            second=0,
            microsecond=0
        )
        check_end = (check_date + datetime.timedelta(days=1)).replace(
            hour=Config.Time.DAILY_END_HOUR,
            minute=Config.Time.DAILY_END_MINUTE,
            second=Config.Time.DAILY_END_SECOND,
            microsecond=999999
        )

        # 인증 데이터 가져오기
        verified_users, unverified_members = await Utils.get_verification_data(
            channel, check_start, check_end
        )

        # 미인증 멤버 메시지 전송
        message_template = (
            Messages.UNVERIFIED_FRIDAY if current_weekday == 0
            else Messages.UNVERIFIED_YESTERDAY
        )
        await send_unverified_messages(
            channel, unverified_members, message_template
        )

        # 처리 결과 로깅
        logger.info(f"Number of unverified members from previous day: {len(unverified_members)}")
        logger.info("Previous day verification check completed")

    except Exception as e:
        logger.error(f"Error during previous day verification check: {str(e)}", exc_info=True)
    finally:
        if 'verified_users' in locals():
            verified_users.clear()


@check_yesterday_verification.before_loop
async def before_yesterday_check():
    await bot.wait_until_ready()
    logger.info("Previous day verification check task ready")


def main():
    try:
        if not Config.TOKEN:
            raise ValueError("Discord Bot Token is missing. Please check .env file.")
        
        # 공휴일 목록 로드
        Config.load_holidays()
            
        logger.info("Starting bot...")
        logger.info(f"Channel ID configured: {Config.VERIFICATION_CHANNEL_ID}")
        logger.info(f"Intents status:")
        logger.info(f"- members: {intents.members}")
        logger.info(f"- message_content: {intents.message_content}")
        logger.info(f"- guilds: {intents.guilds}")
        
        bot.run(Config.TOKEN)
    except Exception as e:
        logger.error(f"Bot error: {str(e)}", exc_info=True)
    finally:
        if session:
            asyncio.get_event_loop().run_until_complete(cleanup())


if __name__ == "__main__":
    main()
