import json
import time
import os
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import jdatetime

def get_alibaba_price(target_url):
    print("🔧 Setting up Chrome options for GitHub Actions...")
    chrome_options = Options()
    
    # --- تنظیمات حیاتی برای جلوگیری از کرش روی سرور ---
    chrome_options.add_argument("--headless=new")  # ورژن جدید و پایدار هدلس
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    
    # --- تکنیک‌های آنتی‌دتکشن (جلوگیری از تشخیص ربات) ---
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # User-Agent جدید و واقعی
    chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        
        # مخفی کردن متغیر navigator.webdriver (ترفند حرفه‌ای)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    except Exception as e:
        print(f"❌ Failed to initialize driver: {e}")
        return None

    try:
        # 1. دامنه اصلی و کوکی
        print("🌍 Going to base domain...")
        driver.get("https://www.alibaba.ir")
        
        if os.path.exists('cookies.json'):
            print("🍪 Loading Cookies...")
            try:
                with open('cookies.json', 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                
                # تعداد کوکی‌های لود شده
                count = 0
                for cookie in cookies:
                    if 'alibaba' in cookie.get('domain', ''):
                        cookie_clean = {
                            'name': cookie['name'],
                            'value': cookie['value'],
                            'domain': '.alibaba.ir',
                            'path': '/',
                            # فیلدهای امنیتی رو برای اطمینان حذف میکنیم
                        }
                        try:
                            driver.add_cookie(cookie_clean)
                            count += 1
                        except:
                            pass
                print(f"✅ {count} Cookies injected.")
                driver.refresh()
                time.sleep(2)
            except Exception as e:
                print(f"⚠️ Cookie warning: {e}")
        else:
            print("ℹ️ No cookies found. Running as Guest.")

        # 2. استخراج تاریخ از لینک
        try:
            parsed = urllib.parse.urlparse(target_url)
            flight_date = urllib.parse.parse_qs(parsed.query).get('departing', ['Unknown'])[0]
        except:
            flight_date = "Unknown"

        # 3. باز کردن صفحه پرواز
        print(f"✈️ Checking flight date: {flight_date}")
        driver.get(target_url)

        wait = WebDriverWait(driver, 40) # افزایش زمان انتظار
        
        # سلکتور قیمت
        selector = ".pdp-card_sidebar .text-secondary-400"

        print("⏳ Waiting for price element...")
        price_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        
        # اسکرول برای اطمینان
        driver.execute_script("arguments[0].scrollIntoView();", price_element)
        
        raw_text = price_element.text
        print(f"🔎 Raw text found: {raw_text}")
        
        digits = ''.join([c for c in raw_text if c.isdigit()])
        
        if not digits:
            print("❌ Element found but no digits inside.")
            # برای دیباگ، سورس صفحه رو چاپ میکنیم (میتونی بعدا پاک کنی)
            # print(driver.page_source[:500]) 
            return None
            
        final_price = int(digits)
        return {
            "price": final_price,
            "flight_date": flight_date
        }

    except Exception as e:
        print(f"❌ Error occurred: {e}")
        # اگر کرش کرد سعی میکنیم تایتل صفحه رو بخونیم ببینیم کجا هستیم
        try:
            print(f"Current Page Title: {driver.title}")
        except:
            pass
        return None

    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    # لینک پرواز - تاریخ را چک کن که برای آینده باشد
    url = "https://www.alibaba.ir/international/search/THRALL-DXBALL?adult=1&child=0&infant=0&departing=1403-11-05&flightClass=economy&airlines[0]=W5"
    
    print("🚀 Starting Scraper (v2 Stable)...")
    
    now_shamsi = jdatetime.datetime.now().strftime("%Y/%m/%d - %H:%M:%S")
    
    data = get_alibaba_price(url)
    
    if data:
        print("\n" + "*"*40)
        print(f"✅ SUCCESS")
        print(f"⏰ Run Time   : {now_shamsi}")
        print(f"📅 Flight Date: {data['flight_date']}")
        print(f"💰 Price      : {data['price']:,} Rials")
        print("*"*40 + "\n")
    else:
        print("\n❌ Failed to extract price.\n")
        exit(1)
