"""
ConfigManager 테스트
"""
import os
import pytest
from config_manager import ConfigManager
import datetime

def test_config_loading(config_manager):
    """설정 로드 테스트"""
    # 기본 설정이 로드되었는지 확인
    assert config_manager.TOKEN == 'test_token'
    assert config_manager.VERIFICATION_CHANNEL_ID == 123456789
    assert config_manager.WEBHOOK_URL == 'https://test.webhook.url'
    
    # 메시지 설정 확인
    assert "Your time has been recorded" in config_manager.MESSAGES['verification_success']
    
    # 인증 키워드 확인
    assert "인증사진" in config_manager.VERIFICATION_KEYWORDS
    assert "인증 사진" in config_manager.VERIFICATION_KEYWORDS

def test_holidays_loading(config_manager):
    """공휴일 로드 테스트"""
    # 공휴일이 로드되었는지 확인
    assert len(config_manager.HOLIDAYS) == 2
    assert "2025-01-01" in config_manager.HOLIDAYS
    assert "2025-05-05" in config_manager.HOLIDAYS
    
    # 공휴일 체크 함수 테스트
    holiday_date = datetime.datetime(2025, 1, 1)
    assert config_manager.is_holiday(holiday_date) == True
    
    normal_date = datetime.datetime(2025, 1, 2)
    assert config_manager.is_holiday(normal_date) == False

def test_default_config(temp_config_file):
    """기본 설정 테스트"""
    # 설정 파일을 지우고 기본값 사용 테스트
    os.remove(temp_config_file)
    
    # 환경 변수 설정
    os.environ['DISCORD_TOKEN'] = 'default_test_token'
    
    config = ConfigManager(config_file=temp_config_file)
    # 기본값 확인
    assert config.MAX_MESSAGE_LENGTH == 1900
    assert config.MAX_ATTACHMENT_SIZE == 8 * 1024 * 1024
    assert config.TIMEZONE.zone == 'Asia/Seoul' 