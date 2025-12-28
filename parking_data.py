#!/usr/bin/env python3
"""
주차 데이터 Redis 저장 및 관리 모듈
Upstash Redis를 사용하여 주차 정보를 저장하고 변경사항을 추적합니다.
"""

import os
import json
import redis
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv


# .env 파일 로드 (로컬 테스트용, GitHub Actions에서는 환경변수 사용)
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print("✅ .env 파일에서 환경변수 로드")


class ParkingDataManager:
    """주차 데이터 Redis 관리 클래스"""

    def __init__(self):
        """Redis 연결 초기화"""
        # Upstash Redis 연결 정보
        redis_url = os.getenv('UPSTASH_REDIS_URL')
        redis_token = os.getenv('UPSTASH_REDIS_TOKEN')

        if not redis_url or not redis_token:
            raise ValueError("UPSTASH_REDIS_URL과 UPSTASH_REDIS_TOKEN 환경변수가 필요합니다.")

        # URL 형식 보정 (https:// → redis://, 포트 추가)
        if redis_url.startswith('https://'):
            # REST API URL에서 호스트 추출
            redis_url = redis_url.replace('https://', '')
            print(f"🔄 REST API URL을 Redis 클라이언트 URL로 변환: {redis_url}")

        # 포트 번호가 없으면 기본 Redis 포트(6379) 추가
        if ':' not in redis_url:
            redis_url = f"{redis_url}:6379"
            print(f"🔄 기본 포트 추가: {redis_url}")

        # Redis 연결 URL 구성
        redis_connection_url = f"rediss://default:{redis_token}@{redis_url}"

        try:
            self.redis = redis.from_url(redis_connection_url)
            # 연결 테스트
            self.redis.ping()
            print("✅ Redis 연결 성공")
        except Exception as e:
            error_msg = str(e)
            if "getaddrinfo failed" in error_msg:
                raise ConnectionError(
                    f"Redis 연결 실패: 호스트를 찾을 수 없습니다.\n"
                    f"UPSTASH_REDIS_URL이 올바른지 확인해주세요.\n"
                    f"현재 URL: {redis_url}\n"
                    f"예시: xxx.upstash.io:6379"
                )
        except Exception as e:
            error_msg = str(e)
            if "getaddrinfo failed" in error_msg or "11001" in error_msg:
                raise ConnectionError(
                    f"Redis 연결 실패: 호스트를 찾을 수 없습니다.\n"
                    f"UPSTASH_REDIS_URL이 올바른지 확인해주세요.\n"
                    f"현재 URL: {redis_url}\n"
                    f"예시: xxx.upstash.io:6379"
                )
            elif "Connection closed by server" in error_msg:
                raise ConnectionError(
                    f"Redis 연결 실패: 서버에서 연결을 거부했습니다.\n"
                    f"가능한 원인:\n"
                    f"  - UPSTASH_REDIS_TOKEN이 잘못됨\n"
                    f"  - Redis 데이터베이스가 비활성화됨\n"
                    f"  - 네트워크 정책으로 차단됨\n"
                    f"현재 URL: {redis_url}\n"
                    f"토큰: {redis_token[:10]}... (길이: {len(redis_token)})\n\n"
                    f"🔧 해결 방법:\n"
                    f"1. Upstash 콘솔에서 Redis 데이터베이스가 활성화되어 있는지 확인\n"
                    f"2. 'Connect' → 'Redis' 탭의 연결 정보를 사용\n"
                    f"3. 토큰이 올바른지 재확인"
                )
            else:
                raise ConnectionError(f"Redis 연결 실패: {error_msg}")

    def _get_kst_now(self) -> datetime:
        """한국 시간 현재 시각 반환"""
        kst = timezone(timedelta(hours=9))
        return datetime.now(kst)

    def _generate_key(self, car_number: str) -> str:
        """주차 정보 저장용 Redis 키 생성"""
        return f"parking:{car_number}"

    def _generate_history_key(self, car_number: str) -> str:
        """주차 정보 변경 이력 저장용 Redis 키 생성"""
        return f"parking:history:{car_number}"

    def save_parking_info(self, result: Dict) -> Tuple[bool, str]:
        """
        주차 정보를 Redis에 저장

        Args:
            result: 주차 조회 결과 딕셔너리

        Returns:
            Tuple[bool, str]: (변경여부, 메시지)
        """
        car_number = result.get('car_number')
        if not car_number:
            return False, "차량번호가 없습니다."

        key = self._generate_key(car_number)
        history_key = self._generate_history_key(car_number)

        # 현재 저장된 데이터 조회
        existing_data = self.redis.get(key)
        current_time = self._get_kst_now()

        # 새로운 데이터 구조 생성
        new_data = {
            'car_number': car_number,
            'status': result.get('status', 'unknown'),
            'last_updated': current_time.isoformat(),
            'details': result.get('details', ''),
            'error': result.get('error', ''),
            'screenshot': result.get('screenshot', '')
        }

        # JSON으로 변환
        new_data_json = json.dumps(new_data, ensure_ascii=False)

        # 변경사항 확인
        is_changed = False
        change_message = ""

        if existing_data:
            existing_data_dict = json.loads(existing_data.decode('utf-8'))

            # 주요 필드 비교 (상태, 상세정보, 오류)
            key_fields = ['status', 'details', 'error']
            for field in key_fields:
                if existing_data_dict.get(field) != new_data.get(field):
                    is_changed = True
                    old_value = existing_data_dict.get(field, 'N/A')
                    new_value = new_data.get(field, 'N/A')
                    change_message += f"{field}: '{old_value}' → '{new_value}'\n"
                    break  # 첫 번째 변경사항만 기록
        else:
            is_changed = True
            change_message = "신규 주차 정보 저장"

        # 데이터 저장
        try:
            self.redis.set(key, new_data_json)
            print(f"✅ 주차 정보 저장 완료: {car_number}")

            # 변경사항이 있으면 이력 저장
            if is_changed:
                history_entry = {
                    'timestamp': current_time.isoformat(),
                    'car_number': car_number,
                    'change_type': 'update' if existing_data else 'create',
                    'changes': change_message.strip(),
                    'data': new_data
                }

                # 이력 리스트에 추가 (최근 10개만 유지)
                self.redis.lpush(history_key, json.dumps(history_entry, ensure_ascii=False))
                self.redis.ltrim(history_key, 0, 9)  # 최근 10개만 유지

                print(f"📝 변경 이력 저장: {change_message.strip()}")

            return is_changed, change_message.strip() if change_message else "변경사항 없음"

        except Exception as e:
            error_msg = f"Redis 저장 실패: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def get_parking_info(self, car_number: str) -> Optional[Dict]:
        """
        저장된 주차 정보 조회

        Args:
            car_number: 차량번호

        Returns:
            저장된 주차 정보 딕셔너리 또는 None
        """
        key = self._generate_key(car_number)

        try:
            data = self.redis.get(key)
            if data:
                return json.loads(data.decode('utf-8'))
            return None
        except Exception as e:
            print(f"❌ 주차 정보 조회 실패: {str(e)}")
            return None

    def get_parking_history(self, car_number: str, limit: int = 5) -> list:
        """
        주차 정보 변경 이력 조회

        Args:
            car_number: 차량번호
            limit: 조회할 이력 개수

        Returns:
            변경 이력 리스트
        """
        history_key = self._generate_history_key(car_number)

        try:
            history_data = self.redis.lrange(history_key, 0, limit - 1)
            history = []

            for item in history_data:
                history.append(json.loads(item.decode('utf-8')))

            return history
        except Exception as e:
            print(f"❌ 변경 이력 조회 실패: {str(e)}")
            return []

    def test_connection(self) -> bool:
        """
        Redis 연결 테스트

        Returns:
            연결 성공 여부
        """
        try:
            self.redis.ping()
            # 기본적인 set/get 테스트
            test_key = "test:connection"
            test_value = "OK"
            self.redis.set(test_key, test_value)
            retrieved = self.redis.get(test_key)
            self.redis.delete(test_key)

            if retrieved.decode('utf-8') == test_value:
                print("✅ Redis 연결 및 기본 기능 테스트 성공")
                return True
            else:
                print("❌ Redis 데이터 일관성 테스트 실패")
                return False

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Redis 연결 테스트 실패: {error_msg}")

            if "Connection closed by server" in error_msg:
                print("\n🔧 문제 해결 방법:")
                print("1. Upstash 콘솔에서 Redis 데이터베이스가 활성화되어 있는지 확인")
                print("2. 'Connect' → 'Redis' 탭의 연결 정보를 사용")
                print("3. UPSTASH_REDIS_TOKEN이 올바른지 재확인")
                print("4. Redis 연결이 아닌 REST API 토큰을 사용하지 않았는지 확인")

            return False


def test_redis_connection():
    """Redis 연결 테스트 함수"""
    print("\n🧪 Upstash Redis 연결 테스트")
    print("=" * 50)

    try:
        manager = ParkingDataManager()

        if manager.test_connection():
            print("\n✅ 모든 테스트 통과!")
            print("Redis 서버에 정상적으로 연결할 수 있습니다.")

            # 샘플 데이터로 저장 테스트
            sample_data = {
                'car_number': '1234',
                'status': 'found',
                'details': '테스트 주차 정보',
                'last_updated': datetime.now().isoformat()
            }

            print("\n📝 샘플 데이터 저장 테스트...")
            is_changed, message = manager.save_parking_info(sample_data)
            print(f"저장 결과: {message}")

            # 저장된 데이터 조회 테스트
            print("\n🔍 저장된 데이터 조회 테스트...")
            retrieved = manager.get_parking_info('1234')
            if retrieved:
                print(f"조회 성공: 차량번호 {retrieved['car_number']}")
            else:
                print("❌ 데이터 조회 실패")

            # 이력 조회 테스트
            print("\n📚 변경 이력 조회 테스트...")
            history = manager.get_parking_history('1234', 3)
            print(f"이력 개수: {len(history)}")

        else:
            print("\n❌ 연결 테스트 실패")
            return False

    except ValueError as e:
        print(f"❌ 환경변수 오류: {str(e)}")
        print("다음 환경변수를 설정해주세요:")
        print("- UPSTASH_REDIS_URL")
        print("- UPSTASH_REDIS_TOKEN")
        return False

    except ConnectionError as e:
        print(f"❌ 연결 오류: {str(e)}")
        print("\n🔧 문제 해결 방법:")
        print("1. Upstash 콘솔에서 Redis 데이터베이스가 활성화되어 있는지 확인")
        print("2. UPSTASH_REDIS_TOKEN이 올바른지 확인")
        print("3. Redis 연결이 아닌 REST API 토큰을 사용하지 않았는지 확인")
        print("4. Upstash 대시보드에서 'Connect' → 'Redis' 탭의 정보를 사용")
        return False

    except Exception as e:
        print(f"❌ 예상치 못한 오류: {str(e)}")
        return False

    return True


if __name__ == "__main__":
    test_redis_connection()