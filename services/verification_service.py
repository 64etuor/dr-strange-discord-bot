"""
인증 관련 서비스 모듈
"""
import logging
import discord
import datetime
from typing import List, Set, Tuple

logger = logging.getLogger('verification_bot')

class VerificationService:
    """인증 관련 서비스 클래스"""
    
    def __init__(self, config, bot, message_util, time_util, webhook_service):
        self.config = config
        self.bot = bot
        self.message_util = message_util
        self.time_util = time_util
        self.webhook_service = webhook_service
    
    async def get_verification_data(
        self,
        channel: discord.TextChannel,
        start_time,
        end_time
    ) -> Tuple[Set[int], List[discord.Member]]:
        """인증 데이터 가져오기"""
        verified_users: Set[int] = set()
        unverified_members: List[discord.Member] = []
        
        try:
            # 메시지 히스토리에서 인증한 사용자 확인
            async for message in channel.history(
                after=start_time,
                before=end_time,
                limit=self.config.MESSAGE_HISTORY_LIMIT
            ):
                if (self.message_util.is_verification_message(message.content) and 
                    any(self.message_util.is_valid_image(attachment) for attachment in message.attachments)):
                    verified_users.add(message.author.id)
            
            # 인증하지 않은 멤버 확인
            async for member in channel.guild.fetch_members():
                if not member.bot and member.id not in verified_users:
                    unverified_members.append(member)
                    
        except discord.Forbidden:
            logger.error("Missing required permissions")
        except discord.HTTPException as e:
            logger.error(f"Error while fetching messages/members: {e}")
            
        return verified_users, unverified_members
    
    async def process_verification_message(self, message: discord.Message) -> None:
        """인증 메시지 처리"""
        try:
            # 반응 추가 (권한 체크 수정)
            if message.guild and message.channel.permissions_for(message.guild.me).add_reactions:
                await message.add_reaction('✅')

            # 이미지 URL 추출
            image_urls = []
            for attachment in message.attachments:
                if self.message_util.is_valid_image(attachment):
                    image_urls.append(attachment.url)
            
            if not image_urls:
                await message.channel.send(self.config.MESSAGES['attach_image_request'])
                return

            # 웹훅 데이터 준비
            webhook_data = {
                "author": message.author.name,
                "content": message.content,
                "image_urls": image_urls,
                "sent_at": self.time_util.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # 웹훅 전송
            if await self.webhook_service.send_webhook(webhook_data):
                await message.channel.send(
                    self.config.MESSAGES['verification_success'].format(name=message.author.name)
                )
            else:
                await message.channel.send(self.config.MESSAGES['verification_error'])
                
        except discord.Forbidden:
            await message.channel.send(self.config.MESSAGES['bot_permission_error'])
        except Exception as e:
            logger.error(f"인증 처리 중 오류: {e}", exc_info=True)
            await message.channel.send("인증 처리 중 오류가 발생했습니다.")
    
    async def send_unverified_messages(
        self,
        channel: discord.TextChannel,
        unverified_members: List[discord.Member],
        message_template: str
    ) -> None:
        """미인증 멤버 메시지 전송"""
        if not unverified_members:
            try:
                await channel.send(self.config.MESSAGES['all_verified'])
                logger.info("모든 멤버 인증 완료 메시지 전송")
            except discord.HTTPException as e:
                logger.error(f"메시지 전송 중 오류: {e}")
            return
            
        # 멘션 청크 생성
        mention_chunks = self.message_util.chunk_mentions(unverified_members)
        
        # 각 청크별로 메시지 전송
        for chunk in mention_chunks:
            try:
                await channel.send(message_template.format(members=chunk))
            except discord.HTTPException as e:
                logger.error(f"메시지 전송 중 오류: {e}")
    
    async def check_daily_verification(self):
        """일일 인증 체크"""
        try:
            current_time = self.time_util.now()
            current_date = current_time.date()
            
            # 주말이나 공휴일인 경우 체크 건너뛰기
            if self.time_util.should_skip_check(current_time):
                reason = "weekend" if self.time_util.is_weekend(current_time.weekday()) else "holiday"
                logger.info(f"Skipping daily check - it's a {reason} ({current_date})")
                return
                
            logger.info(f"Starting daily verification check (KST): {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

            # 채널 확인
            channel = self.bot.get_channel(self.config.VERIFICATION_CHANNEL_ID)
            if not channel or not isinstance(channel, discord.TextChannel):
                logger.error(f"Channel check failed: {self.config.VERIFICATION_CHANNEL_ID}")
                return

            logger.info(f"Channel check successful: {channel.name}")

            # 권한 확인
            permissions = channel.permissions_for(channel.guild.me)
            if not all([permissions.read_message_history, permissions.view_channel, permissions.send_messages]):
                logger.error("Missing required permissions")
                return

            # 날짜 범위 설정
            today_start, today_end = self.time_util.get_today_range()

            # 인증 데이터 가져오기
            verified_users, unverified_members = await self.get_verification_data(
                channel, today_start, today_end
            )

            # 미인증 멤버 메시지 전송
            await self.send_unverified_messages(
                channel, unverified_members, self.config.MESSAGES['unverified_daily']
            )

            # 처리 결과 로깅
            logger.info(f"Number of unverified members: {len(unverified_members)}")
            logger.info("Daily verification check completed")

        except Exception as e:
            logger.error(f"Error during verification check: {str(e)}", exc_info=True)
        finally:
            if 'verified_users' in locals():
                verified_users.clear()
    
    async def check_yesterday_verification(self):
        """전일 인증 체크"""
        try:
            current_time = self.time_util.now()
            current_weekday = current_time.weekday()
            
            # 오늘이 주말이나 공휴일인 경우 체크 건너뛰기
            if self.time_util.should_skip_check(current_time):
                reason = "weekend" if self.time_util.is_weekend(current_time.weekday()) else "holiday"
                logger.info(f"Skipping yesterday check - today is a {reason} ({current_time.date()})")
                return
            
            # 월요일이면 금요일 체크
            if current_weekday == 0:
                check_date = current_time - datetime.timedelta(days=3)
                logger.info(f"Monday: Checking Friday's verification")
            else:
                check_date = current_time - datetime.timedelta(days=1)
                
            # 체크하는 날짜가 주말이나 공휴일인 경우 체크 건너뛰기
            if self.time_util.should_skip_check(check_date):
                reason = "weekend" if self.time_util.is_weekend(check_date.weekday()) else "holiday"
                logger.info(f"Skipping yesterday check - the target date is a {reason} ({check_date.date()})")
                return
                
            logger.info(f"Starting verification check for {check_date.strftime('%Y-%m-%d')} (KST)")

            # 채널 확인
            channel = self.bot.get_channel(self.config.VERIFICATION_CHANNEL_ID)
            if not channel or not isinstance(channel, discord.TextChannel):
                logger.error(f"Channel check failed: {self.config.VERIFICATION_CHANNEL_ID}")
                return

            # 날짜 범위 설정
            check_start, check_end = self.time_util.get_check_date_range(check_date)

            # 인증 데이터 가져오기
            verified_users, unverified_members = await self.get_verification_data(
                channel, check_start, check_end
            )

            # 미인증 멤버 메시지 전송
            message_template = (
                self.config.MESSAGES['unverified_friday'] if current_weekday == 0
                else self.config.MESSAGES['unverified_yesterday']
            )
            await self.send_unverified_messages(
                channel, unverified_members, message_template
            )

            # 처리 결과 로깅
            logger.info(f"Number of unverified members from previous day: {len(unverified_members)}")
            logger.info("Previous day verification check completed")

        except Exception as e:
            logger.error(f"Error during previous day verification check: {str(e)}", exc_info=True)
        finally:
            if 'verified_users' in locals():
                verified_users.clear() 