"""
메시지 처리 통합 테스트
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import discord
import datetime

class TestMessageProcessing:
    @pytest.fixture
    def setup_bot(self):
        # 설정 모의 객체 생성
        config = MagicMock()
        config.VERIFICATION_KEYWORDS = ["인증사진", "인증 사진"]
        
        # 봇 생성
        with patch('discord.ext.commands.Bot', autospec=True):
            from bot import VerificationBot
            bot = VerificationBot(config)
            
            # 서비스 모킹
            bot.verification_service = MagicMock()
            bot.verification_service.process_verification_message = AsyncMock()
            bot.verification_service.process_vacation_request = AsyncMock()
            
            # 메시지 유틸리티 모킹
            def is_verification_message(content):
                return any(keyword in content for keyword in config.VERIFICATION_KEYWORDS)
                
            def is_vacation_message(content):
                return "휴가" in content and not is_verification_message(content)
            
            bot.message_util.is_verification_message = is_verification_message
            bot.message_util.is_vacation_message = is_vacation_message
            
            yield bot
    
    @pytest.mark.asyncio
    async def test_on_message_verification(self, setup_bot):
        """인증 메시지 처리 테스트"""
        bot = setup_bot
        
        # 메시지 모의 객체 생성
        message = AsyncMock()
        message.author = MagicMock(id=12345)
        message.author.bot = False
        message.content = "인증사진 올립니다"
        
        # 메시지 처리 이벤트 호출
        on_message = [h for h in bot.bot.event.call_args_list if h[0][0].__name__ == 'on_message'][0][0][0]
        await on_message(message)
        
        # verification_service.process_verification_message 호출 확인
        bot.verification_service.process_verification_message.assert_called_once_with(message)
        bot.verification_service.process_vacation_request.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_on_message_vacation(self, setup_bot):
        """휴가 메시지 처리 테스트"""
        bot = setup_bot
        
        # 메시지 모의 객체 생성
        message = AsyncMock()
        message.author = MagicMock(id=12345)
        message.author.bot = False
        message.content = "휴가 2023-01-15 ~ 2023-01-20"
        
        # 메시지 처리 이벤트 호출
        on_message = [h for h in bot.bot.event.call_args_list if h[0][0].__name__ == 'on_message'][0][0][0]
        await on_message(message)
        
        # verification_service.process_vacation_request 호출 확인
        bot.verification_service.process_vacation_request.assert_called_once_with(message)
        bot.verification_service.process_verification_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_on_message_normal(self, setup_bot):
        """일반 메시지 처리 테스트"""
        bot = setup_bot
        
        # 메시지 모의 객체 생성
        message = AsyncMock()
        message.author = MagicMock(id=12345)
        message.author.bot = False
        message.content = "안녕하세요"
        
        # 메시지 처리 이벤트 호출
        on_message = [h for h in bot.bot.event.call_args_list if h[0][0].__name__ == 'on_message'][0][0][0]
        await on_message(message)
        
        # 어떤 처리 함수도 호출되지 않아야 함
        bot.verification_service.process_verification_message.assert_not_called()
        bot.verification_service.process_vacation_request.assert_not_called() 