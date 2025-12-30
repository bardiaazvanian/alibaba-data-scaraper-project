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


# ===================== CONFIG =====================

SHEET_NAME = "Mahan Airlines W5061"
CREDENTIALS_FILE = "google_credentials.json"

CHECK_INTERVAL_SECONDS = 3600  # هر ۱ ساعت

# ⏰ تاریخ و ساعت پرواز (شمسی)
FLIGHT_DATETIME_SHAMSI = "1404-10-25 18:30"

URL = "https://www.alibaba.ir/international/search/THRALL-DXBALL?adult=1&child=0&infant=0&departing=1404-10-25&flightClass=economy&airlines[0]=W5&pdm=ODU1Nzc0NTQ2NjA2MjM5Mjk3NC8wZTcwMGRkZi0wODQwLTQ3MzgtYjNiYi04NDk3MjA2MWJlNmY="


# ===================== UTILS =====================

def shamsi_to_gregorian(shamsi_str):
    jdt = jdatetime.datetime.strptime(shamsi_str, "%Y-%m-%d %H:%M")
    return jdt.togregorian()


def get_now_shamsi(tehran_time):
    return jdatetime.datetime.fromgregorian(
        datetime=tehran_time
    ).strftime("%Y/%m/%d - %H:%M:%S")


# ===================== GOOGLE SHEET =====================

def save_to_sheet(data):
    try:
        client = gspread.service_account(filename=CREDENTIALS_FILE)
        sheet = client.open(SHEET_NAME).sheet1

        row = [
            data["check_time"],
            data["price"]
        ]

        sheet.append_row(row)
        print("✅ Saved to Google Sheet")

    except Exception as e:
        print(f"❌ Sheet Error: {e}")


# ===================== SCRAPER =====================

def get_alibaba_price(target_url):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    driver = None

    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

        driver.get("https://www.alibaba.ir")

        if os.path.exists("cookies.json"):
            with open("cookies.json", "r", encoding="utf-8") as f:
                cookies = json.load(f)

            for cookie in cookies:
                if "alibaba" in cookie.get("domain", ""):
                    try:
                        driver.add_cookie({
                            "name": cookie["name"],
                            "value": cookie["value"],
                            "domain": ".alibaba.ir",
                            "path": "/"
                        })
                    except:
                        pass

            driver.refresh()
            time.sleep(3)

        driver.get(target_url)

        wait = WebDriverWait(driver, 45)
        selector = ".pdp-card_sidebar .text-secondary-400"

        price_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )

        raw_text = price_element.text
        digits = "".join(c for c in raw_text if c.isdigit())

        if not digits:
            return None

        return int(digits)

    except Exception as e:
        print(f"❌ Scrape Error: {e}")
        return None

    finally:
        if driver:
            driver.quit()


# ===================== MAIN LOOP =====================

if __name__ == "__main__":

    tehran_tz = pytz.timezone("Asia/Tehran")
    flight_time = shamsi_to_gregorian(FLIGHT_DATETIME_SHAMSI)
    flight_time = tehran_tz.localize(flight_time)

    print("🚀 Flight Price Monitor Started")
    print(f"✈️ Flight Time: {FLIGHT_DATETIME_SHAMSI}")

    while True:
        now_tehran = datetime.now(tehran_tz)

        # ⛔ توقف کامل بعد از ساعت پرواز
        if now_tehran >= flight_time:
            print("⛔ Flight time passed. Bot stopped.")
            break

        now_shamsi = get_now_shamsi(now_tehran)
        print(f"\n⏳ Checking price at {now_shamsi}")

        price = get_alibaba_price(URL)

        if price:
            print(f"✅ Price: {price:,}")

            data = {
                "check_time": now_shamsi,
                "price": price
            }

            save_to_sheet(data)

        else:
            print("❌ Price not found")

        print("😴 Sleeping...\n")
        time.sleep(CHECK_INTERVAL_SECONDS)
