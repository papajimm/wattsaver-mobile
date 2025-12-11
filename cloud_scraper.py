import json
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# Ensure we can find the assets folder relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "wattsaver_mobile", "assets", "providers.json")

class CloudScraper:
    def __init__(self):
        # Residential
        self.url_elec_res = "https://energycost.gr/υπολογισμός-τιμής-βάσει-κατανάλωσης-2/"
        self.url_gas_res = "https://energycost.gr/υπολογισμός-τιμής-βάσει-οι_gas/"
        
        # Business
        self.url_elec_bus = "https://energycost.gr/υπολογισμός-τιμής-βάσει-κατανάλωσης-3/"
        self.url_gas_bus = "https://energycost.gr/υπολογισμός-τιμής-βάσει-επ_gas/"

        self.options = webdriver.ChromeOptions()
        self.options.add_argument("--headless")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--window-size=1920,1080")

    def fetch_table(self, url, category_name):
        print(f"Fetching {category_name}: {url}")
        driver = None
        results = []
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=self.options)
            driver.get(url)

            wait = WebDriverWait(driver, 30)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(5) 

            tables = driver.find_elements(By.TAG_NAME, "table")
            if not tables:
                print("No tables found.")
                return []

            target_table = max(tables, key=lambda t: len(t.find_elements(By.TAG_NAME, "tr")))
            rows = target_table.find_elements(By.TAG_NAME, "tr")
            print(f"Found {len(rows)} rows.")

            for row in rows[1:]:
                cols = row.find_elements(By.TAG_NAME, "td")
                if not cols: continue
                raw_data = [c.text for c in cols]
                if len(raw_data) > 2:
                    try:
                        # Common parsing logic (Assuming table structure is similar across pages)
                        # Adapting to match providers.json structure
                        name = raw_data[1]
                        program = raw_data[4]
                        
                        fee_str = raw_data[7].replace(',', '.')
                        monthly_fee = float(fee_str) if fee_str.strip() else 0.0
                        
                        price_str = raw_data[9].replace(',', '.')
                        price_kwh = float(price_str) if price_str.strip() else 0.0
                        
                        results.append({
                            "name": name,
                            "program": program,
                            "type": "Live",
                            "category": category_name, # Tag the category
                            "price_kwh": price_kwh,
                            "monthly_fee": monthly_fee,
                            "discount_percent": 0.0,
                            "color": "#d35400",
                            "raw_data": raw_data 
                        })
                    except Exception as e:
                        # Only print error if it's not a header/empty row issue
                        if "list index" not in str(e):
                             print(f"Row parse error: {e}")
                        continue
            return results

        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return []
        finally:
            if driver: driver.quit()

    def run(self):
        print("Starting Cloud Scrape...")
        
        # Fetch all 4 categories
        elec_res = self.fetch_table(self.url_elec_res, "Residential Electricity")
        gas_res = self.fetch_table(self.url_gas_res, "Residential Gas")
        elec_bus = self.fetch_table(self.url_elec_bus, "Business Electricity")
        gas_bus = self.fetch_table(self.url_gas_bus, "Business Gas")
        
        # Load existing
        existing_data = {}
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        
        # Update timestamp
        import datetime
        existing_data["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Store Data
        # We'll map them to specific keys.
        # 'providers' -> Residential Electricity (Main backward compatibility)
        # 'gas_providers' -> Residential Gas
        # 'providers_business' -> Business Electricity
        # 'gas_providers_business' -> Business Gas
        
        if elec_res: existing_data["providers"] = elec_res
        if gas_res: existing_data["gas_providers"] = gas_res
        if elec_bus: existing_data["providers_business"] = elec_bus
        if gas_bus: existing_data["gas_providers_business"] = gas_bus

        print(f"Summary: Elec_Res={len(elec_res)}, Gas_Res={len(gas_res)}, Elec_Bus={len(elec_bus)}, Gas_Bus={len(gas_bus)}")

        # Ensure dir exists
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=4, ensure_ascii=False)
        print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    CloudScraper().run()