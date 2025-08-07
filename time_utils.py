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
        
        # 오늘 날짜 기준으로 시작 시간 설정
        start_time = current_time.replace(
            hour=self.config.DAILY_START_HOUR,
            minute=self.config.DAILY_START_MINUTE,
            second=0,
            microsecond=0
        )
        
        # 종료 시간이 새벽인 경우 (예: 03시) - 다음날로 설정
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
    
    def get_verification_time_range_for_date(self, target_date):
        """
        특정 날짜의 인증 시간 범위 계산
        
        Args:
            target_date: 계산할 날짜 (datetime.date 또는 datetime.datetime)
            
        Returns:
            (start_time, end_time): 인증 시작/종료 시간
        """
        # target_date가 date 객체인 경우 datetime으로 변환
        if isinstance(target_date, datetime.date):
            target_date = datetime.datetime.combine(target_date, datetime.time.min)
        
        # 시작 시간 계산
        start_time = target_date.replace(
            hour=self.config.DAILY_START_HOUR,
            minute=self.config.DAILY_START_MINUTE,
            second=0,
            microsecond=0
        )
        
        # 종료 시간 계산 (새벽인 경우 다음날로)
        if self.config.DAILY_END_HOUR < 12:
            end_time = (target_date + datetime.timedelta(days=1)).replace(
                hour=self.config.DAILY_END_HOUR,
                minute=self.config.DAILY_END_MINUTE,
                second=self.config.DAILY_END_SECOND,
                microsecond=0
            )
        else:
            end_time = target_date.replace(
                hour=self.config.DAILY_END_HOUR,
                minute=self.config.DAILY_END_MINUTE,
                second=self.config.DAILY_END_SECOND,
                microsecond=0
            )
        
        return start_time, end_time
    
    def get_verification_time_range_for_current_period(self):
        """
        현재 인증 기간의 시간 범위 계산 (새벽 시간대 고려)
        
        Returns:
            (start_time, end_time): 현재 인증 기간의 시작/종료 시간
        """
        now = self.now()
        
        # 현재 시간이 자정을 넘었지만 설정 종료 시간 이전인 경우 (새벽)
        current_hour = now.hour
        if current_hour < self.config.DAILY_END_HOUR:
            # 전날로부터 시작
            start_time = (now - datetime.timedelta(days=1)).replace(
                hour=self.config.DAILY_START_HOUR,
                minute=self.config.DAILY_START_MINUTE,
                second=0,
                microsecond=0
            )
        else:
            # 오늘로부터 시작
            start_time = now.replace(
                hour=self.config.DAILY_START_HOUR,
                minute=self.config.DAILY_START_MINUTE,
                second=0,
                microsecond=0
            )
        
        # 종료 시간 계산
        if self.config.DAILY_END_HOUR < 12:
            end_time = (now + datetime.timedelta(days=1)).replace(
                hour=self.config.DAILY_END_HOUR,
                minute=self.config.DAILY_END_MINUTE,
                second=self.config.DAILY_END_SECOND,
                microsecond=0
            )
        else:
            end_time = now.replace(
                hour=self.config.DAILY_END_HOUR,
                minute=self.config.DAILY_END_MINUTE,
                second=self.config.DAILY_END_SECOND,
                microsecond=0
            )
        
        return start_time, end_time
    
    def format_verification_time_range(self):
        """
        인증 시간 범위를 읽기 쉬운 형식으로 반환
        
        Returns:
            str: "HH:MM ~ HH:MM" 형식의 문자열
        """
        start_str = f"{self.config.DAILY_START_HOUR:02d}:{self.config.DAILY_START_MINUTE:02d}"
        end_str = f"{self.config.DAILY_END_HOUR:02d}:{self.config.DAILY_END_MINUTE:02d}"
        return f"{start_str} ~ {end_str}" 