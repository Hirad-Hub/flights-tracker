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

    results = {"last_checked": datetime.now().isoformat(), "