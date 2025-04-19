"""
휴가 관리 모듈
"""
import os
import json
import datetime
import logging
from typing import Dict, List, Set, Optional

logger = logging.getLogger('verification_bot')

class VacationService:
    """휴가 관리 서비스"""
    
    def __init__(self, config, time_util):
        self.config = config
        self.time_util = time_util
        self.vacations: Dict[str, Set[str]] = {}  # {user_id: {date1, date2, ...}}
        self.vacations_file = "vacations.json"
        self._load_vacations()
    
    def _load_vacations(self):
        """저장된 휴가 정보를 로드합니다"""
        try:
            if os.path.exists(self.vacations_file):
                with open(self.vacations_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # JSON에서는 set을 직접 저장할 수 없으므로 변환 필요
                    self.vacations = {user_id: set(dates) for user_id, dates in data.items()}
                logger.info(f"{len(self.vacations)} 명의 사용자 휴가 정보를 로드했습니다.")
            else:
                logger.info("휴가 정보 파일이 없습니다. 새로 생성합니다.")
                self.vacations = {}
        except Exception as e:
            logger.error(f"휴가 정보 로드 중 오류: {e}", exc_info=True)
            self.vacations = {}
    
    def _save_vacations(self):
        """휴가 정보를 저장합니다"""
        try:
            # set을 list로 변환하여 저장
            data = {user_id: list(dates) for user_id, dates in self.vacations.items()}
            with open(self.vacations_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"휴가 정보가 {self.vacations_file}에 저장되었습니다.")
        except Exception as e:
            logger.error(f"휴가 정보 저장 중 오류: {e}", exc_info=True)
    
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
            
            # 해당 사용자의 휴가 목록이 없으면 생성
            if user_id_str not in self.vacations:
                self.vacations[user_id_str] = set()
            
            # 이미 등록된 날짜인지 확인
            if date_str in self.vacations[user_id_str]:
                return f"{date_str} 날짜는 이미 휴가로 등록되어 있습니다."
            
            # 휴가 등록
            self.vacations[user_id_str].add(date_str)
            
            # 변경 사항 저장
            self._save_vacations()
            
            return f"{date_str} 날짜가 휴가로 등록되었습니다."
            
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
            
            # 사용자의 휴가 정보가 없는 경우
            if user_id_str not in self.vacations or not self.vacations[user_id_str]:
                return "등록된 휴가가 없습니다."
            
            # 휴가 수 기록
            vacation_count = len(self.vacations[user_id_str])
            
            # 휴가 취소
            self.vacations[user_id_str] = set()
            
            # 변경 사항 저장
            self._save_vacations()
            
            return f"모든 휴가({vacation_count}개)가 취소되었습니다."
            
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
        if user_id_str not in self.vacations:
            return []
        
        # 날짜순으로 정렬하여 반환
        return sorted(list(self.vacations[user_id_str]))
    
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
        
        date_str = date.strftime('%Y-%m-%d')
        user_id_str = str(user_id)
        
        return user_id_str in self.vacations and date_str in self.vacations[user_id_str] 