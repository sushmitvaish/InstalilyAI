import asyncio
import json
import random
import re
import os
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


BASE_URL = "https://www.partselect.com"

CATEGORY_URLS = {
    "Refrigerator": f"{BASE_URL}/Refrigerator-Parts.htm",
    "Dishwasher": f"{BASE_URL}/Dishwasher-Parts.htm",
}

# Additional brand-specific pages to find more parts
BRAND_CATEGORY_URLS = {
    "Refrigerator": [
        f"{BASE_URL}/Whirlpool-Refrigerator-Parts.htm",
        f"{BASE_URL}/GE-Refrigerator-Parts.htm",
        f"{BASE_URL}/Samsung-Refrigerator-Parts.htm",
        f"{BASE_URL}/LG-Refrigerator-Parts.htm",
        f"{BASE_URL}/Frigidaire-Refrigerator-Parts.htm",
        f"{BASE_URL}/KitchenAid-Refrigerator-Parts.htm",
        f"{BASE_URL}/Maytag-Refrigerator-Parts.htm",
    ],
    "Dishwasher": [
        f"{BASE_URL}/Whirlpool-Dishwasher-Parts.htm",
        f"{BASE_URL}/GE-Dishwasher-Parts.htm",
        f"{BASE_URL}/Samsung-Dishwasher-Parts.htm",
        f"{BASE_URL}/LG-Dishwasher-Parts.htm",
        f"{BASE_URL}/Frigidaire-Dishwasher-Parts.htm",
        f"{BASE_URL}/KitchenAid-Dishwasher-Parts.htm",
        f"{BASE_URL}/Bosch-Dishwasher-Parts.htm",
        f"{BASE_URL}/Maytag-Dishwasher-Parts.htm",
    ],
}


async def random_delay(min_sec=2, max_sec=5):
    await asyncio.sleep(random.uniform(min_sec, max_sec))


async def create_stealth_browser(playwright):
    """Launch a non-headless browser with anti-detection measures."""
    browser = await playwright.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone_id="America/New_York",
    )
    page = await context.new_page()
    await page.add_init_script(
        'Object.defineProperty(navigator, "webdriver", {get: () => undefined});'
    )
    return browser, context, page


async def scrape_part_page(page, url: str) -> dict:
    """Scrape a single part page and return structured data."""
    try:
        # Clean URL - remove tracking params
        clean_url = re.sub(r'\?SourceCode=\d+', '', url)
        clean_url = re.sub(r'#.*$', '', clean_url)

        resp = await page.goto(
            clean_url, wait_until="domcontentloaded", timeout=30000
        )
        if resp.status != 200:
            print(f"  Got status {resp.status}, skipping")
            return None

        await random_delay(2, 4)

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        data = {"source_url": clean_url}

        # PS number from URL
        ps_match = re.search(r'PS(\d+)', clean_url)
        if ps_match:
            data["ps_number"] = f"PS{ps_match.group(1)}"

        # Title from h1
        title_el = soup.select_one("h1")
        if title_el:
            data["name"] = title_el.get_text(strip=True)

        # Price from .pd__price or .js-partPrice
        price_el = soup.select_one(".pd__price")
        if price_el:
            price_match = re.search(r'\$[\d,.]+', price_el.get_text())
            if price_match:
                data["price"] = price_match.group(0)
        if "price" not in data:
            js_price = soup.select_one(".js-partPrice")
            if js_price:
                price_text = js_price.get_text(strip=True)
                if re.match(r'[\d,.]+', price_text):
                    data["price"] = f"${price_text}"

        # Description from .pd__description
        desc_el = soup.select_one(".pd__description")
        if desc_el:
            data["description"] = desc_el.get_text(strip=True)[:1500]

        # OEM Part Number from URL pattern or page
        oem_from_url = re.search(
            r'PS\d+-\w+-(\w+)-', clean_url
        )
        if oem_from_url:
            data["oem_part_number"] = oem_from_url.group(1)

        # Main product image
        img_el = soup.select_one(
            'img[src*="partimages"]'
        )
        if img_el:
            src = img_el.get("src", "")
            if src.startswith("//"):
                src = "https:" + src
            data["image_url"] = src

        # Compatible models from .pd__crossref__list
        crossref = soup.select_one(".pd__crossref__list")
        if crossref:
            crossref_text = crossref.get_text()
            model_nums = re.findall(
                r'\b[A-Z0-9]{5,}\b', crossref_text
            )
            # Filter out generic words
            model_nums = [
                m for m in model_nums
                if not m.startswith("REFRIG") and not m.startswith("DISHWA")
                and len(m) >= 6
            ]
            if model_nums:
                data["compatible_models"] = list(set(model_nums))

        # Repair stories / installation info
        repair_stories = soup.select(".pd__repair-story")
        if repair_stories:
            install_texts = []
            for story in repair_stories[:5]:
                text = story.get_text(strip=True)
                if len(text) > 30:
                    install_texts.append(text)
            if install_texts:
                data["installation_instructions"] = (
                    " | ".join(install_texts)[:2000]
                )

        # Repair rating
        rating_el = soup.select_one(".pd__repair-rating__container")
        if rating_el:
            rating_text = rating_el.get_text(strip=True)
            rating_match = re.search(r'([\d.]+)\s*/\s*5', rating_text)
            if rating_match:
                data["repair_rating"] = rating_match.group(1)

        # In stock check
        stock_el = soup.select_one(".pd__ships-today")
        if stock_el:
            data["in_stock"] = True
        else:
            avail_el = soup.select_one(".js-partAvailability")
            if avail_el:
                avail_text = avail_el.get_text(strip=True).lower()
                data["in_stock"] = "in stock" in avail_text

        # Video presence
        video_section = soup.select_one(".pd__video")
        if video_section:
            data["has_video"] = True

        return data

    except Exception as e:
        print(f"  Error scraping {url}: {e}")
        return None


async def collect_part_urls(page, url: str) -> list:
    """Collect part page URLs from a category/brand page."""
    part_urls = []
    try:
        resp = await page.goto(
            url, wait_until="domcontentloaded", timeout=30000
        )
        if resp.status != 200:
            print(f"  Category page returned {resp.status}")
            return []

        await random_delay(2, 4)

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if re.search(r'/PS\d{5,}.*\.htm', href):
                # Clean tracking params and anchors
                clean = re.sub(r'\?.*$', '', href)
                clean = re.sub(r'#.*$', '', clean)
                full_url = (
                    clean if clean.startswith("http")
                    else BASE_URL + clean
                )
                if full_url not in part_urls:
                    part_urls.append(full_url)

    except Exception as e:
        print(f"  Error on category page {url}: {e}")

    return part_urls


async def run_scraper(max_parts_per_category: int = 100,
                      output_file: str = "data/parts.jsonl"):
    """Main scraper entry point."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Clear previous output
    if os.path.exists(output_file):
        os.remove(output_file)

    async with async_playwright() as p:
        browser, context, page = await create_stealth_browser(p)

        all_parts = []
        seen_ps_numbers = set()

        for appliance_type, category_url in CATEGORY_URLS.items():
            print(f"\n{'='*60}")
            print(f"Scraping {appliance_type} parts...")
            print(f"{'='*60}")

            # Collect part URLs from main category page
            part_urls = await collect_part_urls(page, category_url)
            print(f"  Main category: {len(part_urls)} part URLs")

            # Also collect from brand-specific pages
            brand_urls = BRAND_CATEGORY_URLS.get(appliance_type, [])
            for brand_url in brand_urls:
                await random_delay(2, 4)
                brand_parts = await collect_part_urls(page, brand_url)
                brand_name = re.search(
                    r'partselect\.com/(\w+)-', brand_url
                )
                brand_label = brand_name.group(1) if brand_name else "?"
                new_count = 0
                for u in brand_parts:
                    if u not in part_urls:
                        part_urls.append(u)
                        new_count += 1
                print(f"  {brand_label}: +{new_count} new URLs")

            print(f"  Total unique URLs: {len(part_urls)}")

            # Deduplicate by PS number and limit
            unique_urls = []
            for u in part_urls:
                ps = re.search(r'PS(\d+)', u)
                if ps and ps.group(0) not in seen_ps_numbers:
                    seen_ps_numbers.add(ps.group(0))
                    unique_urls.append(u)
            unique_urls = unique_urls[:max_parts_per_category]

            print(f"  Scraping {len(unique_urls)} part pages...")

            # Scrape each part page
            for i, url in enumerate(unique_urls):
                print(f"  [{i+1}/{len(unique_urls)}] {url}")
                part_data = await scrape_part_page(page, url)

                if part_data and part_data.get("ps_number"):
                    part_data["appliance_type"] = appliance_type
                    all_parts.append(part_data)

                    with open(output_file, "a") as f:
                        f.write(json.dumps(part_data) + "\n")

                await random_delay(2, 4)

        await browser.close()

    print(f"\nDone! Scraped {len(all_parts)} parts total.")
    print(f"Output saved to {output_file}")
    return all_parts


if __name__ == "__main__":
    asyncio.run(run_scraper())
