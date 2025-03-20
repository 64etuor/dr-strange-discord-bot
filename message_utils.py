"""
메시지 관련 유틸리티 모듈
"""
import discord
import re
import datetime
from typing import List, Optional, Tuple, Set

class MessageUtility:
    """메시지 관련 유틸리티 클래스"""
    
    def __init__(self, config):
        self.config = config
    
    def is_verification_message(self, content: str) -> bool:
        """인증 메시지인지 확인"""
        return any(keyword in content for keyword in self.config.VERIFICATION_KEYWORDS)
    
    def is_vacation_message(self, content: str) -> bool:
        """휴가 메시지인지 확인"""
        content_lower = content.lower()
        return "휴가" in content_lower and not self.is_verification_message(content)
    
    def is_valid_image(self, attachment: discord.Attachment) -> bool:
        """유효한 이미지인지 확인"""
        if not attachment.content_type:
            return False
            
        is_image = attachment.content_type.startswith('image/')
        is_valid_size = attachment.size <= self.config.MAX_ATTACHMENT_SIZE
        
        return is_image and is_valid_size
    
    def chunk_mentions(self, members: List[discord.Member]) -> List[str]:
        """멘션 목록을 Discord 메시지 길이 제한에 맞게 분할"""
        if not members:
            return []
            
        chunks = []
        current_chunk = ""
        
        for member in members:
            mention = member.mention + " "
            
            # 현재 청크 + 새 멘션이 최대 길이를 초과하면 새 청크 시작
            if len(current_chunk) + len(mention) > self.config.MAX_MESSAGE_LENGTH:
                chunks.append(current_chunk.strip())
                current_chunk = mention
            else:
                current_chunk += mention
                
        # 마지막 청크 추가
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks
    
    def parse_vacation_date(self, content: str) -> Optional[Tuple[datetime.date, datetime.date]]:
        """
        휴가 메시지에서 날짜 정보 추출
        형식: 
        - "휴가 YYYY-MM-DD" (하루)
        - "휴가 YYYY-MM-DD ~ YYYY-MM-DD" (기간)
        
        반환:
        - (시작일, 종료일) 또는 오류 시 None
        """
        # 날짜 패턴 (YYYY-MM-DD)
        date_pattern = r'(\d{4}-\d{2}-\d{2})'
        
        # 하루 휴가 패턴 확인
        single_day_match = re.search(f"휴가\\s+{date_pattern}", content)
        if single_day_match:
            try:
                date_str = single_day_match.group(1)
                vacation_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                return (vacation_date, vacation_date)  # 시작일과 종료일이 같음
            except ValueError:
                return None
        
        # 기간 휴가 패턴 확인
        range_match = re.search(f"휴가\\s+{date_pattern}\\s*~\\s*{date_pattern}", content)
        if range_match:
            try:
                start_str = range_match.group(1)
                end_str = range_match.group(2)
                start_date = datetime.datetime.strptime(start_str, '%Y-%m-%d').date()
                end_date = datetime.datetime.strptime(end_str, '%Y-%m-%d').date()
                
                # 종료일이 시작일보다 이전이면 None 반환 - 여기가 제대로 작동하도록 수정
                if end_date < start_date:
                    return None
                    
                return (start_date, end_date)
            except ValueError:
                return None
        
        # 잘못된 형식(예: 2023/01/01, 01-15-2023)이면 None 반환
        if re.search(r"휴가\s+[\d/\-]+", content) and not re.search(r"휴가\s+\d{4}-\d{2}-\d{2}", content):
            return None
        
        # 기본 - 당일만 휴가로 처리
        current_date = datetime.datetime.now().date()
        return (current_date, current_date) 