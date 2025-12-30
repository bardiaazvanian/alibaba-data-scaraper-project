import json
import time
import os
import urllib.parse
from datetime import datetime
import pytz
import jdatetime
import gspread
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- تنظیمات گوگل شیت ---
SHEET_NAME = "Mahan Airlines W5061"
CREDENTIALS_FILE = "google_credentials.json"

# --- تنظیمات زمانی (بخش جدید) ---
# فرمت باید دقیقاً اینطوری باشه: "ساعت:دقیقه - روز/ماه/سال"
# مثال: "1404/10/25 - 14:30" (یعنی ساعت ۲ و نیم ظهر روز ۲۵ دی)
TARGET_FLIGHT_DEADLINE = "1404/10/25 - 19:00" 

# لینک علی بابا
ALIBABA_URL = "https://www.alibaba.ir/international/search/THRALL-DXBALL?adult=1&child=0&infant=0&departing=1404-10-25&flightClass=economy&airlines[0]=W5&pdm=ODU1Nzc0NTQ2NjA2MjM5Mjk3NC8wZTcwMGRkZi0wODQwLTQ3MzgtYjNiYi04NDk3MjA2MWJlNmY="

def check_if_expired(deadline_str):
    """چک میکنه ببینه از زمان پرواز گذشته یا نه"""
    try:
        # تبدیل رشته ورودی به آبجکت زمانی
        deadline = jdatetime.datetime.strptime(deadline_str, "%Y/%m/%d - %H:%M")
        
        # زمان فعلی سیستم (به شمسی)
        now = jdatetime.datetime.now()
        
        # مقایسه
        if now > deadline:
            print(f"⛔ EXPIRED: Current time ({now}) is past the deadline ({deadline}).")
            return True # یعنی منقضی شده
        else:
            time_left = deadline - now
            print(f"⏳ Time remaining: {time_left}")
            return False # هنوز وقت هست
            
    except Exception as e:
        print(f"⚠️ Error checking date: {e}")
        # اگه فرمت رو اشتباه زده باشی، فرض میکنیم منقضی نشده که برنامه کرش نکنه
        return False

def save_to_sheet(data):
    print("📊 Connecting to Google Sheets...")
    try:
        if not os.path.exists(CREDENTIALS_FILE):
            print("❌ Google Credentials file not found!")
            return

        client = gspread.service_account(filename=CREDENTIALS_FILE)
        sheet = client.open(SHEET_NAME).sheet1 
        
        row = [
            data['check_time'],
            data['price']
        ]
        
        sheet.append_row(row)
        print("✅ Data saved to Google Sheet successfully!")
        
    except Exception as e:
        print(f"❌ Error saving to Sheet: {e}")

def get_alibaba_price(target_url):
    print("🔧 Setting up Chrome options...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        
        # 1. کوکی‌ها
        driver.get("https://www.alibaba.ir")
        if os.path.exists('cookies.json'):
            try:
                with open('cookies.json', 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                for cookie in cookies:
                    if 'alibaba' in cookie.get('domain', ''):
                        cookie_clean = {'name': cookie['name'], 'value': cookie['value'], 'domain': '.alibaba.ir', 'path': '/'}
                        try: driver.add_cookie(cookie_clean)
                        except: pass
                driver.refresh()
                time.sleep(3)
            except: pass

        # 2. گرفتن قیمت
        print(f"✈️ Navigating to URL...")
        driver.get(target_url)
        
        wait = WebDriverWait(driver, 45)
        selector = ".pdp-card_sidebar .text-secondary-400"
        
        try:
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "available-flights")))
        except: 
            print("⚠️ Flights container not found, trying direct price...")

        price_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        driver.execute_script("arguments[0].scrollIntoView();", price_element)
        
        raw_text = price_element.text
        digits = ''.join([c for c in raw_text if c.isdigit()])
        
        if not digits: return None
        
        final_price = int(digits)
        return {"price": final_price}

    except Exception as e:
        print(f"❌ Scrape Error: {e}")
        return None
    finally:
        if driver: driver.quit()

# --- شروع برنامه اصلی ---
if __name__ == "__main__":
    print("🚀 Starting Bot Loop...")
    
    while True: # <--- این حلقه باعث میشه برنامه هیچوقت بسته نشه
        print("\n" + "="*50)
        
        # 1. چک کردن تاریخ انقضا
        if check_if_expired(TARGET_FLIGHT_DEADLINE):
            print("🛑 Flight deadline passed. Stopping the bot permanently.")
            break # شکستن حلقه و خروج کامل از برنامه
            
        # 2. تنظیم ساعت برای لاگ
        try:
            now_shamsi = jdatetime.datetime.now().strftime("%Y/%m/%d - %H:%M:%S")
        except:
            now_shamsi = "Unknown Time"

        # 3. اجرای اسکرپت
        data = get_alibaba_price(ALIBABA_URL)
        
        if data:
            data['check_time'] = now_shamsi
            print(f"✅ Price Found: {data['price']:,} Toman")
            save_to_sheet(data)
        else:
            print("❌ Failed to find price this round.")
        
        print("💤 Sleeping for 1 hour...")
        print("="*50 + "\n")
        
        # 4. صبر کردن به مدت یک ساعت (۳۶۰۰ ثانیه)
        time.sleep(3600)
