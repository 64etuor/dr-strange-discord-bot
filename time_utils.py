"""
시간 관련 유틸리티 모듈
"""
import datetime
from typing import Tuple

class TimeUtility:
    """시간 관련 유틸리티 클래스"""
    
    def __init__(self, config):
        self.config = config
    
    def now(self):
        """현재 시간 반환 (설정된 타임존 기준)"""
        return datetime.datetime.now(self.config.TIMEZONE)
    
    def is_weekend(self, weekday: int) -> bool:
        """주말인지 확인 (토: 5, 일: 6)"""
        return weekday in [5, 6]
    
    def should_skip_check(self, date):
        """해당 날짜의 체크를 건너뛰어야 하는지 확인 (주말 또는 공휴일)"""
        # 주말인지 확인
        if self.is_weekend(date.weekday()):
            return True
            
        # 공휴일인지 확인
        if self.config.SKIP_HOLIDAYS and self.config.is_holiday(date):
            return True
            
        return False
    
    def get_today_range(self) -> Tuple[datetime.datetime, datetime.datetime]:
        """오늘 날짜의 인증 시간 범위 반환"""
        current_time = self.now()
        
        # 하루가 12시부터 이튿날 새벽 3시까지인 경우
        # 시작 시간 설정
        start_time = current_time.replace(
            hour=self.config.DAILY_START_HOUR,
            minute=self.config.DAILY_START_MINUTE,
            second=0,
            microsecond=0
        )
        
        # 종료 시간이 새벽인 경우 (예: 03시)
        if self.config.DAILY_END_HOUR < 12:
            end_time = (current_time + datetime.timedelta(days=1)).replace(
                hour=self.config.DAILY_END_HOUR,
                minute=self.config.DAILY_END_MINUTE,
                second=self.config.DAILY_END_SECOND,
                microsecond=999999
            )
        else:
            end_time = current_time.replace(
                hour=self.config.DAILY_END_HOUR,
                minute=self.config.DAILY_END_MINUTE,
                second=self.config.DAILY_END_SECOND,
                microsecond=999999
            )
        
        # 현재 시간이 자정을 넘었지만 설정 종료 시간 이전인 경우 (새벽)
        current_hour = current_time.hour
        if current_hour < self.config.DAILY_END_HOUR:
            # 전날로부터 시작
            start_time = (current_time - datetime.timedelta(days=1)).replace(
                hour=self.config.DAILY_START_HOUR,
                minute=self.config.DAILY_START_MINUTE,
                second=0,
                microsecond=0
            )
        
        return start_time, end_time
    
    def get_check_date_range(self, check_date):
        """체크 날짜 범위 반환"""
        check_start = check_date.replace(
            hour=self.config.DAILY_START_HOUR,
            minute=self.config.DAILY_START_MINUTE,
            second=0,
            microsecond=0
        )
        
        check_end = (check_date + datetime.timedelta(days=1)).replace(
            hour=self.config.DAILY_END_HOUR,
            minute=self.config.DAILY_END_MINUTE,
            second=self.config.DAILY_END_SECOND,
            microsecond=999999
        )
        
        return check_start, check_end 