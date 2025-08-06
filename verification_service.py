"""
인증 관련 서비스 모듈
"""
import discord
import datetime
from typing import List, Set, Tuple
from db import VerificationManager
from logging_utils import get_logger

logger = get_logger()

class VerificationService:
    """인증 관련 서비스 클래스"""
    
    def __init__(self, config, bot, message_util, time_util, webhook_service=None, vacation_service=None, verification_manager=None):
        self.config = config
        self.bot = bot
        self.message_util = message_util
        self.time_util = time_util
        self.webhook_service = webhook_service  # 하위 호환성을 위해 유지
        self.vacation_service = vacation_service
        self._check_in_progress = False
        
        # ConfigManager에서 verification_manager를 전달받음
        if verification_manager:
            self.verification_manager = verification_manager
            self.db_manager = verification_manager.db_manager
        else:
            raise ValueError("verification_manager가 필요합니다. ConfigManager에서 전달받아야 합니다.")
    
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
            # 데이터베이스에서 인증한 사용자 확인
            verification_date = start_time.date()  # start_time에서 날짜 추출
            db_verified_users = self.verification_manager.get_verified_users_on_date(verification_date)
            verified_users = {int(user_id) for user_id in db_verified_users}  # str을 int로 변환
            
            # 메시지 히스토리도 추가로 확인 (백업용)
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
            # 처리 중임을 표시하는 반응 추가
            if message.guild and message.channel.permissions_for(message.guild.me).add_reactions:
                await message.add_reaction('⏳')  # 처리 중 표시

            # 이미지 URL 추출
            image_urls = []
            for attachment in message.attachments:
                if self.message_util.is_valid_image(attachment):
                    image_urls.append(attachment.url)
            
            # 이미지가 없는 경우
            if not image_urls:
                await message.clear_reactions()
                if message.guild and message.channel.permissions_for(message.guild.me).add_reactions:
                    await message.add_reaction('❌')  # 실패 표시
                
                embed = discord.Embed(
                    title="❌ 인증 실패",
                    description="이미지가 첨부되지 않았습니다",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="필요한 조건",
                    value="인증을 위해 이미지를 첨부해주세요",
                    inline=False
                )
                embed.set_footer(text="인증 이미지와 함께 다시 시도해주세요")
                
                await message.channel.send(
                    content=message.author.mention,
                    embed=embed
                )
                return

            # 현재 시간 (KST) 가져오기
            current_time = self.time_util.now()
            
            # 데이터베이스에 인증 기록 저장
            success = self.verification_manager.add_verification(
                user_id=str(message.author.id),
                username=message.author.name,
                message_content=message.content,
                image_urls=image_urls,
                verification_datetime=current_time
            )
            
            await message.clear_reactions()
            
            if success:
                # 성공 반응 추가
                if message.guild and message.channel.permissions_for(message.guild.me).add_reactions:
                    await message.add_reaction('✅')  # 성공 표시
                
                # 성공 메시지 전송
                embed = discord.Embed(
                    title="✅ 인증 성공",
                    description=self.config.MESSAGES['verification_success'].format(name=message.author.name),
                    color=discord.Color.green()
                )
                
                # 시간 정보 추가
                embed.add_field(
                    name="인증 시간",
                    value=current_time.strftime('%Y-%m-%d %H:%M:%S'),
                    inline=False
                )
                
                # 이미지 미리보기 (첫 번째 이미지만)
                if image_urls:
                    embed.set_thumbnail(url=image_urls[0])
                
                await message.channel.send(
                    content=message.author.mention,
                    embed=embed
                )
            else:
                # 실패 반응 추가
                if message.guild and message.channel.permissions_for(message.guild.me).add_reactions:
                    await message.add_reaction('❌')  # 실패 표시
                
                # 실패 메시지 전송
                embed = discord.Embed(
                    title="❌ 인증 처리 실패",
                    description=self.config.MESSAGES['verification_error'],
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="조치 방법",
                    value="잠시 후 다시 시도해보세요. 문제가 지속되면 관리자에게 문의하세요.",
                    inline=False
                )
                
                await message.channel.send(
                    content=message.author.mention,
                    embed=embed
                )
                
        except discord.Forbidden:
            logger.error("Missing permissions for message processing")
            try:
                await message.clear_reactions()
                embed = discord.Embed(
                    title="⚠️ 권한 오류",
                    description=self.config.MESSAGES['bot_permission_error'],
                    color=discord.Color.gold()
                )
                await message.channel.send(embed=embed)
            except:
                pass
        except Exception as e:
            logger.error(f"인증 처리 중 오류: {e}", exc_info=True)
            try:
                await message.clear_reactions()
                if message.guild and message.channel.permissions_for(message.guild.me).add_reactions:
                    await message.add_reaction('⚠️')  # 경고 표시
                
                embed = discord.Embed(
                    title="⚠️ 인증 처리 오류",
                    description="인증 처리 중 예상치 못한 오류가 발생했습니다.",
                    color=discord.Color.dark_orange()
                )
                embed.add_field(
                    name="조치 방법",
                    value="잠시 후 다시 시도하거나 관리자에게 문의하세요.",
                    inline=False
                )
                
                await message.channel.send(
                    content=message.author.mention,
                    embed=embed
                )
            except:
                # 최후의 에러 처리 - 로그만 남기고 무시
                pass
    
    async def send_unverified_messages(
        self,
        channel: discord.TextChannel,
        unverified_members: List[discord.Member],
        message_template: str
    ) -> None:
        """미인증 멤버 메시지 전송"""
        if not unverified_members:
            try:
                # 모든 멤버가 인증 완료한 경우
                embed = discord.Embed(
                    title="🎉 인증 완료",
                    description=self.config.MESSAGES['all_verified'],
                    color=discord.Color.green()
                )
                
                embed.set_footer(text=f"확인 시간: {self.time_util.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                await channel.send(embed=embed)
                logger.info("모든 멤버 인증 완료 메시지 전송")
                
                # # 웹훅 전송
                # if self.webhook_service and self.config.WEBHOOK_URL:
                #     webhook_data = {
                #         "content": "🎉 모든 멤버가 인증을 완료했습니다!",
                #         "embeds": [{
                #             "title": "🎉 인증 완료",
                #             "description": self.config.MESSAGES['all_verified'],
                #             "color": 0x00ff00,
                #             "footer": {"text": f"확인 시간: {self.time_util.now().strftime('%Y-%m-%d %H:%M:%S')}"}
                #         }]
                #     }
                #     await self.webhook_service.send_webhook(webhook_data)
                
            except discord.HTTPException as e:
                logger.error(f"메시지 전송 중 오류: {e}")
            return
        
        # 멘션 청크 생성
        mention_chunks = self.message_util.chunk_mentions(unverified_members)
        
        # 알림 타입 판단 (일일 or 전일)
        is_daily = "daily" in message_template.lower()
        
        # 웹훅 데이터 준비 (웹훅 서비스가 있는 경우)
        webhook_embeds = []
        
        # 각 청크별로 메시지 전송
        for i, chunk in enumerate(mention_chunks):
            try:
                embed = discord.Embed(
                    title="⚠️ 인증 미완료 알림",
                    description=message_template.format(members=chunk),
                    color=discord.Color.red() if not is_daily else discord.Color.gold()
                )
                
                # 남은 시간 표시 (일일 알림인 경우)
                if is_daily:
                    now = self.time_util.now()
                    
                    # 일일 종료 시간 계산 (공통 함수 사용)
                    _, end_time = self.time_util.get_verification_time_range_for_current_period()
                    
                    # 남은 시간 계산
                    time_left = end_time - now
                    hours, remainder = divmod(int(time_left.total_seconds()), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    
                    embed.add_field(
                        name="⏰ 남은 시간",
                        value=f"{hours}시간 {minutes}분 {seconds}초",
                        inline=False
                    )
                    
                    embed.add_field(
                        name="인증 마감 시간",
                        value=end_time.strftime('%Y-%m-%d %H:%M:%S'),
                        inline=False
                    )
                
                # 페이지 표시 (여러 청크가 있는 경우)
                if len(mention_chunks) > 1:
                    embed.set_footer(text=f"미인증 멤버 목록 {i+1}/{len(mention_chunks)} | {self.time_util.now().strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    embed.set_footer(text=f"확인 시간: {self.time_util.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                await channel.send(embed=embed)
                
                # 웹훅용 임베드 데이터 추가
                webhook_embeds.append({
                    "title": embed.title,
                    "description": embed.description,
                    "color": embed.color.value if embed.color else 0xff0000,
                    "fields": [{"name": field.name, "value": field.value, "inline": field.inline} for field in embed.fields],
                    "footer": {"text": embed.footer.text} if embed.footer else None
                })
                
            except discord.HTTPException as e:
                logger.error(f"메시지 전송 중 오류: {e}")
        
        # 웹훅으로도 전송 (웹훅 서비스가 있는 경우)
        if self.webhook_service and self.config.WEBHOOK_URL and webhook_embeds:
            webhook_data = {
                "content": f"⚠️ 인증 미완료 알림 ({len(unverified_members)}명)",
                "embeds": webhook_embeds
            }
            await self.webhook_service.send_webhook(webhook_data)
    
    async def check_daily_verification(self) -> None:
        """일일 인증 체크"""
        if self._check_in_progress:
            logger.warning("이미 인증 체크가 진행 중입니다.")
            return
            
        self._check_in_progress = True
        logger.info("일일 인증 체크 시작")
        
        try:
            # 허용된 채널 중 첫 번째를 인증 채널로 사용
            if not self.config.ALLOWED_CHANNELS:
                logger.error("허용된 채널이 설정되지 않았습니다.")
                return
                
            channel_id = self.config.ALLOWED_CHANNELS[0]
            channel = self.bot.get_channel(channel_id)
            
            if not channel:
                logger.error(f"인증 채널을 찾을 수 없습니다: {channel_id}")
                return
                
            # 현재 날짜가 체크를 건너뛰어야 하는 날짜인지 확인
            now = self.time_util.now()
            if self.time_util.should_skip_check(now):
                reason = "주말" if self.time_util.is_weekend(now.weekday()) else "공휴일"
                logger.info(f"일일 인증 체크 건너뜀 ({reason})")
                return
                
            # 체크 기간 계산
            start_time, end_time = self.time_util.get_today_range()
            
            # 인증 데이터 가져오기
            verified_users, unverified_members = await self.get_verification_data(channel, start_time, end_time)
            
            # 휴가 사용자 필터링 (휴가 서비스가 있는 경우)
            if self.vacation_service:
                filtered_members = []
                for member in unverified_members:
                    if not self.vacation_service.is_user_on_vacation(member.id):
                        filtered_members.append(member)
                
                if len(filtered_members) != len(unverified_members):
                    logger.info(f"{len(unverified_members) - len(filtered_members)}명이 휴가로 인해 인증 체크에서 제외됨")
                unverified_members = filtered_members
            
            # 결과 출력
            logger.info(f"인증 완료: {len(verified_users)}명, 미완료: {len(unverified_members)}명")
            
            # 인증되지 않은 멤버에게 메시지 전송
            await self.send_unverified_messages(
                channel,
                unverified_members,
                self.config.MESSAGES['daily_check']
            )
            
        except Exception as e:
            logger.error(f"일일 인증 체크 중 오류: {e}", exc_info=True)
        finally:
            self._check_in_progress = False
            logger.info("일일 인증 체크 완료")
            
    async def check_yesterday_verification(self) -> None:
        """어제 인증 체크"""
        try:
            # 허용된 채널 중 첫 번째를 인증 채널로 사용
            if not self.config.ALLOWED_CHANNELS:
                logger.error("허용된 채널이 설정되지 않았습니다.")
                return
                
            channel_id = self.config.ALLOWED_CHANNELS[0]
            channel = self.bot.get_channel(channel_id)
            
            if not channel:
                logger.error(f"인증 채널을 찾을 수 없습니다: {channel_id}")
                return
                
            # 어제가 체크를 건너뛰어야 하는 날짜인지 확인
            yesterday = self.time_util.now() - datetime.timedelta(days=1)
            if self.time_util.should_skip_check(yesterday):
                reason = "주말" if self.time_util.is_weekend(yesterday.weekday()) else "공휴일"
                logger.info(f"전일 인증 체크 건너뜀 ({reason})")
                return
                
            # 체크 기간 계산 (전일)
            start_time, end_time = self.time_util.get_check_date_range(yesterday)
            
            # 인증 데이터 가져오기
            verified_users, unverified_members = await self.get_verification_data(channel, start_time, end_time)
            
            # 휴가 사용자 필터링 (휴가 서비스가 있는 경우)
            if self.vacation_service:
                filtered_members = []
                for member in unverified_members:
                    if not self.vacation_service.is_user_on_vacation(member.id, yesterday.date()):
                        filtered_members.append(member)
                
                if len(filtered_members) != len(unverified_members):
                    logger.info(f"{len(unverified_members) - len(filtered_members)}명이 휴가로 인해 인증 체크에서 제외됨")
                unverified_members = filtered_members
            
            # 결과 출력
            logger.info(f"전일 인증 완료: {len(verified_users)}명, 미완료: {len(unverified_members)}명")
            
            # 인증되지 않은 멤버에게 메시지 전송
            await self.send_unverified_messages(
                channel,
                unverified_members,
                self.config.MESSAGES['yesterday_check']
            )
            
        except Exception as e:
            logger.error(f"전일 인증 체크 중 오류: {e}", exc_info=True)
        finally:
            self._check_in_progress = False
            logger.info("전일 인증 체크 완료") 