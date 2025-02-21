import pytest
from config import Config
import pytz

class TestConfig:
    def test_timezone_setting(self):
        assert Config.Time.TIMEZONE == pytz.timezone('Asia/Seoul')
        
    def test_utc_hour_conversion(self):
        test_cases = [
            (9, 0),   # KST 9시 = UTC 0시
            (0, 15),  # KST 0시 = UTC 15시 (전날)
            (23, 14), # KST 23시 = UTC 14시
            (15, 6),  # KST 15시 = UTC 6시
        ]
        
        for kst_hour, expected_utc in test_cases:
            assert Config.Time.get_utc_hour(kst_hour) == expected_utc 