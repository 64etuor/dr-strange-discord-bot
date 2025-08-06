"""
SQLite 데이터베이스 관리 모듈
"""
import sqlite3
import os
import logging
from contextlib import contextmanager
from typing import List, Dict, Optional, Set
import datetime

logger = logging.getLogger('verification_bot')

class DatabaseManager:
    """SQLite 데이터베이스 관리 클래스"""
    
    def __init__(self, db_path: str = "db/discord_bot.db"):
        """
        데이터베이스 매니저 초기화
        
        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
    
    def _ensure_db_directory(self):
        """데이터베이스 디렉토리가 존재하는지 확인하고 생성"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"데이터베이스 디렉토리 생성: {db_dir}")
    
    @contextmanager
    def get_connection(self):
        """데이터베이스 연결 컨텍스트 매니저"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"데이터베이스 오류: {e}")
            raise
        finally:
            conn.close()
    
    def _init_database(self):
        """데이터베이스 및 테이블 초기화"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 공휴일 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS holidays (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 휴가 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vacations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, date)
                )
            """)
            
            # 인증 기록 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS verifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    message_content TEXT,
                    image_urls TEXT,
                    verification_date TEXT NOT NULL,
                    verification_time TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 인덱스 생성
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_holidays_date ON holidays(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vacations_user_date ON vacations(user_id, date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vacations_date ON vacations(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_verifications_user_date ON verifications(user_id, verification_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_verifications_date ON verifications(verification_date)")
            
            conn.commit()
            logger.info("데이터베이스 초기화 완료")


class HolidayManager:
    """공휴일 관리 클래스"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def add_holiday(self, date: str, name: str) -> bool:
        """
        공휴일 추가
        
        Args:
            date: YYYY-MM-DD 형식의 날짜
            name: 공휴일 이름
            
        Returns:
            추가 성공 여부
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO holidays (date, name) VALUES (?, ?)",
                    (date, name)
                )
                conn.commit()
                logger.debug(f"공휴일 추가: {date} - {name}")
                return True
        except Exception as e:
            logger.error(f"공휴일 추가 오류: {e}")
            return False
    
    def remove_holiday(self, date: str) -> bool:
        """
        공휴일 제거
        
        Args:
            date: YYYY-MM-DD 형식의 날짜
            
        Returns:
            제거 성공 여부
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM holidays WHERE date = ?", (date,))
                conn.commit()
                logger.debug(f"공휴일 제거: {date}")
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"공휴일 제거 오류: {e}")
            return False
    
    def is_holiday(self, date: datetime.date) -> bool:
        """
        특정 날짜가 공휴일인지 확인
        
        Args:
            date: 확인할 날짜
            
        Returns:
            공휴일 여부
        """
        date_str = date.strftime('%Y-%m-%d')
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM holidays WHERE date = ?", (date_str,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"공휴일 확인 오류: {e}")
            return False
    
    def get_holidays(self, year: Optional[int] = None) -> List[Dict]:
        """
        공휴일 목록 조회
        
        Args:
            year: 특정 연도 (None이면 전체)
            
        Returns:
            공휴일 목록 [{'date': '2025-01-01', 'name': '신정'}, ...]
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                if year:
                    cursor.execute(
                        "SELECT date, name FROM holidays WHERE date LIKE ? ORDER BY date",
                        (f"{year}-%",)
                    )
                else:
                    cursor.execute("SELECT date, name FROM holidays ORDER BY date")
                
                return [{'date': row['date'], 'name': row['name']} for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"공휴일 목록 조회 오류: {e}")
            return []
    
    def get_holiday_count(self) -> int:
        """등록된 공휴일 총 개수 반환"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM holidays")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"공휴일 개수 조회 오류: {e}")
            return 0


class VacationManager:
    """휴가 관리 클래스"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def add_vacation(self, user_id: str, date: str) -> bool:
        """
        사용자 휴가 추가
        
        Args:
            user_id: 사용자 ID
            date: YYYY-MM-DD 형식의 날짜
            
        Returns:
            추가 성공 여부
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO vacations (user_id, date) VALUES (?, ?)",
                    (user_id, date)
                )
                conn.commit()
                if cursor.rowcount > 0:
                    logger.debug(f"휴가 추가: {user_id} - {date}")
                    return True
                return False  # 이미 존재하는 경우
        except Exception as e:
            logger.error(f"휴가 추가 오류: {e}")
            return False
    
    def remove_vacation(self, user_id: str, date: str) -> bool:
        """
        사용자 휴가 제거
        
        Args:
            user_id: 사용자 ID
            date: YYYY-MM-DD 형식의 날짜
            
        Returns:
            제거 성공 여부
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM vacations WHERE user_id = ? AND date = ?",
                    (user_id, date)
                )
                conn.commit()
                logger.debug(f"휴가 제거: {user_id} - {date}")
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"휴가 제거 오류: {e}")
            return False
    
    def remove_all_vacations(self, user_id: str) -> int:
        """
        사용자의 모든 휴가 제거
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            제거된 휴가 개수
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM vacations WHERE user_id = ?", (user_id,))
                conn.commit()
                removed_count = cursor.rowcount
                logger.debug(f"사용자 {user_id}의 모든 휴가 제거: {removed_count}개")
                return removed_count
        except Exception as e:
            logger.error(f"모든 휴가 제거 오류: {e}")
            return 0
    
    def is_user_on_vacation(self, user_id: str, date: Optional[datetime.date] = None) -> bool:
        """
        사용자가 특정 날짜에 휴가인지 확인
        
        Args:
            user_id: 사용자 ID
            date: 확인할 날짜 (None이면 오늘)
            
        Returns:
            휴가 여부
        """
        if date is None:
            date = datetime.date.today()
        
        date_str = date.strftime('%Y-%m-%d')
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM vacations WHERE user_id = ? AND date = ?",
                    (user_id, date_str)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"휴가 확인 오류: {e}")
            return False
    
    def get_user_vacations(self, user_id: str) -> Set[str]:
        """
        사용자의 모든 휴가 날짜 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            휴가 날짜 집합 {'2025-01-01', '2025-01-02', ...}
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT date FROM vacations WHERE user_id = ? ORDER BY date",
                    (user_id,)
                )
                return {row['date'] for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"사용자 휴가 조회 오류: {e}")
            return set()
    
    def get_all_vacations_by_date(self, date: datetime.date) -> Set[str]:
        """
        특정 날짜의 모든 휴가자 조회
        
        Args:
            date: 확인할 날짜
            
        Returns:
            휴가자 사용자 ID 집합
        """
        date_str = date.strftime('%Y-%m-%d')
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT user_id FROM vacations WHERE date = ?",
                    (date_str,)
                )
                return {row['user_id'] for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"날짜별 휴가자 조회 오류: {e}")
            return set()


class VerificationManager:
    """인증 기록 관리 클래스"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def add_verification(self, user_id: str, username: str, message_content: str, 
                        image_urls: List[str], verification_datetime: datetime.datetime) -> bool:
        """
        인증 기록 추가
        
        Args:
            user_id: 사용자 ID
            username: 사용자 이름
            message_content: 메시지 내용
            image_urls: 이미지 URL 목록
            verification_datetime: 인증 일시
            
        Returns:
            추가 성공 여부
        """
        try:
            verification_date = verification_datetime.strftime('%Y-%m-%d')
            verification_time = verification_datetime.strftime('%H:%M:%S')
            image_urls_json = ','.join(image_urls) if image_urls else ''
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO verifications 
                    (user_id, username, message_content, image_urls, verification_date, verification_time) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, username, message_content, image_urls_json, verification_date, verification_time))
                conn.commit()
                logger.info(f"인증 기록 저장: {username} ({user_id}) - {verification_date} {verification_time}")
                return True
        except Exception as e:
            logger.error(f"인증 기록 저장 오류: {e}")
            return False
    
    def get_verifications_by_date(self, date: datetime.date) -> List[Dict]:
        """
        특정 날짜의 모든 인증 기록 조회
        
        Args:
            date: 조회할 날짜
            
        Returns:
            인증 기록 목록
        """
        date_str = date.strftime('%Y-%m-%d')
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_id, username, message_content, image_urls, 
                           verification_date, verification_time, created_at
                    FROM verifications 
                    WHERE verification_date = ? 
                    ORDER BY verification_time
                """, (date_str,))
                
                results = []
                for row in cursor.fetchall():
                    image_urls = row['image_urls'].split(',') if row['image_urls'] else []
                    results.append({
                        'user_id': row['user_id'],
                        'username': row['username'],
                        'message_content': row['message_content'],
                        'image_urls': image_urls,
                        'verification_date': row['verification_date'],
                        'verification_time': row['verification_time'],
                        'created_at': row['created_at']
                    })
                return results
        except Exception as e:
            logger.error(f"날짜별 인증 기록 조회 오류: {e}")
            return []
    
    def get_user_verifications(self, user_id: str, start_date: Optional[datetime.date] = None, 
                             end_date: Optional[datetime.date] = None) -> List[Dict]:
        """
        사용자의 인증 기록 조회
        
        Args:
            user_id: 사용자 ID
            start_date: 시작 날짜 (None이면 제한 없음)
            end_date: 종료 날짜 (None이면 제한 없음)
            
        Returns:
            인증 기록 목록
        """
        try:
            query = """
                SELECT user_id, username, message_content, image_urls, 
                       verification_date, verification_time, created_at
                FROM verifications 
                WHERE user_id = ?
            """
            params = [user_id]
            
            if start_date:
                query += " AND verification_date >= ?"
                params.append(start_date.strftime('%Y-%m-%d'))
            
            if end_date:
                query += " AND verification_date <= ?"
                params.append(end_date.strftime('%Y-%m-%d'))
            
            query += " ORDER BY verification_date DESC, verification_time DESC"
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                results = []
                for row in cursor.fetchall():
                    image_urls = row['image_urls'].split(',') if row['image_urls'] else []
                    results.append({
                        'user_id': row['user_id'],
                        'username': row['username'],
                        'message_content': row['message_content'],
                        'image_urls': image_urls,
                        'verification_date': row['verification_date'],
                        'verification_time': row['verification_time'],
                        'created_at': row['created_at']
                    })
                return results
        except Exception as e:
            logger.error(f"사용자 인증 기록 조회 오류: {e}")
            return []
    
    def has_user_verified_on_date(self, user_id: str, date: datetime.date) -> bool:
        """
        사용자가 특정 날짜에 인증했는지 확인
        
        Args:
            user_id: 사용자 ID
            date: 확인할 날짜
            
        Returns:
            인증 여부
        """
        date_str = date.strftime('%Y-%m-%d')
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM verifications WHERE user_id = ? AND verification_date = ?",
                    (user_id, date_str)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"인증 확인 오류: {e}")
            return False
    
    def get_verified_users_on_date(self, date: datetime.date) -> Set[str]:
        """
        특정 날짜에 인증한 모든 사용자 ID 조회
        
        Args:
            date: 확인할 날짜
            
        Returns:
            인증한 사용자 ID 집합
        """
        date_str = date.strftime('%Y-%m-%d')
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT DISTINCT user_id FROM verifications WHERE verification_date = ?",
                    (date_str,)
                )
                return {row['user_id'] for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"날짜별 인증 사용자 조회 오류: {e}")
            return set()