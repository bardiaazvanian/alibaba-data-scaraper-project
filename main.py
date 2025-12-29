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
    # --- تنظیمات مخصوص سرور (GitHub Actions) ---
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # برای سرور حتما باید روشن باشه
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    # نصب و راه اندازی درایور
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        # 1. دامنه اصلی و کوکی (اگر فایلش موجود باشد)
        driver.get("https://www.alibaba.ir")
        
        if os.path.exists('cookies.json'):
            print("🍪 Loading Cookies from secret...")
            try:
                with open('cookies.json', 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                for cookie in cookies:
                    if 'alibaba' in cookie.get('domain', ''):
                        cookie_clean = {
                            'name': cookie['name'],
                            'value': cookie['value'],
                            'domain': '.alibaba.ir',
                            'path': '/'
                        }
                        driver.add_cookie(cookie_clean)
                driver.refresh()
                time.sleep(2)
            except Exception as e:
                print(f"⚠️ Cookie warning: {e}")
        else:
            print("ℹ️ No cookies found. Running as Guest.")

        # 2. استخراج تاریخ پرواز از لینک (برای لاگ)
        try:
            parsed = urllib.parse.urlparse(target_url)
            flight_date = urllib.parse.parse_qs(parsed.query).get('departing', ['Unknown'])[0]
        except:
            flight_date = "Unknown"

        # 3. باز کردن صفحه پرواز
        print(f"✈️ Checking flight date: {flight_date}")
        driver.get(target_url)

        wait = WebDriverWait(driver, 30)
        # سلکتور دقیق قیمت
        selector = ".pdp-card_sidebar .text-secondary-400"

        # منتظر میمانیم
        price_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        
        # گرفتن متن
        raw_text = price_element.text
        
        # تمیز کردن عدد
        digits = ''.join([c for c in raw_text if c.isdigit()])
        
        if not digits:
            print("❌ Element found but no digits inside.")
            return None
            
        final_price = int(digits)
        return {
            "price": final_price,
            "flight_date": flight_date
        }

    except Exception as e:
        print(f"❌ Error occurred: {e}")
        return None

    finally:
        driver.quit()

if __name__ == "__main__":
    # لینک پرواز (حتما تاریخ معتبر و آینده باشد)
    # مثال: پرواز برای 5 بهمن 1403
    url = "https://www.alibaba.ir/international/search/THRALL-DXBALL?adult=1&child=0&infant=0&departing=1403-11-05&flightClass=economy&airlines[0]=W5"
    
    print("🚀 Starting Scraper on GitHub Actions...")
    
    # گرفتن زمان شمسی اجرا
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
        exit(1) # این باعث میشه گیت هاب قرمز نشون بده