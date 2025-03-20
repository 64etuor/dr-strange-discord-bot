"""
인증 봇 메인 실행 파일
"""
import logging
from bot.bot import VerificationBot

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('verification_bot')

def main():
    """메인 함수"""
    try:
        # 봇 생성 및 실행
        bot = VerificationBot()
        bot.run()
    except Exception as e:
        logger.error(f"봇 실행 중 오류 발생: {e}", exc_info=True)

if __name__ == "__main__":
    main()