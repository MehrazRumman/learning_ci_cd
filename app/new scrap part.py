# to get the car list first 
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import re
from datetime import datetime

def setup_driver(headless=True):
    """Setup Chrome driver with appropriate options"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def click_show_more_button(driver):
    """Click 'Show More Results' button if it exists"""
    print("Looking for 'Show More Results' button...")
    
    # Try multiple possible selectors for the button
    button_selectors = [
        "button:contains('Show more results')",
        "button:contains('show more')",
        "button:contains('Show More')",
        "button:contains('Load more')",
        "button:contains('More results')",
        "[class*='show-more']",
        "[class*='load-more']",
        "[class*='ShowMore']",
        "button[class*='more']",
        "//button[contains(text(), 'Show more')]",
        "//button[contains(text(), 'show more')]",
        "//button[contains(text(), 'More')]",
        "//button[contains(., 'more')]",
        "//div[contains(text(), 'Show more')]",
        "//span[contains(text(), 'Show more')]"
    ]
    
    for selector in button_selectors:
        try:
            if selector.startswith("//"):
                # XPath selector
                button = driver.find_element(By.XPATH, selector)
            else:
                # CSS selector
                button = driver.find_element(By.CSS_SELECTOR, selector)
            
            if button and button.is_displayed() and button.is_enabled():
                print(f"✓ Found 'Show More' button with selector: {selector}")
                # Scroll to button
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                time.sleep(8)
                # Click the button
                try:
                    button.click()
                    print("✓ Clicked 'Show More Results' button")
                    time.sleep(8)  # Wait for content to load
                    return True
                except:
                    # If regular click fails, try JavaScript click
                    driver.execute_script("arguments[0].click();", button)
                    print("✓ Clicked 'Show More Results' button (via JavaScript)")
                    time.sleep(8)
                    return True
        except Exception as e:
            continue
    
    print("⚠ 'Show More Results' button not found")
    return False

def scroll_to_load_all_cars(driver, max_scrolls=320, scroll_pause=8, target_links=3700):
    """Scroll the page to load all dynamically loaded cars"""
    print("Scrolling to load all cars...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    scrolls = 0
    
    while scrolls < max_scrolls:
        # car_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/rent-cars/"]')
        # unique_links = set([l.get_attribute('href') for l in car_links if l.get_attribute('href')])
        # print(f"  Found {len(unique_links)} unique car links so far...")

        # # ✅ Stop if we have reached or exceeded target
        # if len(unique_links) >= target_links:
        #     print(f"✅ Reached target of {target_links} car links. Stopping scroll.")
        #     break
        # Scroll down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause)
        
        # Calculate new scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        if new_height == last_height:
            # Try one more time to be sure
            time.sleep(scroll_pause)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
        
        last_height = new_height
        scrolls += 1
        print(f"  Scroll {scrolls}/{max_scrolls}...")
    
    print(f"✓ Finished scrolling after {scrolls} scrolls")

def extract_car_cards(driver):
    """Extract car information from the loaded page"""
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    cars_data = []
    
    # Try multiple selectors that might contain car cards
    possible_selectors = [
        'a[href*="/rent-cars/"]',
        'div[class*="car"]',
        'div[class*="vehicle"]',
        'article',
        '[class*="card"]',
        '[data-testid*="car"]'
    ]
    
    # Find all clickable car links
    car_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/rent-cars/"]')
    
    print(f"Found {len(car_links)} car links")
    
    for idx, link in enumerate(car_links):
        try:
            # Get the URL
            url = link.get_attribute('href')
            
            # IMPORTANT: Only accept URLs with object_id parameter
            # Format: /rent-cars/category/brand/model?object_id=xxxxx
            if 'object_id=' not in url:
                continue
            
            # Must have proper structure: /rent-cars/category/brand/model
            # Skip if it's just the main page or category page
            if url.endswith('/rent-cars') or url.count('/') < 7:
                continue
            
            # Extract visible text from the link element
            text = link.text.strip()
            
            # Get the HTML of this element for more detailed parsing
            html = link.get_attribute('innerHTML')
            soup_elem = BeautifulSoup(html, 'html.parser')
            
            # Try to extract details
            car_info = {
                'index': idx + 1,
                'url': url,
                'car_name': '',
                'price': '',
                'category': '',
                'seats': '',
                'year': '',
                'transmission': '',
                'features': '',
                'full_text': text
            }
            
            # Extract car name from URL
            url_parts = url.split('?')[0].split('/')  # Remove query params first
            if len(url_parts) >= 3:
                # Format: .../category/brand/model
                brand = url_parts[-2] if len(url_parts) > 1 else ''
                model = url_parts[-1] if url_parts else ''
                category = url_parts[-3] if len(url_parts) > 2 else ''
                car_info['car_name'] = f"{brand.title()} {model.title()}".strip()
                car_info['category'] = category.title()
            
            # Try to find price
            price_patterns = [
                r'AED\s*[\d,]+',
                r'\d+\s*/\s*day',
                r'[\d,]+\s*AED',
                r'from\s*[\d,]+'
            ]
            for pattern in price_patterns:
                price_match = re.search(pattern, text, re.IGNORECASE)
                if price_match:
                    car_info['price'] = price_match.group(0)
                    break
            
            # Try to find seats
            seats_match = re.search(r'(\d+)\s*seat', text, re.IGNORECASE)
            if seats_match:
                car_info['seats'] = seats_match.group(1)
            
            # Try to find year
            year_match = re.search(r'20\d{2}', text)
            if year_match:
                car_info['year'] = year_match.group(0)
            
            # Check for transmission type
            if 'automatic' in text.lower():
                car_info['transmission'] = 'Automatic'
            elif 'manual' in text.lower():
                car_info['transmission'] = 'Manual'
            
            # Extract features (AC, GPS, etc.)
            features = []
            feature_keywords = ['AC', 'GPS', 'Bluetooth', 'USB', 'Camera', 'Cruise']
            for keyword in feature_keywords:
                if keyword.lower() in text.lower():
                    features.append(keyword)
            car_info['features'] = ', '.join(features)
            
            cars_data.append(car_info)
            
        except Exception as e:
            print(f"  Error extracting car {idx}: {e}")
            continue
    
    return cars_data

def scrape_yango_cars(url="https://drive.yango.com/uae/dubai/rent-cars", 
                      output_file="yango_cars.xlsx",
                      headless=True,
                      max_scrolls=320):
    """
    Main function to scrape Yango car rental listings and save to Excel
    """
    print(f"\n{'='*70}")
    print(f"Yango Cars Scraper")
    print(f"{'='*70}\n")
    print(f"Target URL: {url}")
    print(f"Output file: {output_file}")
    print(f"Headless mode: {headless}\n")
    
    driver = None
    try:
        # Setup driver
        print("Setting up Chrome driver...")
        driver = setup_driver(headless=headless)
        
        # Load the page
        print(f"Loading page: {url}")
        driver.get(url)
        
        # Wait for page to load
        print("Waiting for page to load...")
        time.sleep(8)  # Initial load
        
        # Try to wait for car elements to appear
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/rent-cars/"]'))
            )
            print("✓ Page loaded successfully")
        except Exception as e:
            print(f"⚠ Warning: Timeout waiting for cars, but continuing anyway...")
        
        # IMPORTANT: Click "Show More Results" button first
        click_show_more_button(driver)
        
        # Scroll to load all cars
        scroll_to_load_all_cars(driver, max_scrolls=max_scrolls)
        
        # Extract car data
        print("\nExtracting car information...")
        cars_data = extract_car_cards(driver)
        
        if not cars_data:
            print("\n⚠ No cars found. The page structure might have changed.")
            print("Saving page source for debugging...")
            with open("page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("✓ Page source saved to page_source.html")
            return None
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_cars = []
        for car in cars_data:
            if car['url'] not in seen_urls:
                seen_urls.add(car['url'])
                unique_cars.append(car)
        
        print(f"✓ Extracted {len(unique_cars)} unique cars with object_id (removed {len(cars_data) - len(unique_cars)} duplicates)")
        
        # Create DataFrame
        df = pd.DataFrame(unique_cars)
        
        # Add metadata
        df['scraped_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Reorder columns
        column_order = ['index', 'car_name', 'category', 'price', 'seats', 
                       'year', 'transmission', 'features', 'url', 'scraped_at']
        
        # Only include columns that exist
        column_order = [col for col in column_order if col in df.columns]
        df = df[column_order]
        
        # Save to Excel
        print(f"\nSaving to Excel: {output_file}")
        df.to_excel(output_file, index=False, sheet_name='Cars')
        
        print(f"\n{'='*70}")
        print(f"✓ SUCCESS! Scraped {len(df)} cars")
        print(f"✓ Data saved to: {output_file}")
        print(f"{'='*70}\n")
        
        # Print sample
        print("Sample data (first 5 cars):")
        print(df.head().to_string())
        
        return df
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        if driver:
            print("\nClosing browser...")
            driver.quit()

def scrape_yango_cars_simple(output_file="yango_cars.xlsx"):
    """
    Simplified version with default settings
    """
    return scrape_yango_cars(
        url="https://drive.yango.com/uae/dubai/rent-cars",
        output_file=output_file,
        headless=False,  # Set to False to see the browser
        max_scrolls=320
    )

if __name__ == "__main__":
    # Run the scraper
    df = scrape_yango_cars_simple("yango_dubai_cars.xlsx")
    
    if df is not None:
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"Total cars scraped: {len(df)}")
        print(f"Categories: {df['category'].value_counts().to_dict() if 'category' in df.columns else 'N/A'}")
        print(f"Price range: {df['price'].iloc[0] if len(df) > 0 and 'price' in df.columns else 'N/A'}")
        print("="*70)