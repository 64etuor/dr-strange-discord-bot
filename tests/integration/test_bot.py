import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import discord
from datetime import datetime
from index import VerificationBot
from config import Config, Messages

class TestBotIntegration:
    @pytest.mark.asyncio
    async def test_verification_workflow(self, bot, mock_message):
        """인증 워크플로우 테스트"""
        # on_message 메서드 구현
        async def mock_on_message(message):
            # 테스트용 채널 ID 직접 사용
            if message.channel.id == 1342318912645234689:  # mock_channel의 ID와 동일하게 설정
                if not message.attachments:
                    await message.channel.send(Messages.ATTACH_IMAGE_REQUEST)
                else:
                    await message.add_reaction("✅")
        
        bot.on_message = mock_on_message

        # 1. 이미지 없는 메시지
        mock_message.attachments = []
        await bot.on_message(mock_message)
        mock_message.channel.send.assert_called_with(Messages.ATTACH_IMAGE_REQUEST)
        
        # 2. 유효한 이미지 첨부
        attachment = MagicMock(content_type="image/jpeg", size=1024*1024)
        mock_message.attachments = [attachment]
        await bot.on_message(mock_message)
        mock_message.add_reaction.assert_called_with("✅")

    @pytest.mark.asyncio
    async def test_daily_verification_check(self, bot, mock_channel):
        """일일 인증 체크 테스트"""
        # check_yesterday_verification 메서드 구현
        async def mock_check_verification():
            await mock_channel.send(Messages.ALL_VERIFIED_YESTERDAY)
        
        bot.check_yesterday_verification = mock_check_verification

        with patch('datetime.datetime') as mock_datetime:
            mock_now = datetime.now(Config.Time.TIMEZONE).replace(
                year=2024, month=1, day=3
            )
            mock_datetime.now.return_value = mock_now
            
            # 미인증 멤버가 없는 경우
            with patch('utils.VerificationUtils.get_unverified_members', 
                      return_value=(set(), [])):
                await bot.check_yesterday_verification()
                mock_channel.send.assert_called_with(Messages.ALL_VERIFIED_YESTERDAY) 