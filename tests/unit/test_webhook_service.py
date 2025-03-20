"""
WebhookService 테스트
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import aiohttp
import asyncio

@pytest.mark.asyncio
async def test_initialize(webhook_service, mock_session):
    """세션 초기화 테스트"""
    await webhook_service.initialize()
    assert webhook_service.session is not None

@pytest.mark.asyncio
async def test_cleanup(webhook_service):
    """세션 정리 테스트"""
    # session을 직접 mock_session으로 설정
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
    # 성공 응답 모킹
    response = AsyncMock()
    response.status = 200
    response.text = AsyncMock(return_value="Success")
    
    # post 메서드 모킹
    webhook_service.session.post = AsyncMock(return_value=response)
    
    # 테스트 실행
    webhook_data = {"test": "data"}
    result = await webhook_service.send_webhook(webhook_data)
    
    # 검증
    assert result is True
    webhook_service.session.post.assert_called_once_with(
        webhook_service.config.WEBHOOK_URL,
        json=webhook_data,
        timeout=webhook_service.config.WEBHOOK_TIMEOUT
    )

@pytest.mark.asyncio
async def test_send_webhook_error(webhook_service):
    """웹훅 전송 실패 테스트"""
    # 실패 응답 모킹
    response = AsyncMock()
    response.status = 404
    response.text = AsyncMock(return_value="Not Found")
    
    # post 메서드 모킹
    webhook_service.session.post = AsyncMock(return_value=response)
    
    # 테스트 실행
    webhook_data = {"test": "data"}
    result = await webhook_service.send_webhook(webhook_data)
    
    # 검증
    assert result is False
    webhook_service.session.post.assert_called_once()

@pytest.mark.asyncio
async def test_send_webhook_rate_limit(webhook_service):
    """웹훅 전송 속도 제한 테스트"""
    # 첫 번째 호출에서는 속도 제한 응답
    rate_limit_response = AsyncMock()
    rate_limit_response.status = 429
    rate_limit_response.headers = {"Retry-After": "1"}
    rate_limit_response.text = AsyncMock(return_value="Rate Limited")
    
    # 두 번째 호출에서는 성공 응답
    success_response = AsyncMock()
    success_response.status = 200
    success_response.text = AsyncMock(return_value="Success")
    
    # 연속적인 호출에 다른 응답 반환
    webhook_service.session.post = AsyncMock(side_effect=[rate_limit_response, success_response])
    
    # sleep 메서드 모킹
    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        # 테스트 실행
        webhook_data = {"test": "data"}
        result = await webhook_service.send_webhook(webhook_data)
        
        # 검증
        assert result is True
        assert webhook_service.session.post.call_count == 2
        mock_sleep.assert_called_once_with(1) 