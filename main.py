import json
import time
import os
import urllib.parse
from datetime import datetime
import pytz
import jdatetime
import gspread # کتابخانه شیت
from oauth2client.service_account import ServiceAccountCredentials # کتابخانه احراز هویت
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- تنظیمات گوگل شیت ---
SHEET_NAME = "FlightPrices" # <--- اسم دقیق فایل گوگل شیتت رو اینجا بنویس
CREDENTIALS_FILE = "google_credentials.json"

def save_to_sheet(data):
    """ذخیره دیتا در گوگل شیت"""
    print("📊 Connecting to Google Sheets...")
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        if not os.path.exists(CREDENTIALS_FILE):
            print("❌ Google Credentials file not found!")
            return

        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        
        # باز کردن شیت
        sheet = client.open(SHEET_NAME).sheet1 # شیت اول
        
        # --- تغییرات درخواستی شما اینجا اعمال شد ---
        # فقط دو ستون: تاریخ چک کردن و قیمت
        row = [
            data['check_time'],  # ستون اول: زمان چک کردن (شمسی)
            data['price']        # ستون دوم: مبلغ
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
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-extensions")
    
    # آنتی‌دتکشن
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        
        # 1. کوکی‌ها
        print("🌍 Injecting cookies...")
        driver.get("https://www.alibaba.ir")
        if os.path.exists('cookies.json'):
            try:
                with open('cookies.json', 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                count = 0
                for cookie in cookies:
                    if 'alibaba' in cookie.get('domain', ''):
                        cookie_clean = {'name': cookie['name'], 'value': cookie['value'], 'domain': '.alibaba.ir', 'path': '/'}
                        try:
                            driver.add_cookie(cookie_clean)
                            count += 1
                        except: pass
                print(f"✅ {count} cookies injected.")
                driver.refresh()
                time.sleep(3)
            except: pass

        # 2. تاریخ پرواز (فقط برای لاگ کردن استفاده میشه ولی در شیت ذخیره نمیشه)
        try:
            parsed = urllib.parse.urlparse(target_url)
            flight_date = urllib.parse.parse_qs(parsed.query).get('departing', ['Unknown'])[0]
        except:
            flight_date = "Unknown"

        # 3. گرفتن قیمت
        print(f"✈️ Navigating to flight: {flight_date}")
        driver.get(target_url)
        
        wait = WebDriverWait(driver, 45)
        # تلاش برای پیدا کردن قیمت
        selector = ".pdp-card_sidebar .text-secondary-400"
        
        try:
            # چک کردن لود شدن کلی
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "available-flights")))
        except: 
            print("⚠️ Flights container not found, trying direct price...")

        price_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        driver.execute_script("arguments[0].scrollIntoView();", price_element)
        
        raw_text = price_element.text
        digits = ''.join([c for c in raw_text if c.isdigit()])
        
        if not digits: return None
        
        final_price = int(digits)
        return {"price": final_price, "flight_date": flight_date}

    except Exception as e:
        print(f"❌ Scrape Error: {e}")
        return None
    finally:
        if driver: driver.quit()

if __name__ == "__main__":
    url = "https://www.alibaba.ir/international/search/THRALL-DXBALL?adult=1&child=0&infant=0&departing=1404-10-25&flightClass=economy&airlines[0]=W5&pdm=ODU1Nzc0NTQ2NjA2MjM5Mjk3NC8wZTcwMGRkZi0wODQwLTQ3MzgtYjNiYi04NDk3MjA2MWJlNmY=
"
    
    print("🚀 Starting Bot...")
    
    # ساعت تهران
    try:
        tehran_tz = pytz.timezone('Asia/Tehran')
        now_tehran = datetime.now(tehran_tz)
        now_shamsi = jdatetime.datetime.fromgregorian(datetime=now_tehran).strftime("%Y/%m/%d - %H:%M:%S")
    except:
        now_shamsi = jdatetime.datetime.now().strftime("%Y/%m/%d - %H:%M:%S")

    data = get_alibaba_price(url)
    
    if data:
        # اضافه کردن ساعت به پکیج دیتا
        data['check_time'] = now_shamsi
        
        print("\n" + "*"*40)
        print(f"✅ Price Found: {data['price']:,}")
        print("*"*40 + "\n")
        
        # ذخیره در گوگل شیت
        save_to_sheet(data)
    else:
        print("❌ Failed.")
        exit(1)
