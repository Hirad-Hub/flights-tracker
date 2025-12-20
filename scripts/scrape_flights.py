import asyncio
import json
import logging
import os
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
AIRPORTS_FILE = os.path.join(os.path.dirname(__file__), '..', 'airports.json')
OUTPUT_FILE = os.path.join(DATA_DIR, 'flights.json')

async def scrape_google_flights():
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Load airports
    if not os.path.exists(AIRPORTS_FILE):
        logging.error(f"Airports file not found at {AIRPORTS_FILE}")
        return

    with open(AIRPORTS_FILE, 'r') as f:
        airports = json.load(f)

    results = {
        "last_checked": datetime.now().isoformat(),
        "flights": []
    }

    # IMPORTANT: This block MUST be indented (4 spaces in)
    async with async_playwright() as p:
        # Use Browserless token from environment variable
        browserless_token = os.getenv("BROWSERLESS_TOKEN")
        
        if browserless_token:
            logging.info("Connecting to Browserless.io...")
            endpoint = f"wss://production-sfo.browserless.io/chromium/stealth?token={browserless_token}"
            browser = await p.chromium.connect_over_cdp(endpoint)
        else:
            logging.warning("No BROWSERLESS_TOKEN found. Running locally.")
            browser = await p.chromium.launch(headless=True)

        if browser.contexts:
            context = browser.contexts[0]
        else:
            context = await browser.new_context(
                 viewport={'width': 1280, 'height': 800},
                 user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
        
        for airport_name, url in airports.items():
            logging.info(f"Scraping flights for {airport_name}...")
            page = await context.new_page()
            await stealth_async(page)
            
            try:
                await page.goto(url, timeout=60000)
                
                try:
                    accept_button = page.get_by_role("button", name="Accept all")
                    if await accept_button.is_visible(timeout=5000):
                        await accept_button.click()
                except Exception:
                    pass

                await page.mouse.move(100, 100)
                await page.mouse.down()
                await page.mouse.up()
                await page.keyboard.press('PageDown')
                await asyncio.sleep(2)
                
                try:
                    await page.wait_for_selector('h3', timeout=20000)
                except Exception:
                    await page.close()
                    continue

                destinations_elements = await page.query_selector_all('h3')

                for dest_el in destinations_elements:
                    try:
                        destination = await dest_el.inner_text()
                        if not destination: continue
                        
                        card = await dest_el.evaluate_handle('el => el.closest("li")')
                        if not card: continue
                            
                        price_el = await card.query_selector('span[role="text"]')
                        if not price_el:
                             price_el = await card.query_selector('span[aria-label*="euro"]')
                             
                        price = await price_el.inner_text() if price_el else "Unknown"
                        
                        dates_el = await card.query_selector('.CQYfx')
                        dates = await dates_el.inner_text() if dates_el else "Unknown"
                        
                        duration_el = await card.query_selector('.Xq1DAb')
                        duration = await duration_el.inner_text() if duration_el else "Unknown"

                        if price != "Unknown":
                            results["flights"].append({
                                "departure_airport": airport_name,
                                "destination": destination,
                                "price": price,
                                "dates": dates,
                                "duration": duration
                            })
                    except Exception:
                        continue

            except Exception as e:
                logging.error(f"Failed to scrape {airport_name}: {e}")
            finally:
                await page.close()

        await browser.close()

    # This part saves the file after the "async with" block is finished
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    asyncio.run(scrape_google_flights())