async def scrape_google_flights():
    print(f"Starting scraper. Looking for output in: {OUTPUT_FILE}")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    async with async_playwright() as p:
        # 1. Launch browser - SET headless=False so you can see it working
        browser = await p.chromium.launch(headless=False) 
        
        # 2. Set a specific locale to ensure the "Accept" button is in English
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            locale="en-US" 
        )

        page = await context.new_page()
        await stealth_async(page)

        # The specific URL you provided
        target_url = "https://www.google.com/travel/explore?tfs=CBwQAxoSKABgrAJqCwgCEgcvbS8wazNwGhIoAGCsAnILCAISBy9tLzBrM3BAAUgBYGRwAoIBCwj___________8BmAEBsgEEGAEgAQ&tfu=GgA"
        
        print("Navigating to Google Flights...")
        await page.goto(target_url, wait_until="networkidle")

        # 3. Handle the Cookie Consent Wall
        try:
            # This looks for the "Accept all" button specifically
            accept_button = page.get_by_role("button", name="Accept all")
            if await accept_button.is_visible():
                await accept_button.click()
                print("Clicked 'Accept all' cookie button.")
                await page.wait_for_timeout(2000)
        except Exception as e:
            print("No consent button found or already passed.")

        # 4. Wait for the flight cards to actually load
        # We use a more generic selector first to see if anything loads
        print("Waiting for flight results...")
        try:
            # This is a common container for the explore results
            await page.wait_for_selector('li', timeout=15000)
            
            # Extracting the flights
            flights = []
            # 'li' with a specific JS name is Google's current card format
            cards = await page.query_selector_all('li[jsname="W4feEd"]')
            
            for card in cards:
                title = await card.query_selector('h3')
                price = await card.query_selector('span[role="text"]')
                
                if title and price:
                    flights.append({
                        "destination": await title.inner_text(),
                        "price": await price.inner_text()
                    })

            print(f"Found {len(flights)} flights!")
            
            # Save to your JSON
            with open(OUTPUT_FILE, 'w') as f:
                json.dump({"flights": flights}, f, indent=2)

        except Exception as e:
            print(f"Error finding flights: {e}")
            # Take a screenshot to see what went wrong
            await page.screenshot(path="error_screen.png")
            print("Saved error_screen.png to check what the bot saw.")

        await browser.close()