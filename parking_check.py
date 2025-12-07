#!/usr/bin/env python3
"""
주차 위치 자동 조회 스크립트
매일 아침 주차 위치를 자동으로 확인합니다.
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# .env 파일 로드 (로컬 테스트용, GitHub Actions에서는 환경변수 사용)
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print("✅ .env 파일에서 환경변수 로드")


def setup_driver():
    """Selenium 웹드라이버 설정 (헤드리스 모드)"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--remote-debugging-port=9222')
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def check_parking_location(car_number):
    """
    주차 위치 조회
    
    Args:
        car_number: 차량번호 (4자리 숫자)
    
    Returns:
        dict: 주차 위치 정보
    """
    driver = None
    try:
        driver = setup_driver()
        url = os.getenv("PARKING_URL")
        
        if not url:
            print("❌ PARKING_URL 환경변수가 설정되지 않았습니다.")
            return {
                "car_number": car_number,
                "status": "error",
                "error": "PARKING_URL not set"
            }
        
        print(f"🚗 주차 위치 조회 중... (차량번호: {car_number})")
        driver.get(url)
        
        # 페이지 로딩 대기
        time.sleep(3)
        
        # 페이지 소스 디버깅
        print(f"페이지 타이틀: {driver.title}")
        
        # 입력 필드 찾기 (id=car-number)
        try:
            input_field = driver.find_element(By.ID, "car-number")
            print(f"✅ 입력 필드 발견: id=car-number")
        except Exception as e:
            print(f"❌ 입력 필드 검색 오류: {e}")
            return None
        
        # 차량번호 입력 - 숫자 키패드 클릭 방식
        try:
            # 입력 필드 클릭
            input_field.click()
            time.sleep(0.5)
            
            # 각 숫자를 키패드에서 클릭
            for digit in car_number:
                digit_link = driver.find_element(By.XPATH, f"//a[text()='{digit}']")
                digit_link.click()
                time.sleep(0.3)
            
            print(f"✅ 차량번호 입력 완료: {car_number}")
        except Exception as e:
            print(f"❌ 차량번호 입력 실패: {e}")
            return None
        
        # 검색 버튼 찾기 및 클릭
        try:
            # '검색' 텍스트가 있는 링크(a 태그) 찾기
            search_button = driver.find_element(By.XPATH, "//a[contains(text(), '검색')]")
            search_button.click()
            print("🔍 검색 버튼 클릭")
        except Exception as e:
            print(f"❌ 검색 버튼 클릭 오류: {e}")
            # 스크린샷 저장
            driver.save_screenshot("/tmp/parking_debug.png")
            print("디버그 스크린샷 저장: /tmp/parking_debug.png")
            return None
        
        # 결과 로딩 대기
        time.sleep(3)
        
        # 결과 스크린샷 저장
        screenshot_path = "/tmp/parking_location.png"
        driver.save_screenshot(screenshot_path)
        print(f"📸 스크린샷 저장: {screenshot_path}")
        
        # 주차 위치 정보 추출 (페이지 구조에 따라 조정 필요)
        try:
            # 페이지 전체 텍스트 가져오기
            body_text = driver.find_element(By.TAG_NAME, "body").text
            
            result = {
                "car_number": car_number,
                "status": "found",
                "screenshot": screenshot_path,
                "details": body_text[:500]  # 처음 500자만
            }
            
            print(f"\n📍 주차 위치 조회 결과:")
            print(f"차량번호: {car_number}")
            print(f"상세정보:\n{body_text[:300]}...")
            
            return result
            
        except Exception as e:
            print(f"⚠️  결과 파싱 중 오류: {e}")
            return {
                "car_number": car_number,
                "status": "error",
                "screenshot": screenshot_path,
                "error": str(e)
            }
    
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return {
            "car_number": car_number,
            "status": "error",
            "error": str(e)
        }
    
    finally:
        if driver:
            driver.quit()


def send_to_mattermost(webhook_url, result):
    """
    Mattermost로 메시지 전송
    
    Args:
        webhook_url: Mattermost webhook URL
        result: 주차 위치 조회 결과 딕셔너리
    """
    import requests
    import re
    
    # 주차 정보 파싱
    details = result.get('details', '')
    
    # 정규식으로 정보 추출
    car_number_match = re.search(r'차량번호\s*(\d+)', details)
    entry_time_match = re.search(r'입차시간\s*([\d\-:\s]+)', details)
    parking_floor_match = re.search(r'주차층\s*([^\n]+)', details)
    parking_location_match = re.search(r'차량위치\s*([^\n]+)', details)
    
    car_number = car_number_match.group(1) if car_number_match else result.get('car_number', 'N/A')
    entry_time = entry_time_match.group(1).strip() if entry_time_match else 'N/A'
    parking_floor = parking_floor_match.group(1).strip() if parking_floor_match else 'N/A'
    parking_location = parking_location_match.group(1).strip() if parking_location_match else 'N/A'
    
    # Mattermost 메시지 포맷팅
    message = f"""### 🚗 주차 위치 알림

**차량번호:** {car_number}
**입차시간:** {entry_time}
**주차층:** {parking_floor}
**차량위치:** {parking_location}

---
_자동 알림 - {time.strftime('%Y-%m-%d %H:%M:%S')}_
"""
    
    payload = {
        "text": message
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Mattermost 전송 완료")
            return True
        else:
            print(f"⚠️  Mattermost 전송 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Mattermost 전송 오류: {e}")
        return False


def main():
    """메인 함수"""
    # 환경변수에서 차량번호 읽기
    car_number = os.getenv("CAR_NUMBER")
    
    if not car_number:
        print("❌ 차량번호가 설정되지 않았습니다.")
        print("환경변수 CAR_NUMBER를 설정해주세요.")
        sys.exit(1)
    
    # 주차 위치 조회
    result = check_parking_location(car_number)
    
    if result and result.get('status') == 'found':
        print("\n" + "="*50)
        print("✅ 주차 위치 조회 완료")
        print("="*50)
        
        # Mattermost 전송
        webhook_url = os.getenv("MATTERMOST_WEBHOOK_URL")
        if webhook_url:
            send_to_mattermost(webhook_url, result)
        else:
            print("⚠️  MATTERMOST_WEBHOOK_URL이 설정되지 않아 알림을 전송하지 않습니다.")
    else:
        print("\n❌ 주차 위치 조회 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
