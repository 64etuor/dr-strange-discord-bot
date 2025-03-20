"""
봇 명령어 처리 모듈
"""
import datetime
import discord
import logging
from discord.ext import commands

logger = logging.getLogger('verification_bot')

class CommandHandler:
    """명령어 처리 클래스"""
    
    def __init__(self, bot, config, verification_service, task_manager, time_util):
        self.bot = bot
        self.config = config
        self.verification_service = verification_service
        self.task_manager = task_manager
        self.time_util = time_util
        
        # 명령어 등록
        self._register_commands()
    
    def _register_commands(self):
        """명령어 등록"""
        
        @self.bot.command()
        async def hello(ctx):
            """인사 명령어"""
            await ctx.send('Hello!')
        
        @self.bot.command()
        async def check_now(ctx):
            """테스트용: 즉시 인증 체크를 실행합니다"""
            await ctx.send("Verification check started...")
            await self.verification_service.check_daily_verification()
            await ctx.send("Verification check completed.")
        
        @self.bot.command()
        async def time_check(ctx):
            """현재 봇이 인식하는 시간을 확인합니다"""
            now = datetime.datetime.now()
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            now_kst = self.time_util.now()
            
            await ctx.send(
                "🕒 Current time information:\n"
                f"Server time: {now}\n"
                f"UTC time: {now_utc}\n"
                f"KST time: {now_kst}"
            )
        
        @self.bot.command()
        async def next_check(ctx):
            """다음 인증 체크 시간을 확인합니다"""
            daily_next = self.task_manager.daily_check_task.next_iteration
            yesterday_next = self.task_manager.yesterday_check_task.next_iteration
            
            await ctx.send(
                "⏰ Next verification check time:\n"
                f"Daily verification check: {daily_next.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                f"Previous day verification check: {yesterday_next.strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )
        
        @self.bot.command()
        async def test_check(ctx):
            """인증 체크를 즉시 테스트합니다 (관리자 전용)"""
            if not ctx.author.guild_permissions.administrator:
                await ctx.send(self.config.MESSAGES['permission_error'])
                return
                
            await ctx.send("🔍 Verification test started...")
            await self.verification_service.check_daily_verification()
            await self.verification_service.check_yesterday_verification()
            await ctx.send("✅ Verification test completed.")
        
        @self.bot.command()
        async def check_settings(ctx):
            """현재 설정된 체크 시간을 확인합니다"""
            await ctx.send(
                "⚙️ Current Check Time Settings:\n"
                f"Daily Check (KST): {self.config.DAILY_CHECK_HOUR:02d}:{self.config.DAILY_CHECK_MINUTE:02d}\n"
                f"Yesterday Check (KST): {self.config.YESTERDAY_CHECK_HOUR:02d}:{self.config.YESTERDAY_CHECK_MINUTE:02d}\n"
                f"Daily Check (UTC): {self.config.UTC_DAILY_CHECK_HOUR:02d}:{self.config.DAILY_CHECK_MINUTE:02d}\n"
                f"Yesterday Check (UTC): {self.config.UTC_YESTERDAY_CHECK_HOUR:02d}:{self.config.YESTERDAY_CHECK_MINUTE:02d}\n"
                "\n📅 Verification Time Range:\n"
                f"Start: {self.config.DAILY_START_HOUR:02d}:{self.config.DAILY_START_MINUTE:02d}\n"
                f"End: {self.config.DAILY_END_HOUR:02d}:{self.config.DAILY_END_MINUTE:02d}:{self.config.DAILY_END_SECOND:02d}"
            )
            
        @self.bot.command()
        async def check_holidays(ctx, date_str=None):
            """
            공휴일 정보를 확인합니다
            
            사용법:
            !check_holidays - 모든 공휴일 목록 확인
            !check_holidays YYYY-MM-DD - 특정 날짜가 공휴일인지 확인
            """
            if date_str:
                try:
                    # 날짜 형식 검증
                    date_parts = date_str.split('-')
                    if len(date_parts) != 3:
                        raise ValueError("Invalid date format")
                    
                    year, month, day = map(int, date_parts)
                    check_date = datetime.datetime(year, month, day)
                    
                    # 공휴일 여부 확인
                    is_holiday = self.config.is_holiday(check_date)
                    is_weekend = self.time_util.is_weekend(check_date.weekday())
                    
                    if is_holiday:
                        await ctx.send(f"📅 {date_str}은(는) **공휴일**입니다.")
                    elif is_weekend:
                        await ctx.send(f"📅 {date_str}은(는) **주말**입니다.")
                    else:
                        await ctx.send(f"📅 {date_str}은(는) 공휴일이 아닙니다.")
                
                except ValueError:
                    await ctx.send("❌ 날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요.")
                    
            else:
                # 전체 공휴일 목록 출력
                if not self.config.HOLIDAYS:
                    await ctx.send("등록된 공휴일이 없습니다.")
                    return
                
                # 공휴일 목록 정렬
                holiday_list = sorted(list(self.config.HOLIDAYS))
                
                # 메시지 생성
                message = "📅 **등록된 공휴일 목록**\n\n"
                current_year = None
                
                for date_str in holiday_list:
                    year = date_str.split('-')[0]
                    
                    # 연도별로 구분
                    if year != current_year:
                        message += f"\n**{year}년**\n"
                        current_year = year
                    
                    message += f"- {date_str}\n"
                
                # 메시지 길이 제한 체크
                if len(message) > 2000:
                    # 여러 메시지로 나누어 전송
                    parts = []
                    current_part = "📅 **등록된 공휴일 목록**\n\n"
                    current_year = None
                    
                    for date_str in holiday_list:
                        year = date_str.split('-')[0]
                        
                        # 연도별로 구분
                        year_header = ""
                        if year != current_year:
                            year_header = f"\n**{year}년**\n"
                            current_year = year
                        
                        line = year_header + f"- {date_str}\n"
                        
                        # 메시지 길이 체크
                        if len(current_part) + len(line) > 2000:
                            parts.append(current_part)
                            current_part = line
                        else:
                            current_part += line
                    
                    if current_part:
                        parts.append(current_part)
                    
                    # 여러 메시지로 전송
                    for part in parts:
                        await ctx.send(part)
                else:
                    await ctx.send(message)
        
        @self.bot.command()
        async def status(ctx):
            """봇의 현재 상태와 설정 정보를 확인합니다"""
            # 현재 시간
            now = self.time_util.now()
            
            # 다음 체크 시간
            daily_next = self.task_manager.daily_check_task.next_iteration
            yesterday_next = self.task_manager.yesterday_check_task.next_iteration
            
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
                name="⏰ 다음 체크 일정",
                value=f"일일 체크: {daily_next.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                      f"어제 체크: {yesterday_next.strftime('%Y-%m-%d %H:%M:%S')} UTC",
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
            
            await ctx.send(embed=embed)
            
        @self.bot.command()
        @commands.has_permissions(administrator=True)
        async def toggle_holiday_check(ctx):
            """공휴일 체크 기능을 켜거나 끕니다 (관리자 전용)"""
            # 공휴일 스킵 설정 토글
            self.config.SKIP_HOLIDAYS = not self.config.SKIP_HOLIDAYS
            
            if self.config.SKIP_HOLIDAYS:
                await ctx.send("✅ 공휴일 체크 기능이 **활성화**되었습니다. 공휴일에는 인증 체크를 하지 않습니다.")
            else:
                await ctx.send("✅ 공휴일 체크 기능이 **비활성화**되었습니다. 공휴일에도 인증 체크를 수행합니다.")
            
        @self.bot.command()
        @commands.has_permissions(administrator=True)
        async def reload_holidays(ctx):
            """공휴일 목록을 다시 로드합니다 (관리자 전용)"""
            old_count = len(self.config.HOLIDAYS)
            self.config.load_holidays()
            new_count = len(self.config.HOLIDAYS)
            
            await ctx.send(f"✅ 공휴일 목록을 다시 로드했습니다.\n"
                          f"이전: {old_count}개 → 현재: {new_count}개")
            
        @self.bot.command()
        async def vacation(ctx, start_date: str = None, end_date: str = None):
            """
            휴가를 등록합니다
            
            사용법:
            !vacation - 당일 휴가 등록
            !vacation YYYY-MM-DD - 특정 날짜 휴가 등록
            !vacation YYYY-MM-DD YYYY-MM-DD - 기간 휴가 등록
            """
            try:
                if start_date:
                    # 날짜 형식 검증
                    try:
                        start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
                        
                        if end_date:
                            end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
                            if end < start:
                                await ctx.send("❌ 종료일이 시작일보다 이전입니다.")
                                return
                        else:
                            end = start  # 종료일이 없으면 시작일과 동일하게 설정
                    except ValueError:
                        await ctx.send("❌ 날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요.")
                        return
                else:
                    # 인자가 없으면 당일 휴가
                    start = datetime.datetime.now().date()
                    end = start
                
                # 휴가 등록
                self.bot.vacation_users[ctx.author.id] = (start, end)
                
                # 확인 메시지
                if start == end:
                    await ctx.send(f"✅ {ctx.author.mention}님의 {start} 휴가가 등록되었습니다.")
                else:
                    await ctx.send(f"✅ {ctx.author.mention}님의 {start} ~ {end} 휴가가 등록되었습니다.")
                
            except Exception as e:
                logger.error(f"휴가 명령어 처리 중 오류: {e}", exc_info=True)
                await ctx.send("❌ 휴가 등록 중 오류가 발생했습니다.")
        
        @self.bot.command()
        async def cancel_vacation(ctx):
            """등록된 휴가를 취소합니다"""
            if ctx.author.id in self.bot.vacation_users:
                start, end = self.bot.vacation_users[ctx.author.id]
                del self.bot.vacation_users[ctx.author.id]
                
                if start == end:
                    await ctx.send(f"✅ {ctx.author.mention}님의 {start} 휴가가 취소되었습니다.")
                else:
                    await ctx.send(f"✅ {ctx.author.mention}님의 {start} ~ {end} 휴가가 취소되었습니다.")
            else:
                await ctx.send("❌ 등록된 휴가가 없습니다.")
        
        @self.bot.command()
        async def my_vacation(ctx):
            """내 휴가 정보를 확인합니다"""
            if ctx.author.id in self.bot.vacation_users:
                start, end = self.bot.vacation_users[ctx.author.id]
                
                if start == end:
                    await ctx.send(f"🗓️ {ctx.author.mention}님은 {start}에 휴가 예정입니다.")
                else:
                    await ctx.send(f"🗓️ {ctx.author.mention}님은 {start} ~ {end} 기간에 휴가 예정입니다.")
            else:
                await ctx.send("❌ 등록된 휴가가 없습니다.")
        
        @self.bot.command()
        @commands.has_permissions(administrator=True)
        async def list_vacations(ctx):
            """현재 등록된 모든 휴가 목록을 확인합니다 (관리자 전용)"""
            if not self.bot.vacation_users:
                await ctx.send("현재 등록된 휴가가 없습니다.")
                return
            
            # 현재 날짜
            today = datetime.datetime.now().date()
            
            # 임베드 생성
            embed = discord.Embed(
                title="🏝️ 휴가 목록",
                description=f"현재 시간: {today}",
                color=discord.Color.gold()
            )
            
            # 현재 진행 중인 휴가와 예정된 휴가 분류
            active_vacations = []
            upcoming_vacations = []
            past_vacations = []
            
            for user_id, (start, end) in self.bot.vacation_users.items():
                user = ctx.guild.get_member(user_id)
                if not user:
                    continue
                
                vacation_str = f"{user.mention}: "
                if start == end:
                    vacation_str += f"{start}"
                else:
                    vacation_str += f"{start} ~ {end}"
                
                if start <= today <= end:
                    active_vacations.append(vacation_str)
                elif start > today:
                    upcoming_vacations.append(vacation_str)
                elif end < today:
                    past_vacations.append(vacation_str)
            
            # 현재 진행 중인 휴가
            if active_vacations:
                embed.add_field(
                    name="🔴 현재 휴가 중",
                    value="\n".join(active_vacations),
                    inline=False
                )
            
            # 예정된 휴가
            if upcoming_vacations:
                embed.add_field(
                    name="🟡 예정된 휴가",
                    value="\n".join(upcoming_vacations),
                    inline=False
                )
            
            # 지난 휴가
            if past_vacations:
                embed.add_field(
                    name="⚪ 지난 휴가",
                    value="\n".join(past_vacations),
                    inline=False
                )
            
            await ctx.send(embed=embed)
        
        @self.bot.command()
        async def help_verification(ctx):
            """인증 봇 도움말을 표시합니다"""
            embed = discord.Embed(
                title="📋 인증 봇 도움말",
                description="인증 관련 명령어 목록입니다.",
                color=discord.Color.green()
            )
            
            # 일반 명령어
            embed.add_field(
                name="🔹 일반 명령어",
                value="`!hello` - 인사 테스트\n"
                      "`!time_check` - 현재 시간 확인\n"
                      "`!next_check` - 다음 인증 체크 시간 확인\n"
                      "`!check_settings` - 현재 설정 확인\n"
                      "`!check_holidays` - 공휴일 목록 확인\n"
                      "`!check_holidays YYYY-MM-DD` - 특정 날짜 공휴일 여부 확인\n"
                      "`!status` - 봇 상태 정보 확인\n"
                      "`!help_verification` - 이 도움말 표시",
                inline=False
            )
            
            # 휴가 명령어 추가
            embed.add_field(
                name="🔹 휴가 명령어",
                value="`!vacation` - 당일 휴가 등록\n"
                      "`!vacation YYYY-MM-DD` - 특정 날짜 휴가 등록\n"
                      "`!vacation YYYY-MM-DD YYYY-MM-DD` - 기간 휴가 등록\n"
                      "`!cancel_vacation` - 등록된 휴가 취소\n"
                      "`!my_vacation` - 내 휴가 정보 확인\n"
                      "채널에 '휴가 YYYY-MM-DD' 형식으로 작성해도 등록됩니다.",
                inline=False
            )
            
            # 관리자 명령어
            embed.add_field(
                name="🔹 관리자 명령어",
                value="`!test_check` - 인증 체크 즉시 테스트\n"
                      "`!check_now` - 즉시 인증 체크 실행\n"
                      "`!toggle_holiday_check` - 공휴일 체크 기능 켜기/끄기\n"
                      "`!reload_holidays` - 공휴일 목록 다시 로드\n"
                      "`!list_vacations` - 모든 휴가 목록 확인",
                inline=False
            )
            
            # 인증 방법
            embed.add_field(
                name="📝 인증 방법",
                value="인증 채널에 '인증사진' 또는 '인증 사진'이라는 키워드와 함께 이미지를 첨부하여 메시지를 보내세요.",
                inline=False
            )
            
            # 체크 시간
            embed.add_field(
                name="⏰ 체크 시간",
                value=f"일일 체크: 매일 {self.config.DAILY_CHECK_HOUR:02d}:{self.config.DAILY_CHECK_MINUTE:02d} KST\n"
                      f"어제 체크: 매일 {self.config.YESTERDAY_CHECK_HOUR:02d}:{self.config.YESTERDAY_CHECK_MINUTE:02d} KST",
                inline=False
            )
            
            await ctx.send(embed=embed) 