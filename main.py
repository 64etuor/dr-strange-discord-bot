"""
인증 봇 메인 실행 파일
"""
from config_manager import ConfigManager
from bot import VerificationBot
from logging_utils import get_logger, configure_logging

# 로거 초기화
logger = configure_logging()

def main():
    """메인 함수"""
    try:
        # 설정 로드
        config = ConfigManager()
        
        # 봇 생성 및 실행
        bot = VerificationBot(config)
        bot.run()
    except Exception as e:
        logger.error(f"봇 실행 중 오류 발생: {e}", exc_info=True)

if __name__ == "__main__":
    main() 