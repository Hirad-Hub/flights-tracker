async def scrape_google_flights():
    # 1. Milestone: Check if we even started
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
                browser = await p.chromium.launch(headless=True)
        except Exception as e:
            print(f"CRITICAL: Failed to launch browser: {e}")
            return

        for airport_name, url in airports.items():
            if not browser.is_connected():
                print("Browser disconnected unexpectedly.")
                break

            print(f"Checking flights for: {airport_name}...")
            
            context = await browser.new_context(
                 viewport={'width': 1280, 'height': 800},
                 user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            try:
                page = await context.new_page()
                await stealth_async(page)
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                
                # ... (Your specific scraping logic here) ...
                # Add this inside your inner loop where you find a price:
                # print(f"Found price: {price} for {destination}")

            except Exception as e:
                print(f"Failed to scrape {airport_name}: {e}")
            finally:
                if browser.is_connected():
                    await context.close()

        if browser.is_connected():
            await browser.close()

    # 2. Milestone: Check if we are actually writing the file
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"SUCCESS: Saved {len(results['flights'])} flights to {OUTPUT_FILE}")