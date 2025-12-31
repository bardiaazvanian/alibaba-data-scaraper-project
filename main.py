import json
import time
import os
import urllib.parse
from datetime import datetime, timedelta
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
from selenium.common.exceptions import TimeoutException

# --- تنظیمات ---
SHEET_NAME = "Mahan Airlines W5061"
CREDENTIALS_FILE = "google_credentials.json"
TARGET_FLIGHT_DEADLINE = "1404/10/25 - 19:00" 
ALIBABA_URL = "https://www.alibaba.ir/international/search/THRALL-DXBALL?adult=1&child=0&infant=0&departing=1404-10-25&flightClass=economy&airlines[0]=W5&pdm=ODU1Nzc0NTQ2NjA2MjM5Mjk3NC8wZTcwMGRkZi0wODQwLTQ3MzgtYjNiYi04NDk3MjA2MWJlNmY="

def get_tehran_time():
    """زمان دقیق تهران به فرمت آبجکت جدیتی‌تایم"""
    try:
        tehran_tz = pytz.timezone('Asia/Tehran')
        now_tehran = datetime.now(tehran_tz)
        return jdatetime.datetime.fromgregorian(datetime=now_tehran)
    except:
        return jdatetime.datetime.now()

def get_last_run_time_from_sheet():
    """آخرین زمان اجرا رو از شیت میخونه تا تکراری نزنیم"""
    try:
        if not os.path.exists(CREDENTIALS_FILE): return None
        client = gspread.service_account(filename=CREDENTIALS_FILE)
        sheet = client.open(SHEET_NAME).sheet1 
        
        all_values = sheet.get_all_values()
        if len(all_values) < 2: return None # شیت خالیه
        
        last_row = all_values[-1]
        last_time_str = last_row[0] # ستون اول زمانه
        
        # تبدیل متن شیت به زمان قابل فهم
        # فرمت توی شیت: 1404/10/09 - 21:46:32
        last_run_time = jdatetime.datetime.strptime(last_time_str, "%Y/%m/%d - %H:%M:%S")
        return last_run_time
    except Exception as e:
        print(f"⚠️ Could not read last run time from sheet: {e}")
        return None

def check_if_expired(deadline_str):
    try:
        deadline = jdatetime.datetime.strptime(deadline_str, "%Y/%m/%d - %H:%M")
        now_tehran = get_tehran_time().replace(tzinfo=None)
        if now_tehran > deadline:
            print(f"⛔ EXPIRED: {now_tehran} > {deadline}")
            return True
        return False
    except: return False

def save_to_sheet(data):
    try:
        if not os.path.exists(CREDENTIALS_FILE): return
        client = gspread.service_account(filename=CREDENTIALS_FILE)
        sheet = client.open(SHEET_NAME).sheet1 
        sheet.append_row([data['check_time'], data['price']])
        print("✅ Data saved to Google Sheet.")
    except Exception as e:
        print(f"❌ Save Error: {e}")

def get_alibaba_price(target_url):
    print("🔧 Scraper Started...")
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
    
    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.set_page_load_timeout(60)

        # 1. گرفتن قیمت
        driver.get(target_url)
        wait = WebDriverWait(driver, 25)
        selector = ".pdp-card_sidebar .text-secondary-400"
        
        try:
            price_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            driver.execute_script("arguments[0].scrollIntoView();", price_element)
            raw_text = price_element.text
            digits = ''.join([c for c in raw_text if c.isdigit()])
            if digits: return {"price": int(digits)}
        except: return None
    except Exception as e:
        print(f"❌ Scrape Error: {e}")
        return None
    finally:
        if driver: driver.quit()

# --- هسته اصلی و هوشمند شده ---
if __name__ == "__main__":
    print("🚀 Bot Started (Smart Mode)...")
    
    while True:
        print("\n" + "-"*30)
        
        # 1. چک کردن انقضا
        if check_if_expired(TARGET_FLIGHT_DEADLINE):
            print("🛑 Deadline passed. Bye.")
            break 

        # 2. چک کردن آخرین باری که دیتا ثبت شده (مهمترین بخش)
        print("🔍 Checking last entry in Sheet...")
        last_run = get_last_run_time_from_sheet()
        now = get_tehran_time().replace(tzinfo=None) # حذف اطلاعات منطقه زمانی برای مقایسه راحت
        
        should_run = True
        
        if last_run:
            # محاسبه اختلاف زمانی به ثانیه
            diff_seconds = (now - last_run).total_seconds()
            print(f"⏱️ Time since last run: {int(diff_seconds/60)} minutes ({int(diff_seconds)} seconds)")
            
            if diff_seconds < 3500: # اگر کمتر از ۵۸ دقیقه (۳۵۰۰ ثانیه) گذشته
                wait_time = 3660 - diff_seconds # محاسبه کن چقدر مونده تا ۱ ساعت بشه (+ یک دقیقه اضافه)
                print(f"⛔ Too soon! Waiting for {int(wait_time/60)} minutes to maintain 1-hour interval.")
                should_run = False
                time.sleep(wait_time) # بگیر بخواب تا سر ساعت بشه
            else:
                print("✅ More than 1 hour passed. Ready to scrape.")
        
        # 3. اجرا اگر لازم بود
        if should_run:
            now_str = get_tehran_time().strftime("%Y/%m/%d - %H:%M:%S")
            data = get_alibaba_price(ALIBABA_URL)
            
            if data:
                data['check_time'] = now_str
                print(f"💰 Price: {data['price']:,}")
                save_to_sheet(data)
            else:
                print("❌ Price not found.")
            
            # خواب اجباری بعد از انجام کار
            print("💤 Job done. Sleeping for 1 hour...")
            time.sleep(3600)
