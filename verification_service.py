"""
인증 관련 서비스 모듈
"""
import logging
import discord
import datetime
from typing import List, Set, Tuple, Dict, Any, Optional

logger = logging.getLogger('verification_bot')

class VerificationService:
    """인증 관련 서비스 클래스"""
    
    def __init__(self, config, bot, message_util, time_util, webhook_service):
        self.config = config
        self.bot = bot
        self.message_util = message_util
        self.time_util = time_util
        self.webhook_service = webhook_service
        self._logger = logging.getLogger('verification_bot')
    
    # --- 인증 데이터 처리 관련 메서드 ---
    
    def _get_vacation_users_for_date(self, check_date: datetime.date) -> Set[int]:
        """특정 날짜에 휴가 중인 사용자 ID 목록 반환"""
        vacation_users = set()
        
        for user_id, (start_date, end_date) in self.bot.vacation_users.items():
            if start_date <= check_date <= end_date:
                vacation_users.add(user_id)
                self._logger.info(f"User {user_id} is on vacation from {start_date} to {end_date}")
                
        return vacation_users
    
    async def _get_verified_users(
        self, 
        channel: discord.TextChannel,
        start_time: datetime.datetime,
        end_time: datetime.datetime
    ) -> Set[int]:
        """지정된 기간 내에 인증한 사용자 ID 목록 반환"""
        verified_users = set()
        
        try:
            async for message in channel.history(
                after=start_time,
                before=end_time,
                limit=self.config.MESSAGE_HISTORY_LIMIT
            ):
                if (self.message_util.is_verification_message(message.content) and 
                    any(self.message_util.is_valid_image(attachment) for attachment in message.attachments)):
                    verified_users.add(message.author.id)
        except discord.HTTPException as e:
            self._logger.error(f"메시지 히스토리 조회 중 오류: {e}")
            
        return verified_users
    
    async def _get_unverified_members(
        self,
        channel: discord.TextChannel,
        verified_ids: Set[int],
        vacation_ids: Set[int]
    ) -> List[discord.Member]:
        """인증하지 않은 멤버 목록 반환 (휴가 사용자 제외)"""
        unverified_members = []
        
        try:
            async for member in channel.guild.fetch_members():
                if not member.bot and member.id not in verified_ids and member.id not in vacation_ids:
                    unverified_members.append(member)
        except discord.HTTPException as e:
            self._logger.error(f"멤버 목록 조회 중 오류: {e}")
            
        return unverified_members
    
    async def get_verification_data(
        self,
        channel: discord.TextChannel,
        start_time,
        end_time
    ) -> Tuple[Set[int], List[discord.Member]]:
        """인증 데이터 가져오기"""
        # 체크 날짜 기준 (자정 기준)
        check_date = end_time.date()
        
        # 1. 휴가 중인 사용자 필터링
        vacation_users = self._get_vacation_users_for_date(check_date)
        
        # 2. 인증한 사용자 확인
        verified_users = await self._get_verified_users(channel, start_time, end_time)
        
        # 3. 인증하지 않은 멤버 확인 (휴가 사용자 제외)
        unverified_members = await self._get_unverified_members(channel, verified_users, vacation_users)
            
        return verified_users, unverified_members
    
    # --- 인증 메시지 처리 관련 메서드 ---
    
    def _extract_image_urls(self, message: discord.Message) -> List[str]:
        """메시지에서 유효한 이미지 URL 추출"""
        image_urls = []
        for attachment in message.attachments:
            if self.message_util.is_valid_image(attachment):
                image_urls.append(attachment.url)
        return image_urls
    
    def _prepare_webhook_data(self, message: discord.Message, image_urls: List[str]) -> Dict[str, Any]:
        """웹훅 데이터 준비"""
        return {
            "author": message.author.name,
            "content": message.content,
            "image_urls": image_urls,
            "sent_at": self.time_util.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    async def _add_verification_reaction(self, message: discord.Message) -> None:
        """인증 메시지에 반응 추가"""
        try:
            if message.guild and message.channel.permissions_for(message.guild.me).add_reactions:
                await message.add_reaction('✅')
        except Exception as e:
            self._logger.warning(f"인증 반응 추가 중 오류: {e}")
    
    async def process_verification_message(self, message: discord.Message) -> None:
        """인증 메시지 처리"""
        try:
            # 1. 반응 추가
            await self._add_verification_reaction(message)

            # 2. 이미지 URL 추출
            image_urls = self._extract_image_urls(message)
            
            # 3. 이미지 유효성 검사
            if not image_urls:
                await message.channel.send(self.config.MESSAGES['attach_image_request'])
                return

            # 4. 웹훅 데이터 준비
            webhook_data = self._prepare_webhook_data(message, image_urls)

            # 5. 웹훅 전송 및 응답
            if await self.webhook_service.send_webhook(webhook_data):
                await message.channel.send(
                    self.config.MESSAGES['verification_success'].format(name=message.author.name)
                )
            else:
                await message.channel.send(self.config.MESSAGES['verification_error'])
                
        except discord.Forbidden:
            await message.channel.send(self.config.MESSAGES['bot_permission_error'])
        except Exception as e:
            self._logger.error(f"인증 처리 중 오류: {e}", exc_info=True)
            await message.channel.send("인증 처리 중 오류가 발생했습니다.")
    
    # --- 인증 체크 관련 메서드 ---
    
    def _check_channel_and_permissions(self, channel_id: int) -> Optional[discord.TextChannel]:
        """채널 및 권한 확인"""
        channel = self.bot.get_channel(channel_id)
        
        # 채널 확인
        if not channel or not isinstance(channel, discord.TextChannel):
            self._logger.error(f"Channel check failed: {channel_id}")
            return None
            
        # 권한 확인
        permissions = channel.permissions_for(channel.guild.me)
        if not all([permissions.read_message_history, permissions.view_channel, permissions.send_messages]):
            self._logger.error("Missing required permissions")
            return None
            
        return channel
    
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
                self._logger.info("모든 멤버 인증 완료 메시지 전송")
            except discord.HTTPException as e:
                self._logger.error(f"메시지 전송 중 오류: {e}")
            return
            
        # 멘션 청크 생성
        mention_chunks = self.message_util.chunk_mentions(unverified_members)
        
        # 각 청크별로 메시지 전송
        for chunk in mention_chunks:
            try:
                await channel.send(message_template.format(members=chunk))
            except discord.HTTPException as e:
                self._logger.error(f"메시지 전송 중 오류: {e}")
    
    async def check_daily_verification(self):
        """일일 인증 체크"""
        try:
            current_time = self.time_util.now()
            
            # 1. 체크 스킵 여부 확인
            if self._should_skip_daily_check(current_time):
                return
                
            self._logger.info(f"Starting daily verification check (KST): {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

            # 2. 채널 및 권한 확인
            channel = self._check_channel_and_permissions(self.config.VERIFICATION_CHANNEL_ID)
            if not channel:
                return
                
            self._logger.info(f"Channel check successful: {channel.name}")

            # 3. 날짜 범위 설정
            today_start, today_end = self.time_util.get_today_range()

            # 4. 인증 데이터 가져오기
            verified_users, unverified_members = await self.get_verification_data(
                channel, today_start, today_end
            )

            # 5. 미인증 멤버 메시지 전송
            await self.send_unverified_messages(
                channel, unverified_members, self.config.MESSAGES['unverified_daily']
            )

            # 6. 처리 결과 로깅
            self._logger.info(f"Number of unverified members: {len(unverified_members)}")
            self._logger.info("Daily verification check completed")

        except Exception as e:
            self._logger.error(f"Error during verification check: {str(e)}", exc_info=True)
        finally:
            if 'verified_users' in locals():
                verified_users.clear()
    
    def _should_skip_daily_check(self, current_time: datetime.datetime) -> bool:
        """일일 체크를 건너뛰어야 하는지 확인"""
        current_date = current_time.date()
        
        # 주말이나 공휴일인 경우 체크 건너뛰기
        if self.time_util.should_skip_check(current_time):
            reason = "weekend" if self.time_util.is_weekend(current_time.weekday()) else "holiday"
            self._logger.info(f"Skipping daily check - it's a {reason} ({current_date})")
            return True
            
        return False
    
    def _get_yesterday_check_date(self, current_time: datetime.datetime) -> Optional[datetime.datetime]:
        """전일 체크 대상 날짜 계산"""
        current_weekday = current_time.weekday()
        
        # 월요일이면 금요일 체크
        if current_weekday == 0:
            check_date = current_time - datetime.timedelta(days=3)
            self._logger.info(f"Monday: Checking Friday's verification")
        else:
            check_date = current_time - datetime.timedelta(days=1)
            
        # 체크하는 날짜가 주말이나 공휴일인 경우 체크 건너뛰기
        if self.time_util.should_skip_check(check_date):
            reason = "weekend" if self.time_util.is_weekend(check_date.weekday()) else "holiday"
            self._logger.info(f"Skipping yesterday check - the target date is a {reason} ({check_date.date()})")
            return None
            
        return check_date
    
    async def check_yesterday_verification(self):
        """전일 인증 체크"""
        try:
            current_time = self.time_util.now()
            current_weekday = current_time.weekday()
            
            # 1. 오늘이 주말이나 공휴일인 경우 체크 건너뛰기
            if self.time_util.should_skip_check(current_time):
                reason = "weekend" if self.time_util.is_weekend(current_time.weekday()) else "holiday"
                self._logger.info(f"Skipping yesterday check - today is a {reason} ({current_time.date()})")
                return
            
            # 2. 체크 대상 날짜 계산
            check_date = self._get_yesterday_check_date(current_time)
            if not check_date:
                return
                
            self._logger.info(f"Starting verification check for {check_date.strftime('%Y-%m-%d')} (KST)")

            # 3. 채널 확인
            channel = self._check_channel_and_permissions(self.config.VERIFICATION_CHANNEL_ID)
            if not channel:
                return

            # 4. 날짜 범위 설정
            check_start, check_end = self.time_util.get_check_date_range(check_date)

            # 5. 인증 데이터 가져오기
            verified_users, unverified_members = await self.get_verification_data(
                channel, check_start, check_end
            )

            # 6. 미인증 멤버 메시지 전송
            message_template = (
                self.config.MESSAGES['unverified_friday'] if current_weekday == 0
                else self.config.MESSAGES['unverified_yesterday']
            )
            await self.send_unverified_messages(
                channel, unverified_members, message_template
            )

            # 7. 처리 결과 로깅
            self._logger.info(f"Number of unverified members from previous day: {len(unverified_members)}")
            self._logger.info("Previous day verification check completed")

        except Exception as e:
            self._logger.error(f"Error during previous day verification check: {str(e)}", exc_info=True)
        finally:
            if 'verified_users' in locals():
                verified_users.clear() 
    
    # --- 휴가 처리 관련 메서드 ---
    
    def _merge_vacation_dates(
        self, 
        user_id: int, 
        new_start: datetime.date, 
        new_end: datetime.date
    ) -> Tuple[datetime.date, datetime.date, bool]:
        """기존 휴가와 새 휴가 날짜 병합"""
        existing_vacation = False
        
        if user_id in self.bot.vacation_users:
            old_start, old_end = self.bot.vacation_users[user_id]
            existing_vacation = True
            
            # 시작일은 더 이른 날짜로 설정
            start_date = min(old_start, new_start)
            
            # 종료일은 더 늦은 날짜로 설정
            end_date = max(old_end, new_end)
        else:
            start_date = new_start
            end_date = new_end
            
        return start_date, end_date, existing_vacation
    
    async def _add_vacation_reaction(self, message: discord.Message) -> None:
        """휴가 메시지에 이모지 반응 추가"""
        try:
            if isinstance(message.guild, discord.Guild):
                permissions = message.channel.permissions_for(message.guild.me)
                if permissions.add_reactions:
                    await message.add_reaction('✈️')
        except Exception as e:
            self._logger.warning(f"이모지 추가 중 오류: {e}")
    
    async def process_vacation_request(self, message: discord.Message) -> None:
        """휴가 요청 처리"""
        try:
            # 1. 휴가 날짜 파싱
            vacation_dates = self.message_util.parse_vacation_date(message.content)
            if not vacation_dates:
                await message.channel.send("❌ 휴가 형식이 올바르지 않습니다. `휴가 YYYY-MM-DD` 또는 `휴가 YYYY-MM-DD ~ YYYY-MM-DD` 형식으로 입력해주세요.")
                return
            
            start_date, end_date = vacation_dates
            
            # 2. 기존 휴가와 병합
            start_date, end_date, existing_vacation = self._merge_vacation_dates(
                message.author.id, start_date, end_date
            )
            
            # 3. 휴가 정보 등록
            self.bot.vacation_users[message.author.id] = (start_date, end_date)
            
            # 4. 확인 메시지 생성
            if existing_vacation:
                vacation_msg = f"✅ {message.author.mention}님의 휴가가 {start_date} ~ {end_date}로 업데이트되었습니다."
            elif start_date == end_date:
                vacation_msg = f"✅ {message.author.mention}님의 {start_date} 휴가가 등록되었습니다."
            else:
                vacation_msg = f"✅ {message.author.mention}님의 {start_date} ~ {end_date} 휴가가 등록되었습니다."
            
            # 5. 확인 메시지 전송
            await message.channel.send(vacation_msg)
            
            # 6. 반응 추가
            await self._add_vacation_reaction(message)
                
        except Exception as e:
            self._logger.error(f"휴가 처리 중 오류: {e}", exc_info=True)
            await message.channel.send("❌ 휴가 등록 중 오류가 발생했습니다. 다시 시도해주세요.") 