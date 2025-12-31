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

def get_last_run_time():
    if not os.path.exists(CREDENTIALS_FILE):
        return None

    client = gspread.service_account(filename=CREDENTIALS_FILE)
    sheet = client.open(SHEET_NAME).sheet1
    rows = sheet.get_all_values()

    if len(rows) < 2:
        return None

    last_time_str = rows[-1][0]
    return jdatetime.datetime.strptime(last_time_str, "%Y/%m/%d - %H:%M:%S")

def should_save(last_run, now):
    if not last_run:
        return True
    diff = (now - last_run).total_seconds()
    return diff >= MIN_INTERVAL_SECONDS

def save_to_sheet(time_str, price):
    client = gspread.service_account(filename=CREDENTIALS_FILE)
    sheet = client.open(SHEET_NAME).sheet1
    sheet.append_row([time_str, price])

def get_alibaba_price(url):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 25)
        selector = ".pdp-card_sidebar .text-secondary-400"
        el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        raw = el.text
        digits = "".join(c for c in raw if c.isdigit())
        return int(digits) if digits else None
    finally:
        driver.quit()

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("🚀 Alibaba Flight Tracker | Single Run Mode")

    if check_if_expired(TARGET_FLIGHT_DEADLINE):
        print("⛔ Deadline passed. Exit.")
        exit(0)

    now = get_tehran_time().replace(tzinfo=None)
    last_run = get_last_run_time()

    if not should_save(last_run, now):
        print("⏳ Less than 1 hour since last save. Skipping.")
        exit(0)

    price = get_alibaba_price(ALIBABA_URL)
    if not price:
        print("❌ Price not found.")
        exit(1)

    now_str = now.strftime("%Y/%m/%d - %H:%M:%S")
    save_to_sheet(now_str, price)

    print(f"✅ Saved: {now_str} | {price:,}")
