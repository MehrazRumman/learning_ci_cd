# scrape.py

import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

# Configuration
ROOT_URL = "https://drive.yango.com/uae/dubai/rent-cars"
OUTPUT_DIR = Path("output")
META_DIR = OUTPUT_DIR / "meta"
IMAGES_DIR = OUTPUT_DIR / "images"

MAX_SHOW_MORE_ATTEMPTS = 200
SCROLL_PAUSE = 0.8
NAV_TIMEOUT = 20000  # ms
MAX_LINKS = 50  # You can adjust how many links you want to collect

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("scrape_yango")
# ensure output dirs
def ensure_dirs():
    META_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

def safe_name(s: str) -> str:
    if not s:
        return "unknown"
    s = s.strip()
    s = re.sub(r"[\\\/:*?\"<>|]+", "_", s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w \-_\.]", "", s)
    return s[:120].strip()

def extract_object_id_from_url(url: str):
    parsed = urlparse(url)
    qs = parsed.query
    # If “?object_id=...” in query
    from urllib.parse import parse_qs
    d = parse_qs(qs)
    return d.get("object_id", [None])[0]

def download_image(session: requests.Session, url: str, dest: Path, max_retries: int = 3):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        logger.info(f"Image exists, skipping: {dest}")
        return True
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(url, stream=True, timeout=15)
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(1024 * 8):
                    if chunk:
                        f.write(chunk)
            logger.info(f"Downloaded image: {dest.name}")
            return True
        except Exception as e:
            logger.warning(f"Attempt {attempt} failed for {url}: {e}")
            if attempt == max_retries:
                logger.error(f"Failed to download {url}")
                return False
            time.sleep(1 + attempt)

async def expand_all_results(page):
    logger.info("Expanding listings with scroll & ‘Show more’")
    prev_count = 0
    for attempt in range(MAX_SHOW_MORE_ATTEMPTS):
        # try clicking the “Show more results” button if exists
        try:
            btn = await page.query_selector("text=Show more results")
            if not btn:
                btn = await page.query_selector("text=Show more")
            if btn:
                await btn.scroll_into_view_if_needed()
                await btn.click()
                logger.debug(f"Clicked show more (attempt {attempt})")
                await page.wait_for_timeout(900)
        except Exception as e:
            logger.debug(f"Clicking show more failed: {e}")
        # scroll
        try:
            await page.evaluate("""() => window.scrollTo(0, document.body.scrollHeight)""")
            await page.wait_for_timeout(int(SCROLL_PAUSE * 1000))
        except Exception:
            pass
        # count anchors
        anchors = await page.query_selector_all("a[href*='/rent-cars/']")
        current = len(anchors)
        logger.info(f"Found {current} listing anchor(s)")
        if current >= MAX_LINKS:
            logger.info("Reached max links threshold, stop expanding")
            break
        if current == prev_count:
            # no change
            await page.wait_for_timeout(800)
            anchors2 = await page.query_selector_all("a[href*='/rent-cars/']")
            if len(anchors2) == prev_count:
                logger.info("No new items, break expansion")
                break
        prev_count = current

async def collect_car_links(page):
    logger.info("Collecting car detail links")
    anchors = await page.query_selector_all("a[href*='/rent-cars/']")
    links = set()
    for a in anchors:
        href = await a.get_attribute("href")
        if not href:
            continue
        full = urljoin(ROOT_URL, href)
        # filter out root or listing duplicates
        if "/rent-cars/" in full and full != ROOT_URL:
            full = full.split("#")[0].rstrip("/")
            links.add(full)
        if len(links) >= MAX_LINKS:
            break
    links = sorted(links)
    logger.info(f"Collected {len(links)} unique links")
    return links

async def scrape_car_page(page, url):
    logger.info(f"Scraping car detail: {url}")
    car = {"source_url": url}
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
    except Exception:
        logger.warning("domcontentloaded failed, fallback to networkidle")
        await page.goto(url, wait_until="networkidle", timeout=NAV_TIMEOUT)

    # Title
    try:
        h1 = await page.locator("h1").first.text_content(timeout=3000)
        car["title"] = h1.strip() if h1 else None
    except Exception:
        car["title"] = None

    car["object_id"] = extract_object_id_from_url(url)

    # JSON-LD scripts
    try:
        arr = []
        scripts = await page.query_selector_all('script[type="application/ld+json"]')
        for s in scripts:
            txt = await s.text_content()
            if not txt:
                continue
            # sometimes starts with some prefix to remove
            try:
                parsed = json.loads(txt)
            except Exception:
                try:
                    cleaned = re.sub(r"^\)\]\}',", "", txt)
                    parsed = json.loads(cleaned)
                except Exception:
                    continue
            arr.append(parsed)
        if arr:
            car["json_ld"] = arr
    except Exception:
        pass

    # Spec heuristics
    try:
        specs = {}
        selts = ["ul li", "div[data-test='car-parameters'] li", "div[class*='spec']", "section li", ".car-specs li"]
        texts = []
        for sel in selts:
            try:
                elems = await page.query_selector_all(sel)
                for e in elems:
                    txt = (await e.text_content()) or ""
                    txt = txt.strip()
                    if txt:
                        texts.append(txt)
            except Exception:
                continue
        for t in texts:
            low = t.lower()
            if "seat" in low:
                specs["seats"] = t
            elif "automatic" in low or "manual" in low:
                specs["transmission"] = t
            elif re.search(r"\baed\b", low):
                specs.setdefault("prices", []).append(t)
            else:
                specs.setdefault("others", []).append(t)
        if specs:
            car["specs"] = specs
    except Exception:
        pass

    # Description (paragraphs)
    try:
        ps = await page.locator("p").all_text_contents()
        ps = [p.strip() for p in ps if p.strip()]
        if ps:
            car["description"] = "\n".join(ps)
    except Exception:
        car["description"] = None

    # Image URLs
    img_urls = set()
    # from <img>
    try:
        imgs = await page.query_selector_all("img")
        for img in imgs:
            for attr in ("src", "data-src", "data-lazy", "data-original"):
                v = await img.get_attribute(attr)
                if v and v.startswith("http"):
                    img_urls.add(v.split("?")[0])
    except Exception:
        pass
    # from style attributes (background-image)
    try:
        els = await page.query_selector_all("[style]")
        for el in els:
            style = await el.get_attribute("style") or ""
            m = re.search(r"url\((['\"]?)(https?://[^)'\"]+)\1\)", style)
            if m:
                img_urls.add(m.group(2).split("?")[0])
    except Exception:
        pass

    car["image_urls"] = sorted(img_urls)
    if car.get("title"):
        car["model_name"] = safe_name(car["title"])
    else:
        parts = urlparse(url).path.strip("/").split("/")
        car["model_name"] = safe_name(parts[-1] if parts else "unknown")

    car["scraped_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    logger.info(f"Found {len(car['image_urls'])} image(s)")
    return car

async def main():
    ensure_dirs()
    session = requests.Session()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        logger.info("Navigating to root")
        await page.goto(ROOT_URL, wait_until="domcontentloaded")

        # Expand to show all results
        await expand_all_results(page)

        # Collect links
        links = await collect_car_links(page)
        logger.info(f"Will scrape {len(links)} car pages")

        for idx, link in enumerate(links, start=1):
            logger.info(f"[{idx}/{len(links)}] {link}")
            # prepare meta output path
            obj_id = extract_object_id_from_url(link) or safe_name(link)
            meta_path = META_DIR / f"{obj_id}.json"
            if meta_path.exists():
                logger.info("Already scraped, skipping")
                continue
            try:
                car = await scrape_car_page(page, link)
            except Exception as e:
                logger.error(f"Error scraping {link}: {e}")
                continue
            # Save metadata
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(car, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved meta: {meta_path.name}")

            # Download images
            model_folder = IMAGES_DIR / car["model_name"]
            for i, img_url in enumerate(car.get("image_urls", []), start=1):
                ext = os.path.splitext(urlparse(img_url).path)[1] or ".jpg"
                fname = f"{i:02d}{ext}"
                dest = model_folder / fname
                download_image(session, img_url, dest)

        await browser.close()
    logger.info("Done scraping")

if __name__ == "__main__":
    asyncio.run(main())
