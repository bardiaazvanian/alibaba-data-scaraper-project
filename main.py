import json
import time
import os
import urllib.parse
from datetime import datetime
import pytz # این برای تنظیم منطقه زمانی لازمه
import jdatetime
import gspread
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException

# --- تنظیمات گوگل شیت ---
SHEET_NAME = "Mahan Airlines W5061"
CREDENTIALS_FILE = "google_credentials.json"

# --- تنظیمات زمانی ---
TARGET_FLIGHT_DEADLINE = "1404/10/25 - 19:00" 

# لینک علی بابا
ALIBABA_URL = "https://www.alibaba.ir/international/search/THRALL-DXBALL?adult=1&child=0&infant=0&departing=1404-10-25&flightClass=economy&airlines[0]=W5&pdm=ODU1Nzc0NTQ2NjA2MjM5Mjk3NC8wZTcwMGRkZi0wODQwLTQ3MzgtYjNiYi04NDk3MjA2MWJlNmY="

def get_tehran_time():
    """زمان فعلی رو به وقت تهران و به صورت آبجکت شمسی برمیگردونه"""
    try:
        # گرفتن زمان دقیق تهران (مهم نیست سرور کجاست)
        tehran_tz = pytz.timezone('Asia/Tehran')
        now_tehran = datetime.now(tehran_tz)
        
        # تبدیل به شمسی
        now_shamsi = jdatetime.datetime.fromgregorian(datetime=now_tehran)
        return now_shamsi
    except Exception as e:
        print(f"⚠️ Timezone Error: {e}")
        return jdatetime.datetime.now() # فال‌بک به ساعت سیستم

def check_if_expired(deadline_str):
    try:
        deadline = jdatetime.datetime.strptime(deadline_str, "%Y/%m/%d - %H:%M")
        
        # استفاده از ساعت تهران برای مقایسه
        # نکته: برای مقایسه دقیق، اطلاعات منطقه زمانی رو حذف میکنیم (naive) تا با ددلاین که اونم naive هست سازگار باشه
        now_tehran = get_tehran_time().replace(tzinfo=None)
        
        if now_tehran > deadline:
            print(f"⛔ EXPIRED: Tehran time ({now_tehran}) is past deadline.")
            return True
        return False
    except Exception as e:
        print(f"⚠️ Date Check Error: {e}")
        return False

def save_to_sheet(data):
    print("📊 Saving to Google Sheets...")
    try:
        if not os.path.exists(CREDENTIALS_FILE): return
        client = gspread.service_account(filename=CREDENTIALS_FILE)
        sheet = client.open(SHEET_NAME).sheet1 
        sheet.append_row([data['check_time'], data['price']])
        print("✅ Saved!")
    except Exception as e:
        print(f"❌ Sheet Error: {e}")

def get_alibaba_price(target_url):
    print("🔧 Setting up Chrome (Fast Mode)...")
    chrome_options = Options()
    chrome_options.page_load_strategy = 'eager' 
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.set_page_load_timeout(60)

        # 1. کوکی‌ها
        try:
            driver.get("https://www.alibaba.ir")
            if os.path.exists('cookies.json'):
                with open('cookies.json', 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                for cookie in cookies:
                    if 'alibaba' in cookie.get('domain', ''):
                        try: driver.add_cookie({'name': cookie['name'], 'value': cookie['value'], 'domain': '.alibaba.ir', 'path': '/'})
                        except: pass
                driver.refresh()
        except: pass

        # 2. گرفتن قیمت
        print(f"✈️ Navigating to Flight Page...")
        driver.get(target_url)
        
        wait = WebDriverWait(driver, 20)
        selector = ".pdp-card_sidebar .text-secondary-400"
        
        try:
            price_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            driver.execute_script("arguments[0].scrollIntoView();", price_element)
            
            raw_text = price_element.text
            digits = ''.join([c for c in raw_text if c.isdigit()])
            
            if digits:
                return {"price": int(digits)}
            
        except TimeoutException:
            print("⚠️ Timeout: Price element not found within 20s.")
            return None

    except Exception as e:
        print(f"❌ Scrape Error: {e}")
        return None
    finally:
        if driver: driver.quit()

if __name__ == "__main__":
    print("🚀 Starting Bot Loop...")
    
    while True:
        print("\n" + "="*40)
        
        if check_if_expired(TARGET_FLIGHT_DEADLINE):
            print("🛑 Deadline passed. Exiting.")
            break 
            
        # محاسبه دقیق زمان شمسی به وقت تهران برای ثبت در شیت
        now_shamsi_str = get_tehran_time().strftime("%Y/%m/%d - %H:%M:%S")

        data = get_alibaba_price(ALIBABA_URL)
        
        if data:
            data['check_time'] = now_shamsi_str
            print(f"✅ Price Found: {data['price']:,} (Time: {now_shamsi_str})")
            save_to_sheet(data)
        else:
            print("❌ No price found.")
        
        print("💤 Sleeping for 1 hour...")
        time.sleep(3600)
