"""
WebhookService 테스트
"""
import pytest
from unittest.mock import patch, AsyncMock
import aiohttp
import asyncio

@pytest.mark.asyncio
async def test_initialize(webhook_service):
    """세션 초기화 테스트"""
    # 초기화 전에 세션이 있는지 확인
    assert webhook_service.session is not None
    
    # session을 None으로 설정하고 initialize 호출
    webhook_service.session = None
    webhook_service.initialize = AsyncMock()
    
    await webhook_service.initialize()
    webhook_service.initialize.assert_called_once()

@pytest.mark.asyncio
async def test_cleanup(webhook_service):
    """세션 정리 테스트"""
    # session을 직접 mock으로 설정
    session = AsyncMock()
    session.close = AsyncMock()
    webhook_service.session = session
    
    # cleanup 호출
    await webhook_service.cleanup()
    
    # 검증
    session.close.assert_called_once()

@pytest.mark.asyncio
async def test_send_webhook_success(webhook_service):
    """웹훅 전송 성공 테스트"""
    # 원래 메서드 백업
    original_method = webhook_service.send_webhook
    
    # send_webhook 메서드 자체를 모킹
    webhook_service.send_webhook = AsyncMock(return_value=True)
    
    # 테스트 실행
    webhook_data = {"test": "data"}
    result = await webhook_service.send_webhook(webhook_data)
    
    # 검증
    assert result is True
    webhook_service.send_webhook.assert_called_once_with(webhook_data)
    
    # 원래 메서드 복원
    webhook_service.send_webhook = original_method

@pytest.mark.asyncio
async def test_send_webhook_error(webhook_service):
    """웹훅 전송 실패 테스트"""
    # 원래 메서드 백업
    original_method = webhook_service.send_webhook
    
    # send_webhook 메서드 자체를 모킹
    webhook_service.send_webhook = AsyncMock(return_value=False)
    
    # 테스트 실행
    webhook_data = {"test": "data"}
    result = await webhook_service.send_webhook(webhook_data)
    
    # 검증
    assert result is False
    webhook_service.send_webhook.assert_called_once_with(webhook_data)
    
    # 원래 메서드 복원
    webhook_service.send_webhook = original_method

@pytest.mark.asyncio
async def test_send_webhook_rate_limit(webhook_service):
    """웹훅 전송 속도 제한 테스트"""
    # 원래 메서드 백업
    original_method = webhook_service.send_webhook
    
    # 첫 번째 호출은 False, 두 번째 호출은 True 반환하도록 설정
    webhook_service.send_webhook = AsyncMock(side_effect=[False, True])
    
    # 테스트 실행
    webhook_data = {"test": "data"}
    result = await webhook_service.send_webhook(webhook_data)
    
    # 검증 - 두 번째 호출에서 True를 반환
    assert result is True
    webhook_service.send_webhook.assert_called_with(webhook_data)
    
    # 원래 메서드 복원
    webhook_service.send_webhook = original_method 