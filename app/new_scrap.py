import os
import re
import json
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime
import requests
from urllib.parse import urlparse, urljoin

def setup_driver(headless=True):
    """Setup Chrome driver"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def extract_car_model_from_url(url):
    """Extract car model name from URL for folder naming"""
    # Example: .../toyota/rush?object_id=... -> toyota_rush
    parts = url.split('?')[0].split('/')
    if len(parts) >= 2:
        brand = parts[-2]
        model = parts[-1]
        return f"{brand}_{model}".replace(' ', '_').replace('-', '_')
    return "unknown_car"

def scrape_car_details(driver, url):
    """Scrape all details from a car detail page"""
    print(f"\n{'='*70}")
    print(f"Scraping: {url}")
    print(f"{'='*70}")
    
    try:
        driver.get(url)
        time.sleep(5)  # Wait for page to load
    except Exception as e:
        print(f"Error loading page: {e}")
        return None
    
    # Click "Show More" button if it exists
    try:
        print("Looking for 'Show More' button...")
        show_more_selectors = [
            "//button[contains(text(), 'Show more')]",
            "//button[contains(text(), 'show more')]",
            "//span[contains(text(), 'Show more')]",
            "//div[contains(text(), 'Show more')]",
            "[class*='show-more']",
            "[class*='ShowMore']",
            "button[class*='more']"
        ]
        
        for selector in show_more_selectors:
            try:
                if selector.startswith("//"):
                    button = driver.find_element(By.XPATH, selector)
                else:
                    button = driver.find_element(By.CSS_SELECTOR, selector)
                
                if button and button.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", button)
                    print("✓ Clicked 'Show More' button")
                    time.sleep(2)
                    break
            except:
                continue
    except Exception as e:
        print(f"  No 'Show More' button found or already expanded")
    
    # Click "Required Documents" button if it exists
    try:
        print("Looking for 'Required Documents' button...")
        doc_selectors = [
            "//button[contains(text(), 'Required documents')]",
            "//button[contains(text(), 'required documents')]",
            "//span[contains(text(), 'Required documents')]",
            "//div[contains(text(), 'Required documents')]",
            "[class*='required-documents']",
            "[class*='RequiredDocuments']"
        ]
        
        for selector in doc_selectors:
            try:
                if selector.startswith("//"):
                    button = driver.find_element(By.XPATH, selector)
                else:
                    button = driver.find_element(By.CSS_SELECTOR, selector)
                
                if button and button.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", button)
                    print("✓ Clicked 'Required Documents' button")
                    time.sleep(2)
                    break
            except:
                continue
    except Exception as e:
        print(f"  No 'Required Documents' button found")
    
    # Get page source after clicking buttons
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    car_data = {
        'title': '',
        'model': '',
        'brand': '',
        'class': '',
        'body_type': '',
        'transmission': '',
        'year': '',
        'color': '',
        'engine_capacity': '',
        'drive_type': '',
        'horsepower': '',
        'max_speed': '',
        'seats': '',
        'doors': '',
        'price': '',
        'instant_delivery': '',
        'required_documents': '',
        'url': url,
        'scraped_at': datetime.now().isoformat()
    }
    
    # Extract title
    title_elem = soup.select_one('h1')
    if title_elem:
        car_data['title'] = title_elem.get_text(strip=True)
    
    # Get all text for searching
    body_text = soup.get_text(' ', strip=True)
    
    # Extract from URL
    url_parts = url.split('?')[0].split('/')
    if len(url_parts) >= 3:
        car_data['class'] = url_parts[-3].replace('-', ' ').title() if len(url_parts) > 2 else ''
        car_data['brand'] = url_parts[-2].replace('-', ' ').title()
        car_data['model'] = url_parts[-1].replace('-', ' ').title()
    
    # Define field patterns to search for
    field_patterns = {
        'transmission': r'(automatic|manual|cvt)',
        'year': r'20\d{2}',
        'color': r'(?:color|colour)[\s:]*([a-z]+)',
        'engine_capacity': r'(\d+\.?\d*)\s*(?:l|liter|litre|cc)',
        'drive_type': r'(fwd|rwd|awd|4wd|front wheel|rear wheel|all wheel)',
        'horsepower': r'(\d+)\s*(?:hp|horsepower)',
        'max_speed': r'(\d+)\s*(?:km/h|kmh|kph)',
        'seats': r'(\d+)\s*(?:seat|passenger)',
        'doors': r'(\d+)\s*door',
        'instant_delivery': r'instant delivery[\s:]*([yes|no|available|not available]*)',
        'body_type': r'(sedan|suv|hatchback|coupe|convertible|wagon|truck|van|minivan)'
    }
    
    for field, pattern in field_patterns.items():
        if not car_data[field]:
            match = re.search(pattern, body_text, re.IGNORECASE)
            if match:
                try:
                    car_data[field] = match.group(1) if match.lastindex else match.group(0)
                except:
                    car_data[field] = match.group(0)
    
    # Extract price
    price_patterns = [
        r'AED\s*[\d,]+(?:\.\d+)?(?:\s*/\s*day)?',
        r'[\d,]+\s*AED(?:\s*/\s*day)?',
        r'from\s*[\d,]+',
    ]
    for pattern in price_patterns:
        match = re.search(pattern, body_text, re.IGNORECASE)
        if match:
            car_data['price'] = match.group(0)
            break
    
    # Extract required documents - look for list items after clicking
    doc_keywords = ['passport', 'visa', 'license', 'driving licence', 'id card', 'emirates id', 'insurance']
    doc_sections = soup.find_all(string=re.compile(r'required documents', re.IGNORECASE))
    
    documents_list = []
    for section in doc_sections:
        parent = section.find_parent()
        if parent:
            # Look for lists near this section
            for sibling in parent.find_all_next(['li', 'p', 'div'], limit=20):
                text = sibling.get_text(strip=True)
                if any(keyword in text.lower() for keyword in doc_keywords):
                    if text not in documents_list and len(text) < 200:
                        documents_list.append(text)
    
    if documents_list:
        car_data['required_documents'] = ', '.join(documents_list)
    else:
        # Fallback: search for documents in entire text
        for keyword in doc_keywords:
            if keyword in body_text.lower():
                idx = body_text.lower().find(keyword)
                snippet = body_text[max(0, idx-20):idx+50]
                if snippet and car_data['required_documents'] == '':
                    car_data['required_documents'] = snippet.strip()
                    break
    
    # Try to find specifications in structured data
    # Look for dt/dd pairs
    for dl in soup.select('dl'):
        dts = dl.select('dt')
        dds = dl.select('dd')
        for dt, dd in zip(dts, dds):
            key = dt.get_text(strip=True).lower()
            value = dd.get_text(strip=True)
            
            if 'model' in key and not car_data['model']:
                car_data['model'] = value
            elif 'brand' in key and not car_data['brand']:
                car_data['brand'] = value
            elif 'class' in key and not car_data['class']:
                car_data['class'] = value
            elif 'body' in key and not car_data['body_type']:
                car_data['body_type'] = value
            elif 'transmission' in key and not car_data['transmission']:
                car_data['transmission'] = value
            elif 'year' in key and not car_data['year']:
                car_data['year'] = value
            elif 'color' in key or 'colour' in key and not car_data['color']:
                car_data['color'] = value
            elif 'engine' in key and not car_data['engine_capacity']:
                car_data['engine_capacity'] = value
            elif 'drive' in key and not car_data['drive_type']:
                car_data['drive_type'] = value
            elif 'horse' in key or 'power' in key and not car_data['horsepower']:
                car_data['horsepower'] = value
            elif 'speed' in key and not car_data['max_speed']:
                car_data['max_speed'] = value
            elif 'seat' in key and not car_data['seats']:
                car_data['seats'] = value
            elif 'door' in key and not car_data['doors']:
                car_data['doors'] = value
    
    print(f"✓ Title: {car_data['title']}")
    print(f"✓ Brand: {car_data['brand']}")
    print(f"✓ Model: {car_data['model']}")
    print(f"✓ Price: {car_data['price']}")
    print(f"✓ Transmission: {car_data['transmission']}")
    print(f"✓ Required Documents: {car_data['required_documents'][:50]}..." if car_data['required_documents'] else "✓ Required Documents: Not found")
    
    return car_data

def download_image(img_url, folder_path, index):
    """Download a single image"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(img_url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()
        
        # Determine file extension
        content_type = response.headers.get('content-type', '')
        if 'png' in content_type:
            ext = '.png'
        elif 'gif' in content_type:
            ext = '.gif'
        elif 'webp' in content_type:
            ext = '.webp'
        else:
            ext = '.jpg'
        
        # Get filename from URL or use index
        url_filename = os.path.basename(urlparse(img_url).path)
        if url_filename and '.' in url_filename:
            filename = f"{index:02d}_{url_filename}"
        else:
            filename = f"{index:02d}_image{ext}"
        
        # Sanitize filename
        filename = re.sub(r'[^\w\-\.]', '_', filename)
        filepath = os.path.join(folder_path, filename)
        
        # Save image
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        
        return filepath
    except Exception as e:
        print(f"    ✗ Failed to download image: {e}")
        return None

def process_car_from_url(driver, url, base_output_folder="scraped_cars"):
    """Process a single car: scrape details, save JSON, download images"""
    try:
        # Scrape car details
        car_data = scrape_car_details(driver, url)
        
        if car_data is None:
            return {
                'url': url,
                'status': 'failed',
                'error': 'Failed to scrape data'
            }
        
        # Create folder name from car model
        car_model = extract_car_model_from_url(url)
        car_folder = os.path.join(base_output_folder, car_model)
        images_folder = os.path.join(car_folder, "images")
        os.makedirs(images_folder, exist_ok=True)
        
        # Download images
        print(f"\nDownloading {len(car_data.get('images', []))} images...")
        downloaded_images = []
        
        # Extract images from page
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        image_urls = []
        
        for img in soup.select('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy')
            if src:
                if any(skip in src.lower() for skip in ['icon', 'logo', 'sprite', 'avatar', 'svg']):
                    continue
                full_url = urljoin(base_url, src)
                if full_url not in image_urls:
                    image_urls.append(full_url)
        
        print(f"Found {len(image_urls)} images to download")
        
        for idx, img_url in enumerate(image_urls, 1):
            print(f"  [{idx}/{len(image_urls)}] Downloading...", end=" ")
            filepath = download_image(img_url, images_folder, idx)
            if filepath:
                downloaded_images.append(filepath)
                print(f"✓ {os.path.basename(filepath)}")
            time.sleep(0.3)  # Be polite
        
        car_data['downloaded_images'] = downloaded_images
        car_data['download_count'] = len(downloaded_images)
        
        # Save JSON
        json_path = os.path.join(car_folder, "car_data.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(car_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Saved data to: {json_path}")
        print(f"✓ Downloaded {len(downloaded_images)} images to: {images_folder}")
        
        return {
            'url': url,
            'status': 'success',
            'car_model': car_model,
            'json_path': json_path,
            'images_folder': images_folder,
            'images_downloaded': len(downloaded_images)
        }
        
    except Exception as e:
        print(f"\n✗ Error processing {url}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'url': url,
            'status': 'failed',
            'error': str(e)
        }

def scrape_all_cars_from_excel(excel_file="yango_dubai_cars.xlsx", 
                                output_folder="scraped_cars",
                                headless=True):
    """
    Main function: Read Excel, scrape each URL, save JSON and images
    """
    print(f"\n{'='*70}")
    print(f"SCRAPING CARS FROM EXCEL FILE")
    print(f"{'='*70}\n")
    print(f"Excel file: {excel_file}")
    print(f"Output folder: {output_folder}")
    print(f"Headless mode: {headless}\n")
    
    # Read Excel file
    try:
        df = pd.read_excel(excel_file)
        print(f"✓ Loaded Excel file: {len(df)} rows")
    except Exception as e:
        print(f"✗ Error reading Excel file: {e}")
        return
    
    # Check if 'url' column exists
    if 'url' not in df.columns:
        print(f"✗ Error: 'url' column not found in Excel file")
        print(f"Available columns: {', '.join(df.columns)}")
        return
    
    # Get all URLs
    urls = df['url'].dropna().tolist()
    print(f"✓ Found {len(urls)} URLs to scrape\n")
    
    if len(urls) == 0:
        print("✗ No URLs found in the 'url' column")
        return
    
    # Setup driver
    driver = None
    results = []
    
    try:
        print("Setting up Chrome driver...")
        driver = setup_driver(headless=headless)
        print("✓ Driver ready\n")
        
        # Process each URL
        for idx, url in enumerate(urls, 1):
            print(f"\n{'#'*70}")
            print(f"PROCESSING CAR {idx}/{len(urls)}")
            print(f"{'#'*70}")
            
            result = process_car_from_url(driver, url, output_folder)
            results.append(result)
            
            # Small delay between cars
            time.sleep(2)
        
        # Save summary
        summary_df = pd.DataFrame(results)
        summary_path = os.path.join(output_folder, "scraping_summary.xlsx")
        summary_df.to_excel(summary_path, index=False)
        
        print(f"\n{'='*70}")
        print(f"SCRAPING COMPLETE!")
        print(f"{'='*70}")
        print(f"Total cars processed: {len(results)}")
        print(f"Successful: {sum(1 for r in results if r['status'] == 'success')}")
        print(f"Failed: {sum(1 for r in results if r['status'] == 'failed')}")
        print(f"\nSummary saved to: {summary_path}")
        print(f"All data saved in: {output_folder}/")
        print(f"{'='*70}\n")
        
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            print("Closing browser...")
            driver.quit()

if __name__ == "__main__":
    # Run the scraper
    scrape_all_cars_from_excel(
        excel_file="yango_dubai_cars.xlsx",
        output_folder="scraped_cars",
        headless=False  # Set to True to hide browser
    )