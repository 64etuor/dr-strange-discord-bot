import discord
import aiohttp
from discord.ext import commands
from datetime import datetime
import pytz
import asyncio
import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# 전역 변수로 session 선언
session = None


@bot.event
async def on_ready():
    global session
    session = aiohttp.ClientSession()
    print(f'Logged in as {bot.user}')


@bot.command()
async def hello(ctx):
    await ctx.send('Hello!')


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
        if "인증사진" in message.content or "인증 사진" in message.content:
            await message.add_reaction('👍')

            webhook_url = "https://koreahub.us/webhook/discord"
            image_urls = [
                attachment.url for attachment in message.attachments
                if attachment.content_type
                and attachment.content_type.startswith('image/')
            ]

            webhook_data = {
                "author":
                message.author.name,
                "content":
                message.content,
                "image_urls":
                image_urls,
                "sent_at":
                datetime.now(
                    pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
            }

            if await send_webhook(webhook_url, webhook_data):
                await message.channel.send(
                    f"{message.author.name}, Your time has been recorded. The bill comes due. Always!"
                )
            else:
                await message.channel.send("인증 처리 중 오류가 발생했습니다.")

    except Exception as e:
        print(f"An error occurred in on_message: {e}")

    await bot.process_commands(message)


try:
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        raise ValueError("Discord 토큰이 설정되지 않았습니다. .env 파일을 확인해주세요.")
    bot.run(TOKEN)
except Exception as e:
    print(f"Bot error: {e}")
finally:
    if session:
        asyncio.run(session.close())
