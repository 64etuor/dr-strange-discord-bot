"""
TimeUtility 테스트
"""
import pytest
from unittest.mock import patch
import datetime
import pytz

def test_is_weekend(time_util):
    """주말 확인 테스트"""
    # 월요일(0)
    assert time_util.is_weekend(0) == False
    # 금요일(4)
    assert time_util.is_weekend(4) == False
    # 토요일(5)
    assert time_util.is_weekend(5) == True
    # 일요일(6)
    assert time_util.is_weekend(6) == True

def test_should_skip_check(time_util, config_manager):
    """체크 건너뛰기 테스트"""
    # 주말(토요일)
    weekend_date = datetime.datetime(2023, 5, 6, tzinfo=pytz.timezone('Asia/Seoul'))
    assert time_util.should_skip_check(weekend_date) == True
    
    # 공휴일
    holiday_date = datetime.datetime(2025, 1, 1, tzinfo=pytz.timezone('Asia/Seoul'))
    assert time_util.should_skip_check(holiday_date) == True
    
    # 평일(월요일)
    normal_date = datetime.datetime(2023, 5, 1, tzinfo=pytz.timezone('Asia/Seoul'))
    assert time_util.should_skip_check(normal_date) == False

def test_get_check_date_range(time_util):
    """날짜 범위 계산 테스트"""
    # 특정 날짜에 대한 체크 범위 확인
    check_date = datetime.datetime(2023, 5, 1, tzinfo=pytz.timezone('Asia/Seoul'))
    start, end = time_util.get_check_date_range(check_date)
    
    # 시작은 당일 설정된 시간
    assert start.year == 2023
    assert start.month == 5
    assert start.day == 1
    assert start.hour == time_util.config.DAILY_START_HOUR
    
    # 종료는 다음날 설정된 시간
    assert end.year == 2023
    assert end.month == 5
    assert end.day == 2
    assert end.hour == time_util.config.DAILY_END_HOUR

def test_get_today_range(time_util):
    """오늘 범위 계산 테스트"""
    # 현재 시간이 시작 시간 이후일 때
    test_time = datetime.datetime(2023, 5, 1, 15, 0, 0, tzinfo=pytz.timezone('Asia/Seoul'))
    with patch.object(time_util, 'now', return_value=test_time):
        start, end = time_util.get_today_range()
        
        # 시작은 당일 설정된 시간
        assert start.year == 2023
        assert start.month == 5
        assert start.day == 1
        assert start.hour == time_util.config.DAILY_START_HOUR
        
        # 종료는 현재 시간
        assert end == test_time
    
    # 현재 시간이 시작 시간 이전일 때
    test_time = datetime.datetime(2023, 5, 1, 8, 0, 0, tzinfo=pytz.timezone('Asia/Seoul'))
    with patch.object(time_util, 'now', return_value=test_time):
        start, end = time_util.get_today_range()
        
        # 시작은 전날 설정된 시간
        assert start.year == 2023
        assert start.month == 4
        assert start.day == 30
        assert start.hour == time_util.config.DAILY_START_HOUR
        
        # 종료는 현재 시간
        assert end == test_time 