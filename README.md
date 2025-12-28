# 주차 위치 조회 시스템

매일 아침 주차 위치를 자동으로 확인하고 Mattermost로 알림을 보내는 시스템입니다. Upstash Redis를 사용하여 주차 정보 변경사항을 추적합니다.

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

# Upstash Redis 설정
UPSTASH_REDIS_URL=your-redis-url.upstash.io:6379
UPSTASH_REDIS_TOKEN=your-redis-token
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
   - `UPSTASH_REDIS_URL`: Upstash Redis URL
   - `UPSTASH_REDIS_TOKEN`: Upstash Redis Token

3. 자동 실행:
   - 매일 오전 7시(한국시간) 자동 실행
   - Actions 탭에서 수동 실행 가능

## Redis 기능

### Upstash Redis 설정

1. [Upstash](https://upstash.com/)에서 Redis 데이터베이스 생성
2. 데이터베이스 대시보드에서 **"Connect"** 탭 클릭
3. **"Redis"** 탭 선택 (REST API가 아닌 Redis 클라이언트 연결 정보)
4. 다음 형식으로 환경변수 설정:

   ```env
   UPSTASH_REDIS_URL=xxx.upstash.io:6379
   UPSTASH_REDIS_TOKEN=your-token-here
   ```

   ⚠️ **주의**: REST API URL(`https://xxx.upstash.io:6379`)이 아닌 **Redis 클라이언트 URL**을 사용하세요!

### Redis 연결 테스트

```bash
# 환경변수 설정 후 테스트
python parking_data.py
```

연결에 성공하면 다음과 같은 메시지가 표시됩니다:

```
✅ Redis 연결 성공
✅ Redis 연결 및 기본 기능 테스트 성공
✅ 모든 테스트 통과!
```

### Redis 기능 설명

- **주차 정보 저장**: 조회된 주차 정보를 Redis에 저장
- **변경사항 추적**: 주차 정보가 변경되면 자동으로 감지
- **중복 알림 방지**: 동일한 정보일 경우 Mattermost 알림 생략
- **변경 이력 관리**: 최근 10개의 변경 이력을 저장

### Redis 연결 테스트

```bash
python parking_data.py
```

## 필요한 환경변수

- `CAR_NUMBER`: 조회할 차량번호
- `PARKING_URL`: 주차 위치 조회 웹페이지 URL
- `MATTERMOST_WEBHOOK_URL`: (선택) Mattermost 알림을 받을 Webhook URL
- `UPSTASH_REDIS_URL`: (선택) Upstash Redis URL
- `UPSTASH_REDIS_TOKEN`: (선택) Upstash Redis Token

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
