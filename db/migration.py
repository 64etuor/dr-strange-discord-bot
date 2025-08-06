"""
CSV/JSON 데이터를 SQLite로 마이그레이션하는 모듈
"""
import csv
import json
import os
import logging
from typing import Dict, Set
from .database import DatabaseManager, HolidayManager, VacationManager

logger = logging.getLogger('verification_bot')

class DataMigration:
    """데이터 마이그레이션 클래스"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.holiday_manager = HolidayManager(db_manager)
        self.vacation_manager = VacationManager(db_manager)
    
    def migrate_holidays_from_csv(self, csv_file: str = "holidays.csv") -> bool:
        """
        CSV 파일에서 공휴일 데이터를 SQLite로 마이그레이션
        
        Args:
            csv_file: CSV 파일 경로
            
        Returns:
            마이그레이션 성공 여부
        """
        if not os.path.exists(csv_file):
            logger.warning(f"공휴일 CSV 파일을 찾을 수 없음: {csv_file}")
            return False
        
        try:
            migrated_count = 0
            with open(csv_file, 'r', encoding='utf-8') as f:
                # BOM 제거
                content = f.read()
                if content.startswith('\ufeff'):
                    content = content[1:]
                
                # StringIO로 처리
                from io import StringIO
                csv_content = StringIO(content)
                reader = csv.DictReader(csv_content)
                
                for row in reader:
                    date_str = row.get('date', '').strip()
                    name = row.get('holiday name', '').strip()
                    
                    if date_str and name:
                        if self.holiday_manager.add_holiday(date_str, name):
                            migrated_count += 1
            
            logger.info(f"공휴일 CSV 마이그레이션 완료: {migrated_count}개")
            return True
            
        except Exception as e:
            logger.error(f"공휴일 CSV 마이그레이션 오류: {e}")
            return False
    
    def migrate_vacations_from_json(self, json_file: str = "vacations.json") -> bool:
        """
        JSON 파일에서 휴가 데이터를 SQLite로 마이그레이션
        
        Args:
            json_file: JSON 파일 경로
            
        Returns:
            마이그레이션 성공 여부
        """
        if not os.path.exists(json_file):
            logger.warning(f"휴가 JSON 파일을 찾을 수 없음: {json_file}")
            return False
        
        try:
            migrated_count = 0
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for user_id, dates in data.items():
                if isinstance(dates, list):
                    for date_str in dates:
                        if self.vacation_manager.add_vacation(str(user_id), date_str):
                            migrated_count += 1
                elif isinstance(dates, str):
                    # 단일 날짜인 경우
                    if self.vacation_manager.add_vacation(str(user_id), dates):
                        migrated_count += 1
            
            logger.info(f"휴가 JSON 마이그레이션 완료: {migrated_count}개")
            return True
            
        except Exception as e:
            logger.error(f"휴가 JSON 마이그레이션 오류: {e}")
            return False
    
    def migrate_all(self, holidays_csv: str = "holidays.csv", vacations_json: str = "vacations.json") -> Dict[str, bool]:
        """
        모든 데이터를 마이그레이션
        
        Args:
            holidays_csv: 공휴일 CSV 파일 경로
            vacations_json: 휴가 JSON 파일 경로
            
        Returns:
            마이그레이션 결과 {'holidays': bool, 'vacations': bool}
        """
        results = {
            'holidays': self.migrate_holidays_from_csv(holidays_csv),
            'vacations': self.migrate_vacations_from_json(vacations_json)
        }
        
        logger.info(f"데이터 마이그레이션 결과: {results}")
        return results
    
    def backup_original_files(self, holidays_csv: str = "holidays.csv", vacations_json: str = "vacations.json"):
        """
        원본 파일들을 백업
        
        Args:
            holidays_csv: 공휴일 CSV 파일 경로
            vacations_json: 휴가 JSON 파일 경로
        """
        import shutil
        from datetime import datetime
        
        backup_suffix = f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        for file_path in [holidays_csv, vacations_json]:
            if os.path.exists(file_path):
                backup_path = file_path + backup_suffix
                try:
                    shutil.copy2(file_path, backup_path)
                    logger.info(f"파일 백업 완료: {file_path} -> {backup_path}")
                except Exception as e:
                    logger.error(f"파일 백업 오류: {file_path} - {e}")


def run_migration():
    """마이그레이션 실행 함수"""
    db_manager = DatabaseManager()
    migration = DataMigration(db_manager)
    
    # 백업 생성
    migration.backup_original_files()
    
    # 마이그레이션 실행
    results = migration.migrate_all()
    
    if all(results.values()):
        print("✅ 모든 데이터 마이그레이션이 성공적으로 완료되었습니다.")
    else:
        print(f"⚠️ 마이그레이션 결과: {results}")
    
    return results

if __name__ == "__main__":
    run_migration()