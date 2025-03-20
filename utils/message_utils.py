"""
메시지 처리 유틸리티 모듈
"""
import discord
from typing import List

class MessageUtility:
    """메시지 관련 유틸리티 클래스"""
    
    def __init__(self, config):
        self.config = config
    
    def is_verification_message(self, content: str) -> bool:
        """인증 메시지인지 확인"""
        return any(keyword in content for keyword in self.config.VERIFICATION_KEYWORDS)
    
    def is_valid_image(self, attachment: discord.Attachment) -> bool:
        """유효한 이미지인지 확인"""
        return (attachment.content_type and 
                attachment.content_type.startswith('image/') and 
                attachment.size <= self.config.MAX_ATTACHMENT_SIZE)
    
    def chunk_mentions(self, members: List[discord.Member]) -> List[str]:
        """멤버 멘션을 Discord 메시지 길이 제한에 맞게 청크로 분할"""
        chunks = []
        current_chunk = []
        current_length = 0
        
        for member in members:
            mention = member.mention
            if current_length + len(mention) + 1 > self.config.MAX_MESSAGE_LENGTH:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0
            current_chunk.append(mention)
            current_length += len(mention) + 1
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks 