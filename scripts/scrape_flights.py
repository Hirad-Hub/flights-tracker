for airport_name, url in airports.items():
            if not browser.is_connected():
                print("Browser disconnected.")
                break

            print(f"Checking flights for: {airport_name}...")
            context = await browser.new_context(viewport={'width': 1280, 'height': 800})
            
            try:
                page = await context.new_page()
                await stealth_async(page)
                
                # Increase timeout and wait for the page to be fully loaded
                await page.goto(url, timeout=90000, wait_until="networkidle")
                
                # TARGETING: Specifically look for flight result cards (class pIos7c)
                # This avoids the "Round Trip" menu that caused your timeout
                try:
                    await page.wait_for_selector('li.pIos7c', timeout=15000)
                except:
                    print(f"No flight cards found for {airport_name} within 15s.")
                    continue

                flight_cards = await page.query_selector_all('li.pIos7c')
                
                for card in flight_cards:
                    # Destination is usually in an h3 within the card
                    dest_el = await card.query_selector('h3')
                    # Price is in a span with a specific role
                    price_el = await card.query_selector('span[role="text"]')
                    
                    if dest_el and price_el:
                        dest_text = await dest_el.inner_text()
                        price_text = await price_el.inner_text()
                        
                        if "€" in price_text:
                            results["flights"].append({
                                "departure_airport": airport_name,
                                "destination": dest_text.strip(),
                                "price": price_text.strip(),
                                "date": datetime.now().strftime("%Y-%m-%d")
                            })
                
                print(f"Successfully scraped {airport_name}.")
                
            except Exception as e:
                print(f"Failed to scrape {airport_name}: {e}")
            finally:
                if browser.is_connected():
                    await context.close()