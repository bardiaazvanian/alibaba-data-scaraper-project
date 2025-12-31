import os
import pytz
import jdatetime
import gspread
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ---------------- CONFIG ----------------
SHEET_NAME = "Mahan Airlines W5061"
CREDENTIALS_FILE = "google_credentials.json"
TARGET_FLIGHT_DEADLINE = "1404/10/25 - 19:00"
ALIBABA_URL = "https://www.alibaba.ir/international/search/THRALL-DXBALL?adult=1&child=0&infant=0&departing=1404-10-25&flightClass=economy&airlines[0]=W5&pdm=ODU1Nzc0NTQ2NjA2MjM5Mjk3NC8wZTcwMGRkZi0wODQwLTQ3MzgtYjNiYi04NDk3MjA2MWJlNmY="
MIN_INTERVAL_SECONDS = 3600  # 1 hour
# ----------------------------------------


def get_tehran_time():
    tehran_tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tehran_tz)
    return jdatetime.datetime.fromgregorian(datetime=now)


def check_if_expired(deadline_str):
    deadline = jdatetime.datetime.strptime(deadline_str, "%Y/%m/%d - %H:%M")
    return get_tehran_time().replace(tzinfo=None) > deadline


def get_last_run_time_from_sheet():
    try:
        if not os.path.exists(CREDENTIALS_FILE):
            return None

        client = gspread.service_account(filename=CREDENTIALS_FILE)
        sheet = client.open(SHEET_NAME).sheet1
        rows = sheet.get_all_values()

        if len(rows) < 2:
            return None

        last_time_str = rows[-1][0]
        return jdatetime.datetime.strptime(last_time_str, "%Y/%m/%d - %H:%M:%S")

    except Exception as e:
        print(f"⚠️ Sheet read error: {e}")
        return None


def save_to_sheet(data):
    try:
        client = gspread.service_account(filename=CREDENTIALS_FILE)
        sheet = client.open(SHEET_NAME).sheet1
        sheet.append_row([data["check_time"], data["price"]])
        print("✅ Data saved to Google Sheet.")
    except Exception as e:
        print(f"❌ Save error: {e}")


def get_alibaba_price(target_url):
    print("🔧 Scraper Started...")

    chrome_options = Options()
    chrome_options.page_load_strategy = "eager"
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
        driver.set_page_load_timeout(60)

        driver.get(target_url)
        wait = WebDriverWait(driver, 30)
        selector = ".pdp-card_sidebar .text-secondary-400"

        price_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )

        driver.execute_script("arguments[0].scrollIntoView();", price_element)
        raw_text = price_element.text
        digits = "".join(c for c in raw_text if c.isdigit())

        if digits:
            return {"price": int(digits)}

        return None

    except Exception as e:
        print(f"❌ Scrape error: {e}")
        return None

    finally:
        if driver:
            driver.quit()


# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("🚀 Alibaba Flight Tracker | Single Run Mode")

    # 1. Deadline check
    if check_if_expired(TARGET_FLIGHT_DEADLINE):
        print("⛔ Deadline passed. Exit.")
        exit(0)

    # 2. Deduplication check
    last_run = get_last_run_time_from_sheet()
    now = get_tehran_time().replace(tzinfo=None)

    if last_run:
        diff_seconds = (now - last_run).total_seconds()
        print(f"⏱️ Time since last run: {int(diff_seconds / 60)} minutes")

        if diff_seconds < MIN_INTERVAL_SECONDS:
            print("⛔ Less than 1 hour passed. Skipping.")
            exit(0)

    # 3. Scrape
    data = get_alibaba_price(ALIBABA_URL)
    if not data:
        print("❌ Price not found.")
        exit(1)

    # 4. Save
    data["check_time"] = now.strftime("%Y/%m/%d - %H:%M:%S")
    print(f"💰 Price: {data['price']:,}")
    save_to_sheet(data)

    print("✅ Job finished successfully.")
