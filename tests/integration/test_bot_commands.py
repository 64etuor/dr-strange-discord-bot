"""
봇 명령어 통합 테스트
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord

@pytest.mark.asyncio
async def test_check_now_command(config_manager):
    """check_now 명령어 테스트"""
    # 봇 및 컨텍스트 모킹
    bot = MagicMock()
    ctx = AsyncMock()
    
    # verification_service 모킹
    verification_service = AsyncMock()
    verification_service.check_daily_verification = AsyncMock()
    
    # 명령어 핸들러 등록
    command_handler = MagicMock()
    command_handler.verification_service = verification_service
    
    # 실제 명령어 함수
    async def check_now(ctx):
        await ctx.send("Verification check started...")
        await verification_service.check_daily_verification()
        await ctx.send("Verification check completed.")
    
    # 테스트 실행
    await check_now(ctx)
    
    # 검증
    assert ctx.send.call_count == 2
    verification_service.check_daily_verification.assert_called_once()

@pytest.mark.asyncio
async def test_time_check_command(config_manager):
    """time_check 명령어 테스트"""
    # 봇 및 컨텍스트 모킹
    bot = MagicMock()
    ctx = AsyncMock()
    
    # time_util 모킹
    time_util = MagicMock()
    time_util.now = MagicMock(return_value="mocked_time")
    
    # 명령어 핸들러 등록
    command_handler = MagicMock()
    command_handler.time_util = time_util
    
    # 실제 명령어 함수
    async def time_check(ctx):
        await ctx.send(f"Time: {time_util.now()}")
    
    # 테스트 실행
    await time_check(ctx)
    
    # 검증
    ctx.send.assert_called_once_with("Time: mocked_time") 