"""
휴가 관리 모듈
"""
import os
import datetime
from typing import Dict, List, Set, Optional
from db import VacationManager
from db.migration import DataMigration
from logging_utils import get_logger

logger = get_logger()

class VacationService:
    """휴가 관리 서비스"""
    
    def __init__(self, config, time_util, vacation_manager=None):
        self.config = config
        self.time_util = time_util
        
        # ConfigManager에서 vacation_manager를 전달받음
        if vacation_manager:
            self.vacation_manager = vacation_manager
            self.db_manager = vacation_manager.db_manager
        else:
            raise ValueError("vacation_manager가 필요합니다. ConfigManager에서 전달받아야 합니다.")
        
        # 하위 호환성을 위한 기존 JSON 지원
        self.vacations_file = "vacations.json"
        self._migrate_from_json_if_needed()
    
    def _migrate_from_json_if_needed(self):
        """기존 JSON 파일이 존재하면 데이터베이스로 마이그레이션"""
        try:
            if os.path.exists(self.vacations_file):
                logger.info(f"기존 {self.vacations_file} 파일을 발견했습니다. 데이터베이스로 마이그레이션을 시도합니다.")
                migration = DataMigration(self.db_manager)
                if migration.migrate_vacations_from_json(self.vacations_file):
                    # 마이그레이션 성공 시 백업 생성
                    migration.backup_original_files("holidays.csv", self.vacations_file)
                    logger.info("휴가 데이터 마이그레이션이 완료되었습니다.")
        except Exception as e:
            logger.error(f"휴가 마이그레이션 중 오류: {e}", exc_info=True)
    
    
    def register_vacation(self, user_id: int, date_str: Optional[str] = None) -> str:
        """
        사용자의 휴가를 등록합니다.
        
        Args:
            user_id: 사용자 ID
            date_str: 휴가 날짜 (YYYY-MM-DD 형식, None인 경우 오늘)
            
        Returns:
            등록 결과 메시지
        """
        try:
            # 날짜가 지정되지 않은 경우 오늘 날짜 사용
            if date_str is None:
                target_date = self.time_util.now().date()
                date_str = target_date.strftime('%Y-%m-%d')
            else:
                # 날짜 형식 검증
                try:
                    parts = date_str.split('-')
                    if len(parts) != 3:
                        return "날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요."
                    
                    year, month, day = map(int, parts)
                    target_date = datetime.date(year, month, day)
                    
                    # 과거 날짜 검증
                    if target_date < self.time_util.now().date():
                        return "과거 날짜는 휴가로 등록할 수 없습니다."
                    
                except ValueError:
                    return "날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요."
            
            # 사용자 ID를 문자열로 변환
            user_id_str = str(user_id)
            
            # 이미 등록된 날짜인지 확인
            if self.vacation_manager.is_user_on_vacation(user_id_str, target_date):
                return f"{date_str} 날짜는 이미 휴가로 등록되어 있습니다."
            
            # 휴가 등록
            if self.vacation_manager.add_vacation(user_id_str, date_str):
                return f"{date_str} 날짜가 휴가로 등록되었습니다."
            else:
                return f"{date_str} 날짜 휴가 등록에 실패했습니다."
            
        except Exception as e:
            logger.error(f"휴가 등록 중 오류: {e}", exc_info=True)
            return "휴가 등록 중 오류가 발생했습니다. 나중에 다시 시도하거나 관리자에게 문의하세요."
    
    def cancel_all_vacations(self, user_id: int) -> str:
        """
        사용자의 모든 휴가를 취소합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            취소 결과 메시지
        """
        try:
            user_id_str = str(user_id)
            
            # 현재 등록된 휴가 수 확인
            vacation_dates = self.vacation_manager.get_user_vacations(user_id_str)
            if not vacation_dates:
                return "등록된 휴가가 없습니다."
            
            # 모든 휴가 취소
            vacation_count = self.vacation_manager.remove_all_vacations(user_id_str)
            
            if vacation_count > 0:
                return f"모든 휴가({vacation_count}개)가 취소되었습니다."
            else:
                return "등록된 휴가가 없습니다."
            
        except Exception as e:
            logger.error(f"휴가 취소 중 오류: {e}", exc_info=True)
            return "휴가 취소 중 오류가 발생했습니다. 나중에 다시 시도하거나 관리자에게 문의하세요."
    
    def get_user_vacations(self, user_id: int) -> List[str]:
        """
        사용자의 등록된 휴가 목록을 반환합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            휴가 날짜 목록 (정렬됨)
        """
        user_id_str = str(user_id)
        vacation_dates = self.vacation_manager.get_user_vacations(user_id_str)
        return sorted(list(vacation_dates))
    
    def is_user_on_vacation(self, user_id: int, date: Optional[datetime.date] = None) -> bool:
        """
        지정된 날짜에 사용자가 휴가인지 확인합니다.
        
        Args:
            user_id: 사용자 ID
            date: 확인할 날짜 (None인 경우 오늘)
            
        Returns:
            휴가 여부
        """
        if date is None:
            date = self.time_util.now().date()
        
        user_id_str = str(user_id)
        return self.vacation_manager.is_user_on_vacation(user_id_str, date) 