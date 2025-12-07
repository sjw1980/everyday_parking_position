# 주차 위치 자동 조회

매일 아침 주차 위치를 자동으로 확인하고 Mattermost로 알림을 보내는 스크립트입니다.

## 설정 방법

### 1. 로컬 테스트

1. `.env` 파일 생성:

```bash
cp .env.example .env
```

2. `.env` 파일 수정:

```env
CAR_NUMBER=1234
PARKING_URL=https://example.com/parking
MATTERMOST_WEBHOOK_URL=https://mattermost.example.com/hooks/xxx
```

3. 의존성 설치:

```bash
pip install -r requirements.txt
```

4. 스크립트 실행:

```bash
python parking_check.py
```

### 2. GitHub Actions 설정

1. GitHub Repository Settings > Secrets and variables > Actions로 이동

2. 다음 Secrets 추가:

   - `CAR_NUMBER`: 차량번호 (4자리)
   - `PARKING_URL`: 주차 조회 URL
   - `MATTERMOST_WEBHOOK_URL`: Mattermost Webhook URL

3. 자동 실행:
   - 매일 오전 9시(한국시간) 자동 실행
   - Actions 탭에서 수동 실행 가능

## 필요한 환경변수

- `CAR_NUMBER`: 조회할 차량번호
- `PARKING_URL`: 주차 위치 조회 웹페이지 URL
- `MATTERMOST_WEBHOOK_URL`: (선택) Mattermost 알림을 받을 Webhook URL

## 스크립트 구조

- `parking_check.py`: 메인 스크립트
- `.env`: 로컬 테스트용 환경변수 (gitignore됨)
- `.env.example`: 환경변수 템플릿
- `requirements.txt`: Python 의존성
- `.github/workflows/parking-check.yml`: GitHub Actions 워크플로우
