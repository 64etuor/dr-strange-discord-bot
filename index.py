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

@bot.event
async def on_ready():
    global session, VERIFICATION_CHANNEL_ID
    if session is None:
        session = aiohttp.ClientSession()
    VERIFICATION_CHANNEL_ID = int(os.getenv('VERIFICATION_CHANNEL_ID', '0'))
    check_daily_verification.start()  # 스케줄러 시작
    print(f'Logged in as {bot.user}')


@bot.command()
async def hello(ctx):
    await ctx.send('Hello!')


@bot.command()
async def check_now(ctx):
    """테스트용: 즉시 인증 체크를 실행합니다"""
    await ctx.send("인증 체크를 시작합니다...")
    await check_daily_verification()
    await ctx.send("인증 체크가 완료되었습니다.")


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


# 11시에 실행 태스크
@tasks.loop(time=datetime.time(hour=23, minute=0))
async def check_daily_verification():
    try:
        current_time = datetime.datetime.now(pytz.timezone('Asia/Seoul'))
        print(f"인증 체크 시작: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

        channel = bot.get_channel(int(VERIFICATION_CHANNEL_ID))
        if not channel or not isinstance(channel, discord.TextChannel):
            print(f"채널 확인 실패: {VERIFICATION_CHANNEL_ID}")
            return

        print(f"채널 확인 성공: {channel.name}")

        # 권한 확인
        permissions = channel.permissions_for(channel.guild.me)
        if not all([permissions.read_message_history, permissions.view_channel, permissions.send_messages]):
            print("필요한 권한이 없습니다")
            return

        now = datetime.datetime.now(pytz.timezone('Asia/Seoul'))
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
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
            print("메시지 히스토리 읽기 권한이 없습니다.")
            return
        except discord.HTTPException as e:
            print(f"메시지 히스토리 조회 중 오류: {e}")
            return

        try:
            unverified_members = []
            async for member in channel.guild.fetch_members():
                if not member.bot and member.id not in verified_users:
                    unverified_members.append(member)
        except discord.Forbidden:
            print("멤버 목록 조회 권한이 없습니다.")
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
                        f"⚠️ 아직 오늘 인증을 하지 않은 멤버들입니다:\n{mention_text}\n"
                        "자정까지 1시간 남았습니다! 오늘의 인증사진 올리는 것 잊지 마세요! 💪"
                    )
                except discord.HTTPException as e:
                    print(f"메시지 전송 중 오류: {e}")
                    continue
        else:
            # 모든 멤버가 인증한 경우
            try:
                await channel.send(
                    "🎉 모든 멤버가 인증을 완료했습니다!\n"
                    "💪 여러분의 꾸준한 노력이 멋집니다. 내일도 힘내세요! 💫"
                )
                print("모든 멤버 인증 완료 메시지 전송")
            except discord.HTTPException as e:
                print(f"메시지 전송 중 오류: {e}")

        # 처리 결과 로깅 추가
        print(f"확인된 미인증 멤버 수: {len(unverified_members)}")
        print("인증 체크 완료")

    except Exception as e:
        print(f"인증 체크 중 오류 발생: {str(e)}")
        import traceback
        print(traceback.format_exc())
    finally:
        verified_users.clear()

@check_daily_verification.before_loop
async def before_check():
    await bot.wait_until_ready()
    print("인증 체크 태스크 준비 완료")


try:
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        raise ValueError("Discord Bot Token is missing. Please check .env file.")
    bot.run(TOKEN)
except Exception as e:
    print(f"Bot error: {e}")
finally:
    if session:
        asyncio.get_event_loop().run_until_complete(cleanup())
