"""
MessageUtility 테스트
"""
import pytest
from unittest.mock import MagicMock, patch
import discord

def test_is_verification_message(message_util):
    """인증 메시지 확인 테스트"""
    # 인증 키워드가 포함된 메시지
    assert message_util.is_verification_message("오늘의 인증사진입니다") == True
    assert message_util.is_verification_message("인증 사진 올립니다!") == True
    
    # 인증 키워드가 없는 메시지
    assert message_util.is_verification_message("안녕하세요") == False
    assert message_util.is_verification_message("인증했어요") == False

def test_is_valid_image(message_util):
    """유효한 이미지 확인 테스트"""
    # 유효한 이미지
    valid_attachment = MagicMock(spec=discord.Attachment)
    valid_attachment.content_type = "image/jpeg"
    valid_attachment.size = 1024 * 1024  # 1MB
    
    assert message_util.is_valid_image(valid_attachment) == True
    
    # 유효하지 않은 이미지 (타입)
    invalid_type = MagicMock(spec=discord.Attachment)
    invalid_type.content_type = "application/pdf"
    invalid_type.size = 1024 * 1024
    
    assert message_util.is_valid_image(invalid_type) == False
    
    # 유효하지 않은 이미지 (크기)
    invalid_size = MagicMock(spec=discord.Attachment)
    invalid_size.content_type = "image/png"
    invalid_size.size = 20 * 1024 * 1024  # 20MB (MAX는 8MB)
    
    assert message_util.is_valid_image(invalid_size) == False

def test_chunk_mentions(message_util):
    """멘션 청크 테스트"""
    # 멤버 목록 생성
    members = []
    for i in range(10):
        member = MagicMock()
        member.mention = f"<@{i}>" * 100  # 긴 멘션 문자열
        members.append(member)
    
    chunks = message_util.chunk_mentions(members)
    
    # 최소 2개 이상의 청크로 나뉘었는지 확인
    assert len(chunks) >= 2
    
    # 모든 청크가 최대 길이 이하인지 확인
    for chunk in chunks:
        assert len(chunk) <= message_util.config.MAX_MESSAGE_LENGTH 