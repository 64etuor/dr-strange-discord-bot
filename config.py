from datetime import time
import pytz

class Config:
    # 인증 관련 설정
    VERIFICATION_KEYWORDS = ["인증사진", "인증 사진"]
    MAX_MESSAGE_LENGTH = 1900
    MAX_ATTACHMENT_SIZE = 9 * 1024 * 1024
    MESSAGE_HISTORY_LIMIT = 1000
    MAX_RETRY_ATTEMPTS = 3
    WEBHOOK_TIMEOUT = 10

    # 시간 설정 (KST 기준)
    class Time:
        TIMEZONE = pytz.timezone('Asia/Seoul')
        
        # 일일 체크 시간
        DAILY_CHECK_HOUR = 22
        DAILY_CHECK_MINUTE = 0
        
        # 전일 체크 시간
        YESTERDAY_CHECK_HOUR = 9
        YESTERDAY_CHECK_MINUTE = 0
        
        # 인증 시간 범위
        DAILY_START_HOUR = 0
        DAILY_START_MINUTE = 0
        DAILY_END_HOUR = 23
        DAILY_END_MINUTE = 59
        DAILY_END_SECOND = 59

        @classmethod
        def get_utc_hour(cls, kst_hour):
            return (kst_hour - 9) % 24
class Messages:
    # 인증 관련 메시지
    VERIFICATION_SUCCESS = "{author}, Your time has been recorded. The bill comes due. Always!"
    VERIFICATION_ERROR = "Verification Error occured. Please try again."
    ATTACH_IMAGE_REQUEST = "Please attach an image."

    # 미인증 알림 메시지
    UNVERIFIED_FRIDAY = ("⚠️ 지난 주 금요일 인증을 하지 않은 멤버(들)입니다:\n{members}\n"
                        "벌칙을 수행해 주세요!")
    UNVERIFIED_DAILY = ("⚠️ 어제 인증을 하지 않은 멤버(들)입니다:\n{members}\n"
                       "벌칙을 수행해 주세요!")
    
    # 인증 완료 메시지
    ALL_VERIFIED_DAILY = ("🎉 모든 멤버가 인증을 완료했네요!\n"
                         "💪 여러분의 꾸준한 노력이 멋져요. 내일도 힘내세요! 💫")
    ALL_VERIFIED_YESTERDAY = ("🎉 어제는 모든 멤버가 인증을 완료했네요!\n"
                            "💪 여러분의 꾸준한 노력이 대단합니다. 오늘도 힘내세요! 💫")

    # 시간 정보 메시지
    TIME_INFO = ("🕒 Current time information:\n"
                "Server(Southeast Asia) time: {server_time}\n"
                "UTC time: {utc_time}\n"
                "KST time: {kst_time}")
