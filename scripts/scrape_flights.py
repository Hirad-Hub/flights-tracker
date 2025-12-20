async def scrape_google_flights():
    # ... (Keep your os.makedirs and airport loading code exactly the same here) ...

    async with async_playwright() as p:
        browserless_token = os.getenv("BROWSERLESS_TOKEN")
        
        try:
            if browserless_token:
                logging.info("Connecting to Browserless.io...")
                endpoint = f"wss://production-sfo.browserless.io/chromium/stealth?token={browserless_token}"
                browser = await p.chromium.connect_over_cdp(endpoint)
            else:
                logging.warning("No BROWSERLESS_TOKEN found. Running locally.")
                browser = await p.chromium.launch(headless=True)
        except Exception as e:
            logging.error(f"Failed to launch browser: {e}")
            return

        for airport_name, url in airports.items():
            # Check if browser is still alive before starting a new airport
            if not browser.is_connected():
                break

            context = await browser.new_context(
                 viewport={'width': 1280, 'height': 800},
                 user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            try:
                page = await context.new_page()
                await stealth_async(page)
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                
                # ... (Keep your scraping/button clicking logic exactly the same) ...

            except Exception as e:
                logging.error(f"Failed to scrape {airport_name}: {e}")
            finally:
                # SAFETY FIX 1: Only close context if the browser is still connected
                if browser.is_connected():
                    try:
                        await context.close()
                    except:
                        pass

        # SAFETY FIX 2: Only close browser if it hasn't been disconnected by Browserless already
        if browser.is_connected():
            try:
                await browser.close()
            except:
                pass

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)