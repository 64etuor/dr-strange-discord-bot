"""
메시지 처리 유틸리티 모듈
"""
import discord
import datetime
from typing import List, Dict, Tuple

class MessageUtility:
    """메시지 관련 유틸리티 클래스"""
    
    def __init__(self, config):
        self.config = config
    
    def is_verification_message(self, content: str) -> bool:
        """인증 메시지인지 확인"""
        if not content:
            return False
        
        content_lower = content.lower()
        return any(keyword.lower() in content_lower for keyword in self.config.VERIFICATION_KEYWORDS)
    
    def is_valid_image(self, attachment: discord.Attachment) -> bool:
        """유효한 이미지인지 확인"""
        if not attachment:
            return False
            
        return (attachment.content_type and 
                attachment.content_type.startswith('image/') and 
                attachment.size <= self.config.MAX_ATTACHMENT_SIZE)
    
    def chunk_mentions(self, members: List[discord.Member], max_per_chunk: int = None) -> List[str]:
        """
        멤버 멘션을 Discord 메시지 길이 제한에 맞게 청크로 분할
        """
        if max_per_chunk is None:
            max_per_chunk = self.config.MAX_MENTIONS_PER_CHUNK
            
        chunks = []
        current_chunk = []
        current_length = 0
        current_count = 0
        
        for member in members:
            mention = member.mention
            
            mention_length = 25
            
            if (current_length + mention_length + 2 > self.config.MAX_MESSAGE_LENGTH or 
                current_count >= max_per_chunk):
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0
                current_count = 0
            
            current_chunk.append(mention)
            current_length += mention_length + 2
            current_count += 1
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks
    
    def format_time_delta(self, delta: datetime.timedelta) -> str:
        """
        시간 차이를 읽기 쉬운 형식으로 변환
        
        Args:
            delta: 시간 차이 (datetime.timedelta)
            
        Returns:
            "X시간 Y분 Z초" 형식의 문자열
        """
        total_seconds = int(delta.total_seconds())
        
        if total_seconds < 0:
            return "0초"
            
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        
        if hours > 0:
            parts.append(f"{hours}시간")
        if minutes > 0 or hours > 0:
            parts.append(f"{minutes}분")
        parts.append(f"{seconds}초")
        
        return " ".join(parts)
    
    def group_members_by_role(self, members: List[discord.Member]) -> Dict[str, List[discord.Member]]:
        """
        멤버를 역할별로 그룹화
        
        Args:
            members: 그룹화할 멤버 목록
            
        Returns:
            역할별 멤버 딕셔너리 {역할명: [멤버 목록]}
        """
        result = {}
        
        for member in members:
            # 가장 높은 역할 (표시되는 역할) 기준으로 그룹화
            top_role = member.top_role.name if member.top_role else "No Role"
            
            if top_role not in result:
                result[top_role] = []
            
            result[top_role].append(member)
        
        return result 