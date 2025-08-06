"""
로깅 유틸리티 모듈
"""
import logging
import sys
from pathlib import Path

# 전역 로거 인스턴스
_logger = None

def configure_logging(level='INFO', format_string=None, log_file=None):
    """
    로깅 설정을 초기화합니다.
    
    Args:
        level (str): 로깅 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string (str): 로그 포맷 문자열
        log_file (str): 로그 파일 경로 (None이면 콘솔만 출력)
    """
    global _logger
    
    if _logger is not None:
        return _logger
    
    # 로거 생성
    _logger = logging.getLogger('discord_bot')
    _logger.setLevel(getattr(logging, level.upper()))
    
    # 기존 핸들러 제거
    for handler in _logger.handlers[:]:
        _logger.removeHandler(handler)
    
    # 포맷터 설정
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(format_string)
    
    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    _logger.addHandler(console_handler)
    
    # 파일 핸들러 추가 (지정된 경우)
    if log_file:
        # 로그 디렉토리 생성
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        _logger.addHandler(file_handler)
    
    # discord.py 로거 비활성화 (중복 방지)
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    logging.getLogger('discord.gateway').setLevel(logging.WARNING)
    
    return _logger

def get_logger():
    """
    설정된 로거를 반환합니다.
    
    Returns:
        logging.Logger: 설정된 로거 인스턴스
        
    Raises:
        RuntimeError: 로거가 초기화되지 않은 경우
    """
    if _logger is None:
        raise RuntimeError("로거가 초기화되지 않았습니다. configure_logging()을 먼저 호출하세요.")
    return _logger 