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

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
             viewport={'width': 1280, 'height': 800},
             user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # Apply stealth directly to the page creation if possible, or just use the page
        # Note: stealth_async expects a page object
        
        for airport_name, url in airports.items():
            logging.info(f"Scraping flights for {airport_name}...")
            page = await context.new_page()
            await stealth_async(page)
            
            try:
                await page.goto(url, timeout=60000)
                
                # specific consent handling for Google
                try:
                    # Wait briefly to see if consent modal appears
                    accept_button = page.get_by_role("button", name="Accept all")
                    if await accept_button.is_visible(timeout=5000):
                        await accept_button.click()
                        logging.info("Clicked 'Accept all' on consent prompt")
                except Exception:
                    # Ignore if no consent prompt found or other issue
                    pass

                # Simulate human interaction
                await page.mouse.move(100, 100)
                await page.mouse.down()
                await page.mouse.up()
                await page.keyboard.press('PageDown')
                await asyncio.sleep(2)
                await page.keyboard.press('PageUp')
                
                # Wait for any H3 element which usually signifies a destination
                try:
                    await page.wait_for_selector('h3', timeout=20000)
                except Exception:
                    logging.warning(f"No flight headers (h3) found for {airport_name} (timeout)")
                    await page.screenshot(path=os.path.join(DATA_DIR, f'timeout_{airport_name}.png'))
                    with open(os.path.join(DATA_DIR, f'timeout_{airport_name}.html'), 'w') as f:
                        f.write(await page.content())
                    await page.close()
                    continue

                # Scroll to load more
                for _ in range(3):
                    await page.keyboard.press('PageDown')
                    await asyncio.sleep(1)

                # Use a more generic approach: Find valid cards by looking for price text
                # We look for any text matching currency patterns roughly, or structured card containers
                
                # Try to find all H3s (Destinations) and work up/down
                destinations_elements = await page.query_selector_all('h3')
                
                logging.info(f"Found {len(destinations_elements)} potential destinations for {airport_name}")

                for dest_el in destinations_elements:
                    try:
                        destination = await dest_el.inner_text()
                        if not destination: continue
                        
                        # Navigate up to find the card container.
                        # Usually h3 is inside the card.
                        # We can try to traverse up until we find a list item or just look at siblings
                        # This is tricky without exact structure.
                        # However, we know from inspection that H3 is inside li.lPyEac
                        # Let's try to find the closest 'li'
                        card = await dest_el.evaluate_handle('el => el.closest("li")')
                        if not card:
                            continue
                            
                        # Now assume this valid card
                        price_el = await card.query_selector('span[role="text"]')
                        if not price_el:
                             # Try alternate price selector
                             price_el = await card.query_selector('span[aria-label*="euro"]')
                             
                        price = await price_el.inner_text() if price_el else "Unknown"
                        
                        # Dates
                        # Look for text that looks like dates? Or the class .CQYfx if it persists
                        dates_el = await card.query_selector('.CQYfx')
                        dates = await dates_el.inner_text() if dates_el else "Unknown"
                        
                        # Duration
                        duration_el = await card.query_selector('.Xq1DAb')
                        duration = await duration_el.inner_text() if dates_el else "Unknown"


                        if price != "Unknown":
                            results["flights"].append({
                                "departure_airport": airport_name,
                                "destination": destination,
                                "price": price,
                                "dates": dates,
                                "duration": duration
                            })
                    except Exception as e:
                        logging.error(f"Error parsing card via H3: {e}")

            except Exception as e:
                logging.error(f"Failed to scrape {airport_name}: {e}")
                # Save debug screenshot
                screenshot_path = os.path.join(DATA_DIR, f'debug_{airport_name}.png')
                try:
                    await page.screenshot(path=screenshot_path)
                    logging.info(f"Saved debug screenshot to {screenshot_path}")
                    
                    html_path = os.path.join(DATA_DIR, f'debug_{airport_name}.html')
                    with open(html_path, 'w') as f:
                        f.write(await page.content())
                    logging.info(f"Saved debug HTML to {html_path}")
                except Exception:
                    pass
            finally:
                await page.close()

        await browser.close()

    logging.info(f"Scraping complete. Found {len(results['flights'])} flights.")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    asyncio.run(scrape_google_flights())
