"""
VerificationService 테스트
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import discord
import datetime
import pytz

@pytest.mark.asyncio
async def test_get_verification_data(verification_service, mock_channel):
    """인증 데이터 가져오기 테스트"""
    # 메시지 모킹
    message1 = MagicMock()
    message1.author = MagicMock(id=123)
    message1.content = "인증사진 올립니다"
    
    valid_attachment = MagicMock()
    valid_attachment.content_type = "image/jpeg"
    valid_attachment.size = 1024 * 1024
    message1.attachments = [valid_attachment]
    
    # 모의 비동기 이터레이터 생성
    class AsyncIterator:
        def __init__(self, items):
            self.items = items
            self.index = 0
            
        def __aiter__(self):
            return self
            
        async def __anext__(self):
            try:
                value = self.items[self.index]
                self.index += 1
                return value
            except IndexError:
                raise StopAsyncIteration
    
    # 채널의 history 메서드를 모킹
    mock_channel.history.return_value = AsyncIterator([message1])
    
    # 멤버 목록을 위한 비동기 이터레이터
    unverified_member = MagicMock(id=456, bot=False)
    bot_member = MagicMock(id=789, bot=True)
    mock_channel.guild.fetch_members.return_value = AsyncIterator([unverified_member, bot_member])
    
    # 테스트 실행
    start_time = datetime.datetime.now(pytz.UTC)
    end_time = start_time + datetime.timedelta(hours=1)
    
    verified_users, unverified_members = await verification_service.get_verification_data(
        mock_channel, start_time, end_time
    )
    
    # 검증
    assert len(verified_users) == 1
    assert 123 in verified_users
    assert len(unverified_members) == 1
    assert unverified_members[0].id == 456

@pytest.mark.asyncio
async def test_process_verification_message(verification_service):
    """인증 메시지 처리 테스트"""
    # 메시지 모킹
    message = AsyncMock()
    message.add_reaction = AsyncMock()  # 직접 add_reaction 메서드 추가
    message.author = MagicMock(name="TestUser")
    message.channel = AsyncMock()
    message.channel.send = AsyncMock()
    
    # 권한 설정
    permissions = MagicMock()
    permissions.add_reactions = True
    
    message.guild = MagicMock()
    message.guild.me = MagicMock()
    
    # permissions_for를 일반 메서드로 설정
    message.channel.permissions_for = MagicMock(return_value=permissions)
    
    # 유효한 이미지 모킹
    valid_attachment = MagicMock()
    valid_attachment.content_type = "image/jpeg"
    valid_attachment.size = 1024 * 1024
    valid_attachment.url = "https://example.com/image.jpg"
    
    message.attachments = [valid_attachment]
    
    # webhook_service.send_webhook 모킹
    verification_service.webhook_service.send_webhook = AsyncMock(return_value=True)
    
    # 테스트 실행
    await verification_service.process_verification_message(message)
    
    # 검증
    message.add_reaction.assert_called_once_with('✅')
    verification_service.webhook_service.send_webhook.assert_called_once()
    message.channel.send.assert_called_once()

@pytest.mark.asyncio
async def test_send_unverified_messages_with_members(verification_service, mock_channel):
    """미인증 멤버 메시지 전송 테스트 (멤버 있음)"""
    # 미인증 멤버 생성
    members = []
    for i in range(3):
        member = MagicMock()
        member.mention = f"<@{i}>"
        members.append(member)
    
    # 테스트 실행
    await verification_service.send_unverified_messages(
        mock_channel, members, "Unverified: {members}"
    )
    
    # 검증
    mock_channel.send.assert_called_once()
    assert "Unverified:" in mock_channel.send.call_args[0][0]
    assert "<@0>" in mock_channel.send.call_args[0][0]
    assert "<@1>" in mock_channel.send.call_args[0][0]
    assert "<@2>" in mock_channel.send.call_args[0][0]

@pytest.mark.asyncio
async def test_send_unverified_messages_empty(verification_service, mock_channel):
    """미인증 멤버 메시지 전송 테스트 (멤버 없음)"""
    # 테스트 실행
    await verification_service.send_unverified_messages(
        mock_channel, [], "Unverified: {members}"
    )
    
    # 검증 - 모든 멤버가 인증한 메시지
    mock_channel.send.assert_called_once()
    assert "모든 멤버가 인증을 완료했네요" in mock_channel.send.call_args[0][0] 