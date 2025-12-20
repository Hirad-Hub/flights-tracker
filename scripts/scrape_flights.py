import os
import json
import logging
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# File paths
AIRPORTS_FILE = "data/airports.json"
OUTPUT_FILE = "data/flights.json"

async def scrape_google_flights():
    print(f"Starting scraper. Looking for output in: {OUTPUT_FILE}")
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    if not os.path.exists(AIRPORTS_FILE):
        print(f"ERROR: Airports file missing at {AIRPORTS_FILE}")
        return

    with open(AIRPORTS_FILE, 'r') as f:
        airports = json.load(f)
        print(f"Loaded {len(airports)} airports to check.")

    results = {"last_checked": datetime.now().isoformat(), "flights": []}

    async with async_playwright() as p:
        browserless_token = os.getenv("BROWSERLESS_TOKEN")
        
        try:
            if browserless_token:
                print("Connecting to Browserless.io...")
                endpoint = f"wss://production-sfo.browserless.io/chromium/stealth?token={browserless_token}"
                browser = await p.chromium.connect_over_cdp(endpoint)
            else:
                print("Running locally (No Browserless token).")
                # Use "new" headless mode which is more reliable for modern sites
                # Add args to help with rendering and detection
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-gpu" 
                    ]
                )
        except Exception as e:
            print(f"CRITICAL: Failed to launch browser: {e}")
            return

        for airport_name, url in airports.items():
            if not browser.is_connected():
                print("Browser disconnected.")
                break

            print(f"Checking flights for: {airport_name}...")
            
            context = await browser.new_context(
                 viewport={'width': 1280, 'height': 800},
                 user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            try:
                page = await context.new_page()
                await stealth_async(page)
                
                # Consent handling: Try to click "Accept all" or "Reject all" if present
                try:
                    consent_button = await page.query_selector('button[aria-label="Accept all"]')
                    if not consent_button:
                        consent_button = await page.query_selector('button:has-text("Accept all")')
                    if not consent_button:
                        consent_button = await page.query_selector('button:has-text("Reject all")')
                    
                    if consent_button:
                        print(f"Found consent button. Clicking...")
                        await consent_button.click()
                        await page.waitForTimeout(2000) # Wait for overlay to disappear
                except Exception as e:
                    print(f"Consent handling error (non-critical): {e}")

                # TARGETING: Specifically look for flight result cards
                # Robust selector identified: li[jsname="W4feEd"]
                card_selector = 'li[jsname="W4feEd"]' 
                
                try:
                    await page.wait_for_selector(card_selector, timeout=15000)
                    await asyncio.sleep(2)
                except:
                    print(f"No flight cards found for {airport_name} within 15s (selector: {card_selector}).")
                    continue

                flight_cards = await page.query_selector_all(card_selector)
                
                for card in flight_cards:
                    destination_el = await card.query_selector('h3')
                    # Look for price in multiple possible spans/divs
                    price_el = await card.query_selector('span[role="text"]')
                    if not price_el:
                         price_el = await card.query_selector('.QB2Jof') # Secondary known price class
                    
                    if destination_el:
                        dest_text = await destination_el.inner_text()
                        dest_text = dest_text.strip()
                        
                        price_text = ""
                        if price_el:
                            price_text = await price_el.inner_text()
                        
                        # Fallback: if price_el not found, try to find text with € in the whole card
                        if not price_text or "€" not in price_text:
                            all_text = await card.inner_text()
                            # simple heuristic to find price line
                            for line in all_text.split('\n'):
                                if '€' in line and len(line) < 20:
                                    price_text = line
                                    break
                        
                        if "€" in price_text:
                            results["flights"].append({
                                "departure_airport": airport_name,
                                "destination": dest_text,
                                "price": price_text.strip(),
                                "date": datetime.now().strftime("%Y-%m-%d")
                            })
                
                print(f"Finished {airport_name}. Found {len(results['flights'])} flights so far.")
                
            except Exception as e:
                print(f"Failed to scrape {airport_name}: {e}")
            finally:
                if browser.is_connected():
                    await context.close()

        if browser.is_connected():
            await browser.close()

    # Write the results to the file
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"SUCCESS: Saved {len(results['flights'])} flights to {OUTPUT_FILE}")

# --- THE TRIGGER ---
if __name__ == "__main__":
    asyncio.run(scrape_google_flights())