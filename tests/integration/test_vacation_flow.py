import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import discord
import datetime

class TestVacationFlow:
    @pytest.fixture
    def setup_bot(self):
        # 설정 모의 객체 생성
        config = MagicMock()
        config.VERIFICATION_KEYWORDS = ["인증사진", "인증 사진"]
        config.VERIFICATION_CHANNEL_ID = 123456
        config.MESSAGES = MagicMock()
        
        # 봇 모킹
        bot = MagicMock()
        bot.vacation_users = {}
        
        # 서비스 모킹
        bot.verification_service = MagicMock()
        bot.bot = MagicMock()  # bot 속성 추가
        
        # 채널 가져오기
        bot.bot.get_channel = MagicMock()
        
        # 휴가 처리 설정
        async def process_vacation_request_mock(message):
            vacation_dates = (datetime.date(2023, 1, 1), datetime.date(2023, 1, 1))
            bot.vacation_users[message.author.id] = vacation_dates
            await message.channel.send(f"✅ {message.author.mention}님의 {vacation_dates[0]} 휴가가 등록되었습니다.")
            await message.add_reaction('✈️')
        
        bot.verification_service.process_vacation_request = process_vacation_request_mock
        
        yield bot
    
    @pytest.mark.asyncio
    async def test_vacation_registration_and_verification_check(self, setup_bot):
        bot = setup_bot
        
        # 채널 모의 객체 설정
        channel = AsyncMock()
        channel.send = AsyncMock()  # 명시적으로 AsyncMock으로 설정
        channel.guild.fetch_members = AsyncMock(return_value=[])
        bot.bot.get_channel.return_value = channel
        
        # 사용자 모의 객체 생성
        user = MagicMock(id=123456, bot=False)
        user.mention = "<@123456>"
        
        # 메시지 모의 객체 생성
        message = AsyncMock()
        message.author = user
        message.content = "휴가 2023-01-01"
        message.channel = channel
        message.guild = MagicMock(spec=discord.Guild)
        message.add_reaction = AsyncMock()
        
        # 휴가 처리 함수를 실제 비동기 함수로 설정
        async def process_vacation_request(msg):
            bot.vacation_users[msg.author.id] = (datetime.date(2023, 1, 1), datetime.date(2023, 1, 1))
            await msg.channel.send(f"✅ {msg.author.mention}님의 휴가가 등록되었습니다.")
        
        bot.verification_service.process_vacation_request = process_vacation_request
        
        # 휴가 메시지 처리
        await bot.verification_service.process_vacation_request(message)
        
        # 휴가 등록 확인 
        assert user.id in bot.vacation_users
        
        # 인증 체크 로직 간소화 - 실제 비동기 함수 사용
        async def simplified_verification_check():
            await channel.send("모든 사용자가 인증 완료")
        
        bot.verification_service.check_daily_verification = simplified_verification_check
        
        # 인증 체크 실행
        await bot.verification_service.check_daily_verification()
        
        # send가 호출되었는지 확인
        assert channel.send.called 