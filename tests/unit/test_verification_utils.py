import pytest
from utils import VerificationUtils
from config import Config

class TestVerificationUtils:
    @pytest.fixture
    def mock_attachment(self):
        class MockAttachment:
            def __init__(self, content_type, size):
                self.content_type = content_type
                self.size = size
        return MockAttachment
        
    def test_is_valid_image(self, mock_attachment):
        # 유효한 이미지 테스트
        valid_cases = [
            ("image/jpeg", 1024 * 1024),
            ("image/png", 100),
            ("image/gif", Config.MAX_ATTACHMENT_SIZE)
        ]
        
        for content_type, size in valid_cases:
            attachment = mock_attachment(content_type, size)
            assert VerificationUtils.is_valid_image(attachment)
            
        # 유효하지 않은 케이스 테스트
        invalid_cases = [
            ("video/mp4", 1024),
            ("image/jpeg", Config.MAX_ATTACHMENT_SIZE + 1),
            (None, 1024),
            ("text/plain", 100)
        ]
        
        for content_type, size in invalid_cases:
            attachment = mock_attachment(content_type, size)
            assert not VerificationUtils.is_valid_image(attachment)

    def test_is_verification_message(self):
        valid_messages = [
            "인증사진 입니다",
            "오늘의 인증 사진",
            "인증사진!",
            "   인증사진   ",  # 공백 테스트
            "인증 사진과 함께하는 오늘"
        ]
        
        invalid_messages = [
            "안녕하세요",
            "오늘 날씨가 좋네요",
            "사진",
            "",  # 빈 문자열
            "   ",  # 공백만 있는 경우
            "인증해주세요"
        ]
        
        for msg in valid_messages:
            assert VerificationUtils.is_verification_message(msg)
        
        for msg in invalid_messages:
            assert not VerificationUtils.is_verification_message(msg) 