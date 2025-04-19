"""
봇 명령어 처리 모듈 (Discord 슬래시 명령어 활용)
"""
import datetime
import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger('verification_bot')

class VerificationCommands(commands.Cog):
    """인증 관련 명령어 Cog"""
    
    def __init__(self, bot, config, verification_service, task_manager, time_util):
        self.bot = bot
        self.config = config
        self.verification_service = verification_service
        self.task_manager = task_manager
        self.time_util = time_util
    
    @commands.Cog.listener()
    async def on_ready(self):
        """봇이 준비되었을 때 실행"""
        logger.info("VerificationCommands Cog loaded")
    
    @app_commands.command(name="hello", description="인사 테스트")
    async def hello(self, interaction: discord.Interaction):
        """인사 명령어"""
        await interaction.response.send_message('안녕하세요! 인증 봇입니다. 👋', ephemeral=True)
    
    @app_commands.command(name="verify_status", description="내 인증 상태 확인")
    async def verify_status(self, interaction: discord.Interaction):
        """사용자의 현재 인증 상태를 확인합니다"""
        # 응답 지연 설정 (데이터 조회에 시간이 걸릴 수 있음)
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            # 채널 가져오기
            channel = self.bot.get_channel(self.config.VERIFICATION_CHANNEL_ID)
            if not channel:
                await interaction.followup.send(
                    "인증 채널을 찾을 수 없습니다. 관리자에게 문의하세요.",
                    ephemeral=True
                )
                return
                
            # 오늘 날짜 범위 계산
            today_start, today_end = self.time_util.get_today_range()
            
            # 어제 날짜 범위 계산
            yesterday = self.time_util.now() - datetime.timedelta(days=1)
            yesterday_start, yesterday_end = self.time_util.get_check_date_range(yesterday)
            
            # 검색할 사용자 ID
            user_id = interaction.user.id
            is_verified_today = False
            is_verified_yesterday = False
            verification_time_today = None
            verification_time_yesterday = None
            
            # 오늘 인증 여부 확인
            async for message in channel.history(after=today_start, before=today_end, limit=self.config.MESSAGE_HISTORY_LIMIT):
                if (message.author.id == user_id and 
                    self.verification_service.message_util.is_verification_message(message.content) and 
                    any(self.verification_service.message_util.is_valid_image(attachment) for attachment in message.attachments)):
                    is_verified_today = True
                    verification_time_today = message.created_at
                    break
            
            # 어제 인증 여부 확인
            async for message in channel.history(after=yesterday_start, before=yesterday_end, limit=self.config.MESSAGE_HISTORY_LIMIT):
                if (message.author.id == user_id and 
                    self.verification_service.message_util.is_verification_message(message.content) and 
                    any(self.verification_service.message_util.is_valid_image(attachment) for attachment in message.attachments)):
                    is_verified_yesterday = True
                    verification_time_yesterday = message.created_at
                    break
            
            # 결과 표시할 임베드 생성
            embed = discord.Embed(
                title="🔍 인증 상태 확인",
                description=f"{interaction.user.mention}님의 인증 상태입니다.",
                color=discord.Color.blue()
            )
            
            # 오늘 인증 상태
            if is_verified_today:
                embed.add_field(
                    name="✅ 오늘 인증 완료",
                    value=f"인증 시간: {verification_time_today.strftime('%Y-%m-%d %H:%M:%S')}",
                    inline=False
                )
            else:
                # 인증 기간 중인지 확인
                now = self.time_util.now()
                today_date = now.date()
                
                # 인증 시간 범위 계산
                start_time = now.replace(
                    hour=self.config.DAILY_START_HOUR,
                    minute=self.config.DAILY_START_MINUTE,
                    second=0,
                    microsecond=0
                )
                
                # 종료 시간이 새벽인 경우 (다음날)
                if self.config.DAILY_END_HOUR < 12:
                    end_time = (now + datetime.timedelta(days=1)).replace(
                        hour=self.config.DAILY_END_HOUR,
                        minute=self.config.DAILY_END_MINUTE,
                        second=self.config.DAILY_END_SECOND,
                        microsecond=0
                    )
                else:
                    end_time = now.replace(
                        hour=self.config.DAILY_END_HOUR,
                        minute=self.config.DAILY_END_MINUTE,
                        second=self.config.DAILY_END_SECOND,
                        microsecond=0
                    )
                
                # 주말이나 공휴일인지 확인
                if self.time_util.should_skip_check(now):
                    reason = "주말" if self.time_util.is_weekend(now.weekday()) else "공휴일"
                    embed.add_field(
                        name="📅 오늘은 인증이 필요 없습니다",
                        value=f"오늘은 {reason}입니다.",
                        inline=False
                    )
                elif start_time <= now <= end_time:
                    # 남은 시간 계산
                    time_left = end_time - now
                    time_str = self.verification_service.message_util.format_time_delta(time_left)
                    
                    embed.add_field(
                        name="⚠️ 오늘 인증 필요",
                        value=f"인증 마감까지 {time_str} 남았습니다.",
                        inline=False
                    )
                    
                    embed.add_field(
                        name="📝 인증 방법",
                        value=f"인증 채널(<#{self.config.VERIFICATION_CHANNEL_ID}>)에 인증 키워드와 함께 이미지를 첨부하세요.\n"
                              f"인증 키워드: {', '.join([f'`{keyword}`' for keyword in self.config.VERIFICATION_KEYWORDS[:3]])} 등",
                        inline=False
                    )
                elif now < start_time:
                    # 아직 인증 시간이 아닌 경우
                    time_to_start = start_time - now
                    time_str = self.verification_service.message_util.format_time_delta(time_to_start)
                    
                    embed.add_field(
                        name="⏳ 아직 인증 시간이 아닙니다",
                        value=f"인증 시작까지 {time_str} 남았습니다.\n"
                              f"인증 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}",
                        inline=False
                    )
                else:
                    # 인증 시간이 지난 경우
                    embed.add_field(
                        name="❌ 오늘 인증 미완료",
                        value="인증 시간이 지났습니다.",
                        inline=False
                    )
            
            # 어제 인증 상태
            if self.time_util.should_skip_check(yesterday):
                reason = "주말" if self.time_util.is_weekend(yesterday.weekday()) else "공휴일"
                embed.add_field(
                    name="📅 어제는 인증이 필요 없었습니다",
                    value=f"어제는 {reason}이었습니다.",
                    inline=False
                )
            elif is_verified_yesterday:
                embed.add_field(
                    name="✅ 어제 인증 완료",
                    value=f"인증 시간: {verification_time_yesterday.strftime('%Y-%m-%d %H:%M:%S')}",
                    inline=False
                )
            else:
                embed.add_field(
                    name="❌ 어제 인증 미완료",
                    value="어제 인증을 하지 않았습니다.",
                    inline=False
                )
                
            # 날짜 정보
            embed.set_footer(text=f"현재 시간: {self.time_util.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"인증 상태 확인 중 오류 발생: {e}", exc_info=True)
            await interaction.followup.send(
                "인증 상태 확인 중 오류가 발생했습니다. 나중에 다시 시도하거나 관리자에게 문의하세요.",
                ephemeral=True
            )
    
    @app_commands.command(name="time_check", description="현재 봇이 인식하는 시간 확인")
    async def time_check(self, interaction: discord.Interaction):
        """현재 봇이 인식하는 시간을 확인합니다"""
        now = datetime.datetime.now()
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        now_kst = self.time_util.now()
        
        embed = discord.Embed(
            title="🕒 현재 시간 정보",
            description="봇이 인식하는 시간 정보입니다",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="서버 시간", value=now.strftime('%Y-%m-%d %H:%M:%S'), inline=False)
        embed.add_field(name="UTC 시간", value=now_utc.strftime('%Y-%m-%d %H:%M:%S'), inline=False)
        embed.add_field(name="KST 시간", value=now_kst.strftime('%Y-%m-%d %H:%M:%S'), inline=False)
        
        embed.set_footer(text=f"Discord Verification Bot | {self.bot.user.name}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="next_check", description="다음 인증 체크 시간 확인")
    async def next_check(self, interaction: discord.Interaction):
        """다음 인증 체크 시간을 확인합니다"""
        daily_next = self.task_manager.daily_check_task.next_iteration
        yesterday_next = self.task_manager.yesterday_check_task.next_iteration
        
        # UTC -> KST 변환
        daily_next_kst = daily_next.replace(tzinfo=datetime.timezone.utc).astimezone(self.config.TIMEZONE)
        yesterday_next_kst = yesterday_next.replace(tzinfo=datetime.timezone.utc).astimezone(self.config.TIMEZONE)
        
        embed = discord.Embed(
            title="⏰ 다음 인증 체크 시간",
            description="예정된 인증 체크 시간입니다",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="일일 인증 체크 (UTC)",
            value=daily_next.strftime('%Y-%m-%d %H:%M:%S'),
            inline=False
        )
        embed.add_field(
            name="일일 인증 체크 (KST)",
            value=daily_next_kst.strftime('%Y-%m-%d %H:%M:%S'),
            inline=False
        )
        embed.add_field(
            name="전일 인증 체크 (UTC)",
            value=yesterday_next.strftime('%Y-%m-%d %H:%M:%S'),
            inline=False
        )
        embed.add_field(
            name="전일 인증 체크 (KST)",
            value=yesterday_next_kst.strftime('%Y-%m-%d %H:%M:%S'),
            inline=False
        )
        
        # 남은 시간 계산 - tzinfo 일관성 보장
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        daily_next_aware = daily_next.replace(tzinfo=datetime.timezone.utc)
        yesterday_next_aware = yesterday_next.replace(tzinfo=datetime.timezone.utc)
        
        daily_delta = (daily_next_aware - now_utc).total_seconds()
        yesterday_delta = (yesterday_next_aware - now_utc).total_seconds()
        
        daily_hours, remainder = divmod(int(daily_delta), 3600)
        daily_minutes, daily_seconds = divmod(remainder, 60)
        
        yesterday_hours, remainder = divmod(int(yesterday_delta), 3600)
        yesterday_minutes, yesterday_seconds = divmod(remainder, 60)
        
        embed.add_field(
            name="남은 시간",
            value=f"일일 체크까지: {daily_hours}시간 {daily_minutes}분 {daily_seconds}초\n"
                  f"전일 체크까지: {yesterday_hours}시간 {yesterday_minutes}분 {yesterday_seconds}초",
            inline=False
        )
        
        embed.set_footer(text=f"Discord Verification Bot | {self.bot.user.name}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="check_settings", description="현재 설정된 체크 시간 확인")
    async def check_settings(self, interaction: discord.Interaction):
        """현재 설정된 체크 시간을 확인합니다"""
        embed = discord.Embed(
            title="⚙️ 인증 체크 설정",
            description="현재 설정된 인증 체크 관련 설정입니다",
            color=discord.Color.dark_green()
        )
        
        embed.add_field(
            name="일일 체크 시간 (KST)",
            value=f"{self.config.DAILY_CHECK_HOUR:02d}:{self.config.DAILY_CHECK_MINUTE:02d}",
            inline=True
        )
        embed.add_field(
            name="전일 체크 시간 (KST)",
            value=f"{self.config.YESTERDAY_CHECK_HOUR:02d}:{self.config.YESTERDAY_CHECK_MINUTE:02d}",
            inline=True
        )
        embed.add_field(
            name="일일 체크 시간 (UTC)",
            value=f"{self.config.UTC_DAILY_CHECK_HOUR:02d}:{self.config.DAILY_CHECK_MINUTE:02d}",
            inline=True
        )
        embed.add_field(
            name="전일 체크 시간 (UTC)",
            value=f"{self.config.UTC_YESTERDAY_CHECK_HOUR:02d}:{self.config.YESTERDAY_CHECK_MINUTE:02d}",
            inline=True
        )
        
        embed.add_field(
            name="📅 인증 시간 범위",
            value=f"시작: {self.config.DAILY_START_HOUR:02d}:{self.config.DAILY_START_MINUTE:02d}\n"
                  f"종료: {self.config.DAILY_END_HOUR:02d}:{self.config.DAILY_END_MINUTE:02d}:{self.config.DAILY_END_SECOND:02d}",
            inline=False
        )
        
        embed.set_footer(text=f"Discord Verification Bot | {self.bot.user.name}")
        
        await interaction.response.send_message(embed=embed)


class HolidayCommands(commands.Cog):
    """공휴일 관련 명령어 Cog"""
    
    def __init__(self, bot, config, time_util):
        self.bot = bot
        self.config = config
        self.time_util = time_util
    
    @commands.Cog.listener()
    async def on_ready(self):
        """봇이 준비되었을 때 실행"""
        logger.info("HolidayCommands Cog loaded")
    
    @app_commands.command(name="check_holidays", description="공휴일 정보 확인")
    @app_commands.describe(date="특정 날짜 확인 (YYYY-MM-DD 형식, 생략 시 전체 목록 표시)")
    async def check_holidays(self, interaction: discord.Interaction, date: Optional[str] = None):
        """
        공휴일 정보를 확인합니다
        
        사용법:
        /check_holidays - 모든 공휴일 목록 확인
        /check_holidays YYYY-MM-DD - 특정 날짜가 공휴일인지 확인
        """
        if date:
            try:
                # 날짜 형식 검증
                date_parts = date.split('-')
                if len(date_parts) != 3:
                    raise ValueError("Invalid date format")
                
                year, month, day = map(int, date_parts)
                check_date = datetime.datetime(year, month, day)
                
                # 공휴일 여부 확인
                is_holiday = self.config.is_holiday(check_date)
                is_weekend = self.time_util.is_weekend(check_date.weekday())
                
                embed = discord.Embed(
                    title="📅 날짜 확인 결과",
                    description=f"**{date}**",
                    color=discord.Color.brand_red() if is_holiday or is_weekend else discord.Color.dark_gray()
                )
                
                if is_holiday:
                    embed.add_field(name="상태", value="**🎉 공휴일**입니다", inline=False)
                elif is_weekend:
                    embed.add_field(name="상태", value="**🎉 주말**입니다", inline=False)
                else:
                    embed.add_field(name="상태", value="평일입니다 (공휴일 아님)", inline=False)
                
                await interaction.response.send_message(embed=embed)
            
            except ValueError:
                await interaction.response.send_message(
                    "❌ 날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요.",
                    ephemeral=True
                )
                
        else:
            # 전체 공휴일 목록 출력
            if not self.config.HOLIDAYS:
                await interaction.response.send_message("등록된 공휴일이 없습니다.", ephemeral=True)
                return
            
            # 공휴일 목록 정렬
            holiday_list = sorted(list(self.config.HOLIDAYS))
            
            # 연도별로 구분
            holidays_by_year = {}
            for date_str in holiday_list:
                year = date_str.split('-')[0]
                if year not in holidays_by_year:
                    holidays_by_year[year] = []
                holidays_by_year[year].append(date_str)
            
            # 임베드 생성
            embed = discord.Embed(
                title="📅 등록된 공휴일 목록",
                description=f"총 {len(holiday_list)}개의 공휴일이 등록되어 있습니다",
                color=discord.Color.brand_red()
            )
            
            # 연도별로 필드 추가
            for year, dates in holidays_by_year.items():
                value = "\n".join([f"- {date}" for date in dates])
                
                # Discord 필드 값 제한 (1024자) 처리
                if len(value) > 1024:
                    chunks = []
                    current_chunk = ""
                    for date in dates:
                        line = f"- {date}\n"
                        if len(current_chunk) + len(line) > 1020:
                            chunks.append(current_chunk)
                            current_chunk = line
                        else:
                            current_chunk += line
                    
                    if current_chunk:
                        chunks.append(current_chunk)
                    
                    for i, chunk in enumerate(chunks):
                        embed.add_field(
                            name=f"{year}년 ({i+1}/{len(chunks)})",
                            value=chunk,
                            inline=False
                        )
                else:
                    embed.add_field(name=f"{year}년", value=value, inline=False)
            
            await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="toggle_holiday_check", description="공휴일 체크 기능 켜기/끄기 (관리자 전용)")
    async def toggle_holiday_check(self, interaction: discord.Interaction):
        """공휴일 체크 기능을 켜거나 끕니다 (관리자 전용)"""
        # 관리자 권한 체크
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                self.config.MESSAGES['permission_error'],
                ephemeral=True
            )
            return
            
        # 공휴일 스킵 설정 토글
        self.config.SKIP_HOLIDAYS = not self.config.SKIP_HOLIDAYS
        
        embed = discord.Embed(
            title="⚙️ 공휴일 체크 설정 변경",
            description=f"공휴일 체크 기능이 **{'활성화' if self.config.SKIP_HOLIDAYS else '비활성화'}** 되었습니다.",
            color=discord.Color.green() if self.config.SKIP_HOLIDAYS else discord.Color.orange()
        )
        
        if self.config.SKIP_HOLIDAYS:
            embed.add_field(
                name="현재 상태",
                value="공휴일에는 인증 체크를 하지 않습니다.",
                inline=False
            )
        else:
            embed.add_field(
                name="현재 상태",
                value="공휴일에도 인증 체크를 수행합니다.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="reload_holidays", description="공휴일 목록 다시 로드 (관리자 전용)")
    async def reload_holidays(self, interaction: discord.Interaction):
        """공휴일 목록을 다시 로드합니다 (관리자 전용)"""
        # 관리자 권한 체크
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                self.config.MESSAGES['permission_error'],
                ephemeral=True
            )
            return
            
        old_count = len(self.config.HOLIDAYS)
        self.config.load_holidays()
        new_count = len(self.config.HOLIDAYS)
        
        embed = discord.Embed(
            title="📅 공휴일 목록 재로드",
            description="공휴일 목록을 다시 로드했습니다.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="변경 정보",
            value=f"이전: {old_count}개 → 현재: {new_count}개",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)


class AdminCommands(commands.Cog):
    """관리자 전용 명령어 Cog"""
    
    def __init__(self, bot, config, verification_service):
        self.bot = bot
        self.config = config
        self.verification_service = verification_service
    
    @commands.Cog.listener()
    async def on_ready(self):
        """봇이 준비되었을 때 실행"""
        logger.info("AdminCommands Cog loaded")
    
    @app_commands.command(name="test_check", description="인증 체크를 즉시 테스트 (관리자 전용)")
    @app_commands.choices(check_type=[
        app_commands.Choice(name="일일 체크만", value="daily"),
        app_commands.Choice(name="전일 체크만", value="yesterday"),
        app_commands.Choice(name="모두 실행", value="both")
    ])
    async def test_check(
        self,
        interaction: discord.Interaction,
        check_type: app_commands.Choice[str]
    ):
        """인증 체크를 즉시 테스트합니다 (관리자 전용)"""
        # 관리자 권한 체크
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                self.config.MESSAGES['permission_error'],
                ephemeral=True
            )
            return
        
        await interaction.response.defer(thinking=True)
        
        if check_type.value == "daily" or check_type.value == "both":
            await self.verification_service.check_daily_verification()
        
        if check_type.value == "yesterday" or check_type.value == "both":
            await self.verification_service.check_yesterday_verification()
        
        embed = discord.Embed(
            title="✅ 인증 체크 테스트 완료",
            description=f"테스트 타입: {check_type.name}",
            color=discord.Color.green()
        )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="check_now", description="즉시 인증 체크 실행 (관리자 전용)")
    async def check_now(self, interaction: discord.Interaction):
        """테스트용: 즉시 인증 체크를 실행합니다 (관리자 전용)"""
        # 관리자 권한 체크
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                self.config.MESSAGES['permission_error'],
                ephemeral=True
            )
            return
            
        await interaction.response.defer(thinking=True)
        
        await self.verification_service.check_daily_verification()
        
        embed = discord.Embed(
            title="✅ 인증 체크 실행 완료",
            description="일일 인증 체크가 실행되었습니다.",
            color=discord.Color.green()
        )
        
        await interaction.followup.send(embed=embed)


class StatusCommands(commands.Cog):
    """상태 확인 명령어 Cog"""
    
    def __init__(self, bot, config, task_manager, time_util):
        self.bot = bot
        self.config = config
        self.task_manager = task_manager
        self.time_util = time_util
    
    @commands.Cog.listener()
    async def on_ready(self):
        """봇이 준비되었을 때 실행"""
        logger.info("StatusCommands Cog loaded")
    
    @app_commands.command(name="status", description="봇 상태 정보 확인")
    async def status(self, interaction: discord.Interaction):
        """봇의 현재 상태와 설정 정보를 확인합니다"""
        # 현재 시간
        now = self.time_util.now()
        
        # 다음 체크 시간
        daily_next = self.task_manager.daily_check_task.next_iteration
        yesterday_next = self.task_manager.yesterday_check_task.next_iteration
        
        # UTC -> KST 변환
        daily_next_kst = daily_next.replace(tzinfo=datetime.timezone.utc).astimezone(self.config.TIMEZONE)
        yesterday_next_kst = yesterday_next.replace(tzinfo=datetime.timezone.utc).astimezone(self.config.TIMEZONE)
        
        # 남은 시간 계산 - tzinfo 일관성 보장
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        daily_next_aware = daily_next.replace(tzinfo=datetime.timezone.utc)
        yesterday_next_aware = yesterday_next.replace(tzinfo=datetime.timezone.utc)
        
        daily_delta = (daily_next_aware - now_utc).total_seconds()
        yesterday_delta = (yesterday_next_aware - now_utc).total_seconds()
        
        daily_hours, remainder = divmod(int(daily_delta), 3600)
        daily_minutes, daily_seconds = divmod(remainder, 60)
        
        yesterday_hours, remainder = divmod(int(yesterday_delta), 3600)
        yesterday_minutes, yesterday_seconds = divmod(remainder, 60)
        
        # 상태 정보 메시지 생성
        embed = discord.Embed(
            title="📊 봇 상태 정보",
            description=f"현재 시간: {now.strftime('%Y-%m-%d %H:%M:%S')} KST",
            color=discord.Color.blue()
        )
        
        # 기본 설정 정보
        embed.add_field(
            name="📝 기본 설정",
            value=f"인증 채널: <#{self.config.VERIFICATION_CHANNEL_ID}>\n"
                  f"공휴일 스킵: {'활성화' if self.config.SKIP_HOLIDAYS else '비활성화'}\n"
                  f"등록된 공휴일: {len(self.config.HOLIDAYS)}개",
            inline=False
        )
        
        # 체크 일정 정보
        embed.add_field(
            name="⏰ 다음 체크 일정 (KST)",
            value=f"일일 체크: {daily_next_kst.strftime('%Y-%m-%d %H:%M:%S')}\n"
                  f"어제 체크: {yesterday_next_kst.strftime('%Y-%m-%d %H:%M:%S')}",
            inline=False
        )
        
        # 남은 시간
        embed.add_field(
            name="⌛ 남은 시간",
            value=f"일일 체크까지: {daily_hours}시간 {daily_minutes}분 {daily_seconds}초\n"
                  f"전일 체크까지: {yesterday_hours}시간 {yesterday_minutes}분 {yesterday_seconds}초",
            inline=False
        )
        
        # 인증 시간 범위
        embed.add_field(
            name="🕒 인증 시간 범위",
            value=f"시작: {self.config.DAILY_START_HOUR:02d}:{self.config.DAILY_START_MINUTE:02d}\n"
                  f"종료: {self.config.DAILY_END_HOUR:02d}:{self.config.DAILY_END_MINUTE:02d}:{self.config.DAILY_END_SECOND:02d}",
            inline=False
        )
        
        # 봇 정보
        embed.set_footer(text=f"Discord Verification Bot | {self.bot.user.name}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="help", description="인증 봇 도움말")
    async def help_command(self, interaction: discord.Interaction):
        """인증 봇 도움말을 표시합니다"""
        embed = discord.Embed(
            title="📋 인증 봇 도움말",
            description="슬래시 명령어(`/`) 목록입니다.",
            color=discord.Color.green()
        )
        
        # 일반 명령어
        embed.add_field(
            name="🔹 일반 명령어",
            value="`/hello` - 인사 테스트\n"
                  "`/verify_status` - 내 인증 상태 확인\n"
                  "`/time_check` - 현재 시간 확인\n"
                  "`/next_check` - 다음 인증 체크 시간 확인\n"
                  "`/check_settings` - 현재 설정 확인\n"
                  "`/check_holidays` - 공휴일 목록 확인\n"
                  "`/status` - 봇 상태 정보 확인\n"
                  "`/help` - 이 도움말 표시\n"
                  "`/vacation` - 휴가 등록 (YYYY-MM-DD, 생략 시 오늘)\n"
                  "`/cancel_vacation` - 모든 휴가 취소\n"
                  "`/my_vacations` - 내 휴가 목록 확인",
            inline=False
        )
        
        # 관리자 명령어
        embed.add_field(
            name="🔹 관리자 명령어",
            value="`/test_check` - 인증 체크 즉시 테스트\n"
                  "`/check_now` - 즉시 인증 체크 실행\n"
                  "`/toggle_holiday_check` - 공휴일 체크 기능 켜기/끄기\n"
                  "`/reload_holidays` - 공휴일 목록 다시 로드",
            inline=False
        )
        
        # 인증 방법
        embed.add_field(
            name="📝 인증 방법",
            value="인증 채널에 인증 키워드와 함께 이미지를 첨부하여 메시지를 보내세요.\n"
                 f"인증 키워드: {', '.join([f'`{keyword}`' for keyword in self.config.VERIFICATION_KEYWORDS[:3]])} 등",
            inline=False
        )
        
        # 디스코드 인증 팁
        embed.add_field(
            name="💡 인증 팁",
            value="1. 인증 채널에 이미지를 드래그 앤 드롭하세요.\n"
                  "2. 이미지를 업로드한 후 인증 키워드(예: 인증사진)를 포함한 메시지를 작성하세요.\n"
                  "3. 인증이 성공하면 체크 표시(✅)가 표시됩니다.\n"
                  "4. 인증 여부는 `/verify_status` 명령어로 확인할 수 있습니다.",
            inline=False
        )
        
        # 체크 시간
        embed.add_field(
            name="⏰ 체크 시간",
            value=f"일일 체크: 매일 {self.config.DAILY_CHECK_HOUR:02d}:{self.config.DAILY_CHECK_MINUTE:02d} KST\n"
                  f"어제 체크: 매일 {self.config.YESTERDAY_CHECK_HOUR:02d}:{self.config.YESTERDAY_CHECK_MINUTE:02d} KST\n"
                  f"인증 가능 시간: {self.config.DAILY_START_HOUR:02d}:{self.config.DAILY_START_MINUTE:02d} ~ {self.config.DAILY_END_HOUR:02d}:{self.config.DAILY_END_MINUTE:02d}",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)


class VacationCommands(commands.Cog):
    """휴가 관련 명령어 Cog"""
    
    def __init__(self, bot, config, vacation_service, time_util):
        self.bot = bot
        self.config = config
        self.vacation_service = vacation_service
        self.time_util = time_util
    
    @commands.Cog.listener()
    async def on_ready(self):
        """봇이 준비되었을 때 실행"""
        logger.info("VacationCommands Cog loaded")
        
    async def _vacation_logic(self, interaction: discord.Interaction, date: Optional[str] = None):
        """휴가 등록 로직"""
        result = self.vacation_service.register_vacation(interaction.user.id, date)
        
        if "이미 휴가로 등록" in result:
            color = discord.Color.yellow()
            title = "⚠️ 이미 등록된 휴가"
        elif "날짜 형식이 올바르지 않습니다" in result or "과거 날짜는 휴가로" in result:
            color = discord.Color.red()
            title = "❌ 휴가 등록 실패"
        else:
            color = discord.Color.green()
            title = "🏖️ 휴가 등록 완료"
        
        embed = discord.Embed(title=title, description=result, color=color)
        
        vacations = self.vacation_service.get_user_vacations(interaction.user.id)
        if vacations:
            vacation_list = "\n".join([f"• {date}" for date in vacations])
            embed.add_field(name="📅 등록된 휴가 목록", value=vacation_list, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="vacation", description="휴가 등록")
    @app_commands.describe(date="휴가 날짜 (YYYY-MM-DD 형식, 생략 시 오늘)")
    async def vacation(self, interaction: discord.Interaction, date: Optional[str] = None):
        await self._vacation_logic(interaction, date)
            
    async def _cancel_vacation_logic(self, interaction: discord.Interaction):
        """휴가 취소 로직"""
        result = self.vacation_service.cancel_all_vacations(interaction.user.id)
        
        if "등록된 휴가가 없습니다" in result:
            color = discord.Color.blue()
            title = "ℹ️ 휴가 정보"
        else:
            color = discord.Color.green()
            title = "✅ 휴가 취소 완료"
        
        embed = discord.Embed(title=title, description=result, color=color)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="cancel_vacation", description="모든 휴가 취소")
    async def cancel_vacation(self, interaction: discord.Interaction):
        await self._cancel_vacation_logic(interaction)
            
    async def _my_vacations_logic(self, interaction: discord.Interaction):
        """내 휴가 목록 확인 로직"""
        vacations = self.vacation_service.get_user_vacations(interaction.user.id)
        
        if not vacations:
            embed = discord.Embed(title="📅 내 휴가 목록", description="등록된 휴가가 없습니다.", color=discord.Color.blue())
        else:
            vacation_list = "\n".join([f"• {date}" for date in vacations])
            embed = discord.Embed(title="📅 내 휴가 목록", description=f"총 {len(vacations)}개의 휴가가 등록되어 있습니다.", color=discord.Color.green())
            embed.add_field(name="등록된 날짜", value=vacation_list, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="my_vacations", description="내 휴가 목록 확인")
    async def my_vacations(self, interaction: discord.Interaction):
        await self._my_vacations_logic(interaction)


class CommandSetup:
    """명령어 설정 클래스"""
    
    def __init__(self, bot, config, verification_service, task_manager, time_util, vacation_service):
        self.bot = bot
        self.config = config
        self.verification_service = verification_service
        self.task_manager = task_manager
        self.time_util = time_util
        self.vacation_service = vacation_service
        
        # 기존 명령어 제거 (필요한 경우)
        self._remove_commands()
        
        # 명령어 Cog 추가는 async가 필요하므로 on_ready에서 수행하도록 설정
        self.add_cogs_done = False
    
    def _remove_commands(self):
        """기존 명령어 제거"""
        for command in list(self.bot.commands):
            self.bot.remove_command(command.name)
    
    async def add_cogs_if_needed(self):
        """명령어 Cog 추가 (아직 추가되지 않은 경우)"""
        if self.add_cogs_done:
            return
            
        # 검증 관련 명령어
        verification_commands = VerificationCommands(
            self.bot, self.config, self.verification_service, self.task_manager, self.time_util
        )
        await self.bot.add_cog(verification_commands)
        
        # 공휴일 관련 명령어
        holiday_commands = HolidayCommands(
            self.bot, self.config, self.time_util
        )
        await self.bot.add_cog(holiday_commands)
        
        # 관리자 전용 명령어
        admin_commands = AdminCommands(
            self.bot, self.config, self.verification_service
        )
        await self.bot.add_cog(admin_commands)
        
        # 상태 확인 명령어
        status_commands = StatusCommands(
            self.bot, self.config, self.task_manager, self.time_util
        )
        await self.bot.add_cog(status_commands)
        
        # 휴가 관련 명령어
        vacation_commands = VacationCommands(
            self.bot, self.config, self.vacation_service, self.time_util
        )
        await self.bot.add_cog(vacation_commands)
        
        self.add_cogs_done = True
        logger.info("명령어 Cog 추가 완료")


# CommandHandler 클래스를 CommandSetup 클래스로 대체
CommandHandler = CommandSetup 