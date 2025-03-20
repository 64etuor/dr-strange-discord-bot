# 일일 인증 체크 태스크 설정
self.daily_check_task = tasks.loop(time=daily_check_time)(self.verification_service.check_daily_verification)
self.yesterday_check_task = tasks.loop(time=yesterday_check_time)(self.verification_service.check_yesterday_verification) 