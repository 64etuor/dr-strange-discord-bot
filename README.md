# Discord 인증 봇

Discord 서버의 일일 인증을 관리하는 봇입니다.

## 주요 기능

- 일일 인증 체크 및 알림
- 전일 미인증자 체크
- 주말/공휴일 자동 스킵
- 인증 이미지 자동 저장
- 관리자 전용 명령어

## 설치 방법

1. 저장소 클론

```bash
git clone https://github.com/yourusername/discord-bot-strange.git
cd discord-bot-strange
```

2. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 의존성 설치

```bash
pip install -r requirements.txt
```

4. 환경 변수 설정
   `.env` 파일을 생성하고 다음 내용을 입력:

```
DISCORD_TOKEN=your_bot_token
VERIFICATION_CHANNEL_ID=your_channel_id
WEBHOOK_URL=your_webhook_url
```

5. 봇 실행

```bash
python main.py
```

## 설정

`config.yaml` 파일에서 다음 설정을 변경할 수 있습니다:

- 인증 체크 시간
- 인증 키워드
- 메시지 템플릿
- 공휴일 설정

## 명령어

- `!check_now`: 즉시 인증 체크 실행
- `!time_check`: 현재 봇 시간 확인
- `!next_check`: 다음 체크 시간 확인
- `!check_settings`: 현재 설정 확인
- `!check_holidays`: 공휴일 정보 확인
- `!status`: 봇 상태 확인

## 개발

테스트 실행:

```bash
pytest
```

## 라이선스

MIT License
