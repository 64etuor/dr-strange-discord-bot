import pytest
from utils import MessageUtils
from config import Config

class TestMessageUtils:
    def test_chunk_mentions(self):
        class MockMember:
            def __init__(self, id):
                self.mention = f"<@{id}>"
        
        # 테스트 데이터 준비
        members = [MockMember(i) for i in range(100)]
        chunks = MessageUtils.chunk_mentions(members)
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert len(chunk) <= Config.MAX_MESSAGE_LENGTH
            
    def test_empty_members_list(self):
        chunks = MessageUtils.chunk_mentions([])
        assert len(chunks) == 0
        
    def test_single_member(self):
        class MockMember:
            def __init__(self):
                self.mention = "<@123456789>"
                
        chunks = MessageUtils.chunk_mentions([MockMember()])
        assert len(chunks) == 1
        assert "<@123456789>" in chunks[0] 