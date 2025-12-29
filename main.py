import json
import time
import os
import urllib.parse
from datetime import datetime # این رو اضافه کردم
import pytz # این رو اضافه کردم (برای تایم زون تهران)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import jdatetime

def get_alibaba_price(target_url):
    print("🔧 Setting up Chrome options (Logged-in Mode)...")
    chrome_options = Options()
    
    # --- تنظیمات سرور ---
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

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    except Exception as e:
        print(f"❌ Driver Init Failed: {e}")
        return None

    try:
        # 1. دامنه اصلی و کوکی
        print("🌍 Going to base domain to inject cookies...")
        driver.get("https://www.alibaba.ir")
        
        if os.path.exists('cookies.json'):
            print("🍪 Loading Cookies...")
            try:
                with open('cookies.json', 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                
                injected_count = 0
                for cookie in cookies:
                    if 'alibaba' in cookie.get('domain', ''):
                        cookie_clean = {
                            'name': cookie['name'],
                            'value': cookie['value'],
                            'domain': '.alibaba.ir',
                            'path': '/',
                        }
                        try:
                            driver.add_cookie(cookie_clean)
                            injected_count += 1
                        except:
                            pass
                
                print(f"✅ {injected_count} Cookies injected.")
                driver.refresh()
                time.sleep(3)
                
            except Exception as e:
                print(f"⚠️ Cookie Error: {e}")
        else:
            print("⚠️ CRITICAL: No cookies.json found!")

        # 2. استخراج تاریخ از لینک
        try:
            parsed = urllib.parse.urlparse(target_url)
            flight_date = urllib.parse.parse_qs(parsed.query).get('departing', ['Unknown'])[0]
        except:
            flight_date = "Unknown"

        # 3. رفتن به لینک پرواز
        print(f"✈️ Navigating to flight: {flight_date}")
        driver.get(target_url)
        print(f"📍 Page Title: {driver.title}")

        wait = WebDriverWait(driver, 45)
        selector = ".pdp-card_sidebar .text-secondary-400"

        print("⏳ Waiting for price...")
        try:
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "available-flights")))
        except:
            print("⚠️ 'Available flights' container not found, checking for price directly...")

        price_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        
        driver.execute_script("arguments[0].scrollIntoView();", price_element)
        
        raw_text = price_element.text
        print(f"🔎 Found text: {raw_text}")
        
        digits = ''.join([c for c in raw_text if c.isdigit()])
        
        if not digits:
            print("❌ Price element found but empty.")
            return None
            
        final_price = int(digits)
        return {
            "price": final_price,
            "flight_date": flight_date
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    # لینک پرواز
    url = "https://www.alibaba.ir/international/search/THRALL-DXBALL?adult=1&child=0&infant=0&departing=1404-10-25&flightClass=economy&airlines[0]=W5"
    
    print("🚀 Starting Logged-in Scraper...")
    
    # --- اصلاح زمان به وقت تهران ---
    try:
        # تنظیم منطقه زمانی تهران
        tehran_tz = pytz.timezone('Asia/Tehran')
        # گرفتن زمان حال با تنظیمات تهران
        now_tehran = datetime.now(tehran_tz)
        # تبدیل به شمسی
        now_shamsi = jdatetime.datetime.fromgregorian(datetime=now_tehran).strftime("%Y/%m/%d - %H:%M:%S")
    except Exception as e:
        # اگر کتابخانه pytz نبود، همون UTC رو بزنه که ارور نده
        print(f"Timezone Error: {e}")
        now_shamsi = jdatetime.datetime.now().strftime("%Y/%m/%d - %H:%M:%S")
    
    data = get_alibaba_price(url)
    
    if data:
        print("\n" + "*"*40)
        print(f"✅ SUCCESS")
        print(f"⏰ Tehran Time: {now_shamsi}")
        print(f"💰 Price      : {data['price']:,} Rials")
        print("*"*40 + "\n")
    else:
        print("\n❌ Failed.\n")
        exit(1)
