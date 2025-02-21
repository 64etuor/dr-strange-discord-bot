import logging
from typing import List, Set, Tuple
import discord
from config import Config, Messages
import datetime

logger = logging.getLogger(__name__)

class MessageUtils:
    @staticmethod
    def chunk_mentions(members: List[discord.Member]) -> List[str]:
        """
        멤버 멘션을 Discord 메시지 길이 제한에 맞게 청크로 분할
        """
        chunks = []
        current_chunk = []
        current_length = 0
        
        for member in members:
            mention = member.mention
            if current_length + len(mention) + 1 > Config.MAX_MESSAGE_LENGTH:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0
            current_chunk.append(mention)
            current_length += len(mention) + 1
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks

class VerificationUtils:
    @staticmethod
    def is_valid_image(attachment: discord.Attachment) -> bool:
        """
        첨부 파일이 유효한 이미지인지 확인
        """
        return (attachment.content_type and 
                attachment.content_type.startswith('image/') and 
                attachment.size <= Config.MAX_ATTACHMENT_SIZE)

    @staticmethod
    def is_verification_message(content: str) -> bool:
        """
        메시지가 인증 메시지인지 확인
        """
        return any(keyword in content for keyword in Config.VERIFICATION_KEYWORDS)

    @staticmethod
    async def get_unverified_members(
        channel: discord.TextChannel,
        after: datetime,
        before: datetime
    ) -> Tuple[Set[int], List[discord.Member]]:
        """
        지정된 기간 동안 인증하지 않은 멤버 목록 반환
        """
        verified_users: Set[int] = set()
        unverified_members = []

        try:
            async for message in channel.history(
                after=after,
                before=before,
                limit=Config.MESSAGE_HISTORY_LIMIT
            ):
                if (VerificationUtils.is_verification_message(message.content) and 
                    message.attachments):
                    verified_users.add(message.author.id)

            async for member in channel.guild.fetch_members():
                if not member.bot and member.id not in verified_users:
                    unverified_members.append(member)

        except discord.Forbidden:
            logger.error("Missing required permissions")
        except discord.HTTPException as e:
            logger.error(f"Error while fetching messages/members: {e}")

        return verified_users, unverified_members