"""
VerificationService 테스트
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import discord
import datetime
import pytz

@pytest.mark.asyncio
async def test_process_verification_message(verification_service, mock_channel):
    """인증 메시지 처리 테스트"""
    # 메시지 모킹
    message = AsyncMock()
    message.add_reaction = AsyncMock()
    message.author = MagicMock(name="TestUser")
    message.channel = mock_channel
    
    # 유효한 이미지 모킹
    valid_attachment = MagicMock()
    valid_attachment.content_type = "image/jpeg"
    valid_attachment.size = 1024 * 1024
    valid_attachment.url = "https://example.com/image.jpg"
    
    message.attachments = [valid_attachment]
    
    # webhook_service.send_webhook 모킹
    verification_service.webhook_service.send_webhook = AsyncMock(return_value=True)
    
    # message_util.is_valid_image 모킹
    verification_service.message_util.is_valid_image = MagicMock(return_value=True)
    
    # 테스트 실행
    await verification_service.process_verification_message(message)
    
    # 검증
    message.add_reaction.assert_called_once_with('✅')
    verification_service.webhook_service.send_webhook.assert_called_once()
    mock_channel.send.assert_called_once()

@pytest.mark.asyncio
async def test_send_unverified_messages_with_members(verification_service, mock_channel):
    """미인증 멤버 메시지 전송 테스트 (멤버 있음)"""
    # 미인증 멤버 생성
    members = []
    for i in range(3):
        member = MagicMock()
        member.mention = f"<@{i}>"
        members.append(member)
    
    # chunk_mentions 모킹
    verification_service.message_util.chunk_mentions = MagicMock(return_value=["<@0> <@1> <@2>"])
    
    # 테스트 실행
    await verification_service.send_unverified_messages(
        mock_channel, members, "Unverified: {members}"
    )
    
    # 검증
    mock_channel.send.assert_called_once_with("Unverified: <@0> <@1> <@2>")

@pytest.mark.asyncio
async def test_send_unverified_messages_empty(verification_service, mock_channel):
    """미인증 멤버 메시지 전송 테스트 (멤버 없음)"""
    # 테스트 실행
    await verification_service.send_unverified_messages(
        mock_channel, [], "Unverified: {members}"
    )
    
    # 검증 - 모든 멤버가 인증한 메시지
    mock_channel.send.assert_called_once()
    assert verification_service.config.MESSAGES['all_verified'] in mock_channel.send.call_args[0][0] 