"""
웹훅 처리 서비스 모듈
"""
import aiohttp
import asyncio
import logging

logger = logging.getLogger('verification_bot')

class WebhookService:
    """웹훅 통신 서비스 클래스"""
    
    def __init__(self, config):
        self.config = config
        self.session = None
    
    async def initialize(self):
        """세션 초기화"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def cleanup(self):
        """리소스 정리"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def send_webhook(self, webhook_data: dict) -> bool:
        """웹훅 전송"""
        # 세션이 없으면 초기화
        await self.initialize()
        
        try:
            response = await self.session.post(
                self.config.WEBHOOK_URL, 
                json=webhook_data,
                timeout=self.config.WEBHOOK_TIMEOUT
            )
            
            # 응답 처리
            if response.status in [401, 403, 404]:
                logger.error(f"Webhook error: Status {response.status}")
                return False

            if response.status == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                logger.warning(f"Rate limited, retrying after {retry_after} seconds")
                await asyncio.sleep(retry_after)
                return await self.send_webhook(webhook_data)

            # 응답 내용 로깅 추가
            response_text = await response.text()
            if response.status != 200:
                logger.error(f"Webhook failed: Status {response.status}, Response: {response_text}")
                return False
            
            logger.info(f"Webhook sent successfully: Status {response.status}")
            return True
            
        except Exception as e:
            logger.error(f"Unexpected error during webhook request: {e}", exc_info=True)
            return False 