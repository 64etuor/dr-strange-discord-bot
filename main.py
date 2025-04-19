"""
인증 봇 메인 실행 파일
"""
import logging
import logging.handlers
import os
from config_manager import ConfigManager
from bot import VerificationBot

# We'll get the logger but not configure it globally
logger = logging.getLogger('verification_bot')

def configure_logging(config):
    """설정에 따라 로깅 구성"""
    log_level = getattr(logging, config.LOGGING_LEVEL)
    log_format = config.LOGGING_FORMAT
    log_file = config.LOGGING_FILE
    
    # 기존 핸들러 제거
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 로그 레벨 설정
    logger.setLevel(log_level)
    
    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(console_handler)
    
    # 파일 로깅이 설정된 경우 파일 핸들러 추가
    if log_file:
        # 로그 디렉토리 생성
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(file_handler)
    
    logger.info(f"로깅 설정 완료: 레벨={config.LOGGING_LEVEL}, 파일={log_file or '없음'}")

def main():
    """메인 함수"""
    try:
        # 설정 로드
        config = ConfigManager()
        
        # 로깅 설정 적용
        configure_logging(config)
        
        # 봇 생성 및 실행
        bot = VerificationBot(config)
        bot.run()
    except Exception as e:
        logger.error(f"봇 실행 중 오류 발생: {e}", exc_info=True)

if __name__ == "__main__":
    main() 