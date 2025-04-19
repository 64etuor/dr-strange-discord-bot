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

4. 환경 설정
   - `.env.example`을 복사하여 `.env` 파일 생성
   - `.env` 파일에 필요한 정보 입력
   - 필요한 경우 `config.yaml` 파일 수정

```bash
cp .env.example .env
# .env 파일 편집
```

5. 봇 실행

```bash
python main.py
```

## 설정 구조

이 프로젝트는 두 가지 설정 파일을 사용합니다:

### 1. 환경 변수 (.env)

`.env` 파일에는 민감한 정보를 저장합니다:

```
# 디스코드 봇 토큰
DISCORD_TOKEN=your_bot_token

# 인증 채널 ID
VERIFICATION_CHANNEL_ID=your_channel_id

# 웹훅 URL (선택 사항)
WEBHOOK_URL=your_webhook_url
```

### 2. 일반 설정 (config.yaml)

`config.yaml` 파일에는 봇의 일반적인 설정을 저장합니다:

```yaml
# 봇 기본 설정 (프리픽스, 권한 등)
bot:
  prefix: "!"
  intents:
    message_content: true
    guilds: true
    reactions: true
    members: true

# 인증 체크 시간, 키워드 등의 설정
time:
  timezone: Asia/Seoul
  daily_check_hour: 22
  daily_check_minute: 0

verification:
  keywords:
    - 인증사진
    - 인증 사진

# 메시지 템플릿
messages:
  verification_success: "{name}, Your time has been recorded!"

# 로깅 설정
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: null # 파일로 로그를 저장하려면 경로 지정 (예: 'logs/bot.log')
```

## 주요 설정 항목

### 봇 기본 설정

- `bot.prefix`: 명령어 접두사 (기본값: "!")
- `bot.intents`: 봇 권한 설정

### 시간 설정

- `time.timezone`: 타임존 (기본값: "Asia/Seoul")
- `time.daily_check_hour`: 일일 체크 시간 (시)
- `time.daily_check_minute`: 일일 체크 시간 (분)
- `time.daily_start_hour`: 일일 인증 시작 시간 (시)
- `time.daily_end_hour`: 일일 인증 종료 시간 (시)

### 인증 설정

- `verification.keywords`: 인증 메시지로 인식할 키워드 목록

### 로깅 설정

- `logging.level`: 로그 레벨 (INFO, DEBUG, WARNING, ERROR, CRITICAL)
- `logging.format`: 로그 형식
- `logging.file`: 로그 파일 경로 (null인 경우 콘솔에만 출력)

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
