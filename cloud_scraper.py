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
        self.url_elec = "https://energycost.gr/υπολογισμός-τιμής-βάσει-κατανάλωσης-2/"
        self.url_gas = "https://energycost.gr/υπολογισμός-τιμής-βάσει-κατανάλωσης-2/" # NOTE: Using Elec URL as base, logic needs to be distinct if URLs differ. 
        # Check original scraper for Gas URL...
        # Original scraper had: "https://energycost.gr/υπολογισμός-τιμής-βάσει-οι_gas/"
        # Let's fix that.
        self.url_gas = "https://energycost.gr/υπολογισμός-τιμής-βάσει-οι_gas/"

        self.options = webdriver.ChromeOptions()
        self.options.add_argument("--headless")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--window-size=1920,1080")

    def fetch_table(self, url):
        print(f"Fetching: {url}")
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
                    # Clean/Parse immediately to match our JSON structure
                    try:
                        # Adapting to the structure found in providers.json
                        # Note: The scraper returns "raw_data". 
                        # We need to map this to: name, program, price_kwh, monthly_fee, etc.
                        # Based on original app logic:
                        # name = raw[1], program = raw[4], fee = raw[7], price = raw[9]
                        
                        name = raw_data[1]
                        program = raw_data[4]
                        
                        fee_str = raw_data[7].replace(',', '.')
                        monthly_fee = float(fee_str) if fee_str.strip() else 0.0
                        
                        price_str = raw_data[9].replace(',', '.')
                        price_kwh = float(price_str) if price_str.strip() else 0.0
                        
                        results.append({
                            "name": name,
                            "program": program,
                            "type": "Live", # Marker
                            "price_kwh": price_kwh,
                            "monthly_fee": monthly_fee,
                            "discount_percent": 0.0,
                            "color": "#d35400",
                            "raw_data": raw_data # Keep raw just in case
                        })
                    except Exception as e:
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
        elec_data = self.fetch_table(self.url_elec)
        gas_data = self.fetch_table(self.url_gas)
        
        # Load existing to preserve regulated charges structure
        existing_data = {}
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        
        # Update timestamp
        import datetime
        existing_data["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # We replace the 'providers' list with the new Electric data
        # AND we might want to store Gas data separate or in same list?
        # The mobile app splits them by logic or creates separate lists. 
        # Current 'providers.json' only has one "providers" list (Electricity).
        # Let's add a "gas_providers" key to be safe and clean.
        
        if elec_data:
            existing_data["providers"] = elec_data
            print(f"Updated {len(elec_data)} Electricity providers.")
        
        if gas_data:
            existing_data["gas_providers"] = gas_data
            print(f"Updated {len(gas_data)} Gas providers.")

        # Ensure dir exists
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=4, ensure_ascii=False)
        print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    CloudScraper().run()
