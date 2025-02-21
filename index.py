import discord
import aiohttp
from discord.ext import commands
import datetime
import pytz
import asyncio
import os
from dotenv import load_dotenv
from discord.ext import tasks

# .env 파일에서 환경 변수 로드
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.reactions = True
intents.members = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# 전역 변수로 session 선언
session = None
VERIFICATION_CHANNEL_ID = None 

# 상수 정의
MAX_RETRY_ATTEMPTS = 3
WEBHOOK_TIMEOUT = 10
MESSAGE_HISTORY_LIMIT = 1000  # 하루 메시지 제한

# 시간 설정 (한국 시간 기준)
DAILY_CHECK_HOUR = 22  
DAILY_CHECK_MINUTE = 0
YESTERDAY_CHECK_HOUR = 9
YESTERDAY_CHECK_MINUTE = 0

# 인증 시간 범위 설정
DAILY_START_HOUR = 0   
DAILY_START_MINUTE = 0
DAILY_END_HOUR = 23    
DAILY_END_MINUTE = 59
DAILY_END_SECOND = 59

# UTC 시간으로 변환 (KST = UTC + 9)
UTC_DAILY_CHECK_HOUR = (DAILY_CHECK_HOUR - 9) % 24
UTC_YESTERDAY_CHECK_HOUR = (YESTERDAY_CHECK_HOUR - 9) % 24

@bot.event
async def on_ready():
    global session, VERIFICATION_CHANNEL_ID
    if session is None:
        session = aiohttp.ClientSession()
    VERIFICATION_CHANNEL_ID = int(os.getenv('VERIFICATION_CHANNEL_ID', '0'))
    
    # 시간 디버깅 추가
    now = datetime.datetime.now()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_kst = datetime.datetime.now(pytz.timezone('Asia/Seoul'))
    
    print("=== Time Debug ===")
    print(f"Server time: {now}")
    print(f"UTC time: {now_utc}")
    print(f"KST time: {now_kst}")
    print("================")
   
    check_daily_verification.start()
    check_yesterday_verification.start()
    print(f'Logged in as {bot.user}')


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
    now_kst = datetime.datetime.now(pytz.timezone('Asia/Seoul'))
    
    await ctx.send(
        "🕒 Current time information:\n"
        f"Server(Southeast Asia) time: {now}\n"
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
        await ctx.send("❌ 관리자만 사용할 수 있는 명령어입니다.")
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
        f"Daily Check (KST): {DAILY_CHECK_HOUR:02d}:{DAILY_CHECK_MINUTE:02d}\n"
        f"Yesterday Check (KST): {YESTERDAY_CHECK_HOUR:02d}:{YESTERDAY_CHECK_MINUTE:02d}\n"
        f"Daily Check (UTC): {UTC_DAILY_CHECK_HOUR:02d}:{DAILY_CHECK_MINUTE:02d}\n"
        f"Yesterday Check (UTC): {UTC_YESTERDAY_CHECK_HOUR:02d}:{YESTERDAY_CHECK_MINUTE:02d}\n"
        "\n📅 Verification Time Range:\n"
        f"Start: {DAILY_START_HOUR:02d}:{DAILY_START_MINUTE:02d}\n"
        f"End: {DAILY_END_HOUR:02d}:{DAILY_END_MINUTE:02d}:{DAILY_END_SECOND:02d}"
    )


async def send_webhook(webhook_url, webhook_data):
    """웹훅을 보낼 때 Rate Limit과 유효성 검사 적용"""
    if not session:
        return False

    try:
        async with session.post(webhook_url, json=webhook_data) as response:
            if response.status in [401, 403, 404]:
                print(f"Webhook error: Status {response.status}")
                return False

            if response.status == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                await asyncio.sleep(retry_after)
                return await send_webhook(webhook_url, webhook_data)

            return response.status == 200

    except aiohttp.ClientError as e:
        print(f"Webhook request failed: {e}")
        return False


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    try:
        if any(keyword in message.content for keyword in ["인증사진", "인증 사진"]):
            # 반응 추가 전에 권한 확인
            if message.guild and message.channel.permissions_for(message.guild.me).add_reactions:
                await message.add_reaction('👍')

            webhook_url = "https://koreahub.us/webhook/discord"
            image_urls = []
            
            # 첨부 파일 검증 개선
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    # 파일 크기 제한 확인 (예: 8MB)
                    if attachment.size <= 8 * 1024 * 1024:  
                        image_urls.append(attachment.url)
            
            if not image_urls:
                await message.channel.send("Please attach an image.")
                return

            webhook_data = {
                "author":
                message.author.name,
                "content":
                message.content,
                "image_urls":
                image_urls,
                "sent_at":
                datetime.datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
            }

            if await send_webhook(webhook_url, webhook_data):
                await message.channel.send(
                    f"{message.author.name}, Your time has been recorded. The bill comes due. Always!"
                )
            else:
                await message.channel.send("Verification Error occured. Please try again.")

    except discord.Forbidden:
        await message.channel.send("Bot doesn't have permission to add reactions.")
    except Exception as e:
        print(f"An error occurred in on_message: {e}")
        await message.channel.send("An error occurred in on_message.")

    await bot.process_commands(message)


async def cleanup():
    if session:
        await session.close()  # 비동기로 세션 정리


@bot.event
async def on_shutdown():
    await cleanup()


@tasks.loop(time=datetime.time(hour=UTC_DAILY_CHECK_HOUR, minute=DAILY_CHECK_MINUTE, tzinfo=datetime.timezone.utc))
async def check_daily_verification():
    try:
        current_time = datetime.datetime.now(pytz.timezone('Asia/Seoul'))
        print(f"Starting daily verification check (KST): {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

        channel = bot.get_channel(int(VERIFICATION_CHANNEL_ID))
        if not channel or not isinstance(channel, discord.TextChannel):
            print(f"Channel check failed: {VERIFICATION_CHANNEL_ID}")
            return

        print(f"Channel check successful: {channel.name}")

        # 권한 확인
        permissions = channel.permissions_for(channel.guild.me)
        if not all([permissions.read_message_history, permissions.view_channel, permissions.send_messages]):
            print("Missing required permissions")
            return

        # 날짜 범위 설정을 KST 기준으로 변경
        now = datetime.datetime.now(pytz.timezone('Asia/Seoul'))
        today_start = now.replace(
            hour=DAILY_START_HOUR, 
            minute=DAILY_START_MINUTE, 
            second=0, 
            microsecond=0
        )
        today_end = now

        verified_users: set[int] = set()
        try:
            async for message in channel.history(
                after=today_start, 
                before=today_end,
                limit=MESSAGE_HISTORY_LIMIT
            ):
                if any(keyword in message.content for keyword in ["인증사진", "인증 사진"]):
                    if message.attachments:
                        verified_users.add(message.author.id)
        except discord.Forbidden:
            print("Missing permission to read message history")
            return
        except discord.HTTPException as e:
            print(f"Error while fetching message history: {e}")
            return

        try:
            unverified_members = []
            async for member in channel.guild.fetch_members():
                if not member.bot and member.id not in verified_users:
                    unverified_members.append(member)
        except discord.Forbidden:
            print("Missing permission to fetch member list")
            return

        if unverified_members:
            mention_chunks = []
            current_chunk = []
            current_length = 0
            
            for member in unverified_members:
                mention = member.mention
                if current_length + len(mention) + 1 > 1900:
                    mention_chunks.append(current_chunk)
                    current_chunk = []
                    current_length = 0
                current_chunk.append(mention)
                current_length += len(mention) + 1
            
            if current_chunk:
                mention_chunks.append(current_chunk)

            for chunk in mention_chunks:
                mention_text = " ".join(chunk)
                try:
                    await channel.send(
                        f"⚠️ 아직 오늘의 인증을 하지 않은 멤버들이에요:\n{mention_text}\n"
                        "자정까지 2시간 남았어요! 오늘의 기록 인증을 올리는 것 잊지 마세요! 💪"
                    )
                except discord.HTTPException as e:
                    print(f"메시지 전송 중 오류: {e}")
                    continue
        else:
            # 모든 멤버가 인증한 경우
            try:
                await channel.send(
                    "🎉 모든 멤버가 인증을 완료했네요!\n"
                    "💪 여러분의 꾸준한 노력이 멋져요. 내일도 힘내세요! 💫"
                )
                print("모든 멤버 인증 완료 메시지 전송")
            except discord.HTTPException as e:
                print(f"메시지 전송 중 오류: {e}")

        # 처리 결과 로깅 추가
        print(f"Number of unverified members: {len(unverified_members)}")
        print("Daily verification check completed")

    except Exception as e:
        print(f"Error during verification check: {str(e)}")
        import traceback
        print(traceback.format_exc())
    finally:
        verified_users.clear()

@check_daily_verification.before_loop
async def before_check():
    await bot.wait_until_ready()
    print("Daily verification check task ready")


@tasks.loop(time=datetime.time(hour=UTC_YESTERDAY_CHECK_HOUR, minute=YESTERDAY_CHECK_MINUTE, tzinfo=datetime.timezone.utc))
async def check_yesterday_verification():
    try:
        current_time = datetime.datetime.now(pytz.timezone('Asia/Seoul'))
        print(f"Starting previous day verification check (KST): {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

        channel = bot.get_channel(int(VERIFICATION_CHANNEL_ID))
        if not channel or not isinstance(channel, discord.TextChannel):
            print(f"Channel check failed: {VERIFICATION_CHANNEL_ID}")
            return

        # 날짜 범위 설정을 KST 기준으로 변경
        now = datetime.datetime.now(pytz.timezone('Asia/Seoul'))
        yesterday = now - datetime.timedelta(days=1)
        yesterday_weekday = yesterday.weekday()  # 어제의 요일 확인 (0=월요일, 6=일요일)
        
        # 토요일(5)이나 일요일(6)의 인증은 체크하지 않음
        if yesterday_weekday in [5, 6]:
            print(f"주말({['월','화','수','목','금','토','일'][yesterday_weekday]}요일)은 인증 체크를 하지 않습니다.")
            return

        yesterday_start = yesterday.replace(
            hour=DAILY_START_HOUR, 
            minute=DAILY_START_MINUTE, 
            second=0, 
            microsecond=0
        )
        yesterday_end = yesterday.replace(
            hour=DAILY_END_HOUR, 
            minute=DAILY_END_MINUTE, 
            second=DAILY_END_SECOND, 
            microsecond=999999
        )

        verified_users: set[int] = set()
        try:
            async for message in channel.history(
                after=yesterday_start, 
                before=yesterday_end,
                limit=MESSAGE_HISTORY_LIMIT
            ):
                if any(keyword in message.content for keyword in ["인증사진", "인증 사진"]):
                    if message.attachments:
                        verified_users.add(message.author.id)
        except discord.Forbidden:
            print("Missing permission to read message history")
            return
        except discord.HTTPException as e:
            print(f"Error while fetching message history: {e}")
            return

        try:
            unverified_members = []
            async for member in channel.guild.fetch_members():
                if not member.bot and member.id not in verified_users:
                    unverified_members.append(member)
        except discord.Forbidden:
            print("Missing permission to fetch member list")
            return

        if unverified_members:
            mention_chunks = []
            current_chunk = []
            current_length = 0
            
            for member in unverified_members:
                mention = member.mention
                if current_length + len(mention) + 1 > 1900:
                    mention_chunks.append(current_chunk)
                    current_chunk = []
                    current_length = 0
                current_chunk.append(mention)
                current_length += len(mention) + 1
            
            if current_chunk:
                mention_chunks.append(current_chunk)

            for chunk in mention_chunks:
                mention_text = " ".join(chunk)
                try:
                    # 현재가 월요일인 경우 (어제가 일요일(6)인 경우)
                    if now.weekday() == 0:
                        await channel.send(
                            f"⚠️ 지난 주 금요일 인증을 하지 않은 멤버(들)입니다:\n{mention_text}\n"
                            "벌칙을 수행해 주세요!"
                        )
                    else:
                        await channel.send(
                            f"⚠️ 어제 인증을 하지 않은 멤버(들)입니다:\n{mention_text}\n"
                            "벌칙을 수행해 주세요!"
                        )
                except discord.HTTPException as e:
                    print(f"메시지 전송 중 오류: {e}")
                    continue
        else:
            # 모든 멤버가 인증한 경우
            try:
                await channel.send(
                    "🎉 어제는 모든 멤버가 인증을 완료했네요!\n"
                    "💪 여러분의 꾸준한 노력이 대단합니다. 오늘도 힘내세요! 💫"
                )
                print("모든 멤버 인증 완료 메시지 전송")
            except discord.HTTPException as e:
                print(f"메시지 전송 중 오류: {e}")

        print(f"Number of unverified members from previous day: {len(unverified_members)}")
        print("Previous day verification check completed")

    except Exception as e:
        print(f"Error during previous day verification check: {str(e)}")
        import traceback
        print(traceback.format_exc())
    finally:
        verified_users.clear()

@check_yesterday_verification.before_loop
async def before_yesterday_check():
    await bot.wait_until_ready()
    print("Previous day verification check task ready")


try:
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        raise ValueError("Discord Bot Token is missing. Please check .env file.")
    print("Starting bot...")
    print(f"Channel ID configured: {VERIFICATION_CHANNEL_ID}")
    print(f"Intents status:")
    print(f"- members: {intents.members}")
    print(f"- message_content: {intents.message_content}")
    print(f"- guilds: {intents.guilds}")
    bot.run(TOKEN)
except Exception as e:
    print(f"Bot error: {str(e)}")
    import traceback
    print(traceback.format_exc())
finally:
    if session:
        asyncio.get_event_loop().run_until_complete(cleanup())
