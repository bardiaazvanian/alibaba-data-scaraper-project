# ✈️ Alibaba.ir Real-time Flight Price Tracker

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python)
![Selenium](https://img.shields.io/badge/Selenium-Webdriver-43B02A?style=for-the-badge&logo=selenium)
![Status](https://img.shields.io/badge/Status-Production-brightgreen?style=for-the-badge)

## 📉 Overview

This project is a specialized web scraper built with **Python** and **Selenium**. Its primary goal is to monitor flight ticket prices on **Alibaba.ir** (Iran's leading travel agency) for specific routes leading up to the departure time.

The data extracted by this engine is designed to be logged into **Google Sheets** every hour, enabling data visualization and price trend analysis via **Looker Studio**.

## 🤝 Project Background & Consulting

> **"Why Python instead of n8n?"**

As a Solo Builder, I initially proposed an **n8n low-code workflow** for faster deployment and lower maintenance. However, the client had a strict requirement for a custom **Python-based codebase** for their internal infrastructure. I adapted to this constraint and delivered a robust Selenium solution that mimics human behavior.

## ✨ Key Features

* **Bot Detection Bypass:** Uses **Cookie Injection** (`cookies.json`) to simulate a logged-in user session, preventing the scraper from being blocked as a "Guest Bot."
* **Headless Execution:** optimized for **GitHub Actions** or Linux Servers (CI/CD ready) with flags like `--disable-gpu` and `--no-sandbox`.
* **Smart Parsing:** Handles dynamic CSS classes (e.g., `.text-secondary-400`) to accurately locate price tags.
* **Jalali Date Support:** Integrated `jdatetime` to log timestamps in the Persian calendar format, matching the local business context.
* **Auto-Driver Management:** Uses `webdriver_manager` to automatically handle Chrome Driver versions.

## ⚙️ How It Works

1.  **Initialization:** The script initializes a Headless Chrome browser optimized for server environments.
2.  **Authentication:** It loads pre-saved session cookies to authenticate the request as a real user.
3.  **Navigation:** Navigates to the specific flight URL (Dynamic parameters for Date/Origin/Dest).
4.  **Extraction:**
    * Waits for the DOM to load (Explicit Waits).
    * Locates the price element.
    * Cleans the data (removes non-digit characters).
5.  **Output:** Returns the clean integer price and flight date for downstream processing (Google Sheets/Database).

## 🛠️ Installation & Usage

### Prerequisites
* Python 3.x
* Google Chrome installed

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/bardiaazvanian/alibaba-data-scaraper-project.git
    ```

2.  **Install dependencies:**
    ```bash
    pip install selenium webdriver-manager jdatetime
    ```

3.  **Cookie Setup (Crucial):**
    * Log in to Alibaba.ir on your local browser.
    * Export your cookies as JSON using a browser extension (e.g., EditThisCookie).
    * Save the file as `cookies.json` in the root directory.

4.  **Run the script:**
    ```bash
    python main.py
    ```

## 📊 Analytics Pipeline

Although this repository contains the **Extraction Engine**, the full pipeline was designed as follows:
1.  **Python Script:** Runs every hour via Cron Job / GitHub Actions.
2.  **Data Storage:** Appends price data to a Google Sheet.
3.  **Visualization:** **Looker Studio** connects to the Sheet to visualize price drops and optimal booking times.

## 👨‍💻 Author

**Bardia Azvanian**
*Solo AI Builder & Full-Stack Engineer*

---
*Disclaimer: This tool was developed for price analysis and monitoring purposes requested by a client. Use responsibly and adhere to the target website's Terms of Service.*
