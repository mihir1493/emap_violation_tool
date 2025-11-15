#!/usr/bin/env python3
"""
Amazon Direct Scraper
Searches Amazon for a given term, extracts all products from the first page,
then visits each product page to extract detailed information.

Extracts:
- Product title
- Brand
- Price
- Ratings
- Reviews count
- All product images (stored in images/<ASIN>/)
- Main seller
- All other sellers

Outputs to CSV with all extracted data.
"""

import os
import sys
import time
import csv
import requests
from pathlib import Path
from urllib.parse import urljoin, quote_plus
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from tqdm import tqdm

# ========== CONFIG ==========
SEARCH_TERM = sys.argv[1] if len(sys.argv) > 1 else "jif"
BASE_URL = "https://www.amazon.com"
CSV_PATH = Path("amazon_scraper_results.csv")
IMAGES_DIR = Path("images")
PAGE_LOAD_TIMEOUT = 15
ELEMENT_WAIT_TIMEOUT = 10
REQUEST_DELAY = 2  # seconds between product page loads
# ============================

CSV_FIELDS = [
    "search_term",
    "asin",
    "product_title",
    "brand",
    "price",
    "rating",
    "reviews_count",
    "product_url",
    "main_seller",
    "other_sellers",  # semicolon-separated
    "product_description",
    "best_sellers_rank",
    "image_files"     # semicolon-separated local paths
]

IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def setup_driver():
    """Setup Chrome driver with options to avoid detection."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    return driver


def extract_asin_from_url(url):
    """Extract ASIN from Amazon product URL."""
    if not url:
        return None

    # Common patterns: /dp/ASIN or /gp/product/ASIN
    parts = url.split("/")
    for i, part in enumerate(parts):
        if part in ["dp", "product"] and i + 1 < len(parts):
            asin = parts[i + 1].split("?")[0].split("/")[0]
            if len(asin) == 10:
                return asin
    return None


def search_amazon(driver, search_term):
    """Search Amazon and return list of product URLs from first page."""
    search_url = f"{BASE_URL}/s?k={quote_plus(search_term)}"
    print(f"[info] Searching Amazon for: '{search_term}'")
    print(f"[info] URL: {search_url}")

    driver.get(search_url)
    time.sleep(3)  # Wait for page to load

    product_urls = []

    # Try multiple selectors for product links
    selectors = [
        "div[data-component-type='s-search-result'] h2 a",
        "div.s-result-item h2 a",
        "a.s-link-style.a-text-normal"
    ]

    for selector in selectors:
        try:
            products = driver.find_elements(By.CSS_SELECTOR, selector)
            if products:
                for product in products:
                    try:
                        url = product.get_attribute("href")
                        if url and "/dp/" in url:
                            product_urls.append(url)
                    except:
                        continue
                break
        except:
            continue

    # Remove duplicates while preserving order
    seen = set()
    unique_urls = []
    for url in product_urls:
        asin = extract_asin_from_url(url)
        if asin and asin not in seen:
            seen.add(asin)
            unique_urls.append(url)

    print(f"[info] Found {len(unique_urls)} unique products on first page")
    return unique_urls[:60]  # Return up to 60 products


def download_images(asin, image_urls):
    """Download product images to images/<ASIN>/ folder."""
    saved = []
    outdir = IMAGES_DIR / asin
    outdir.mkdir(parents=True, exist_ok=True)

    for i, url in enumerate(image_urls):
        if not url:
            continue
        try:
            # Clean up the URL - remove size constraints for high-res images
            url = url.split("._")[0] + ".jpg" if "._" in url else url

            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            resp = requests.get(url, timeout=10, headers=headers)

            if resp.status_code == 200:
                ext = ".jpg"
                fname = outdir / f"{asin}_{i}{ext}"
                with open(fname, "wb") as f:
                    f.write(resp.content)
                saved.append(str(fname))
        except Exception as e:
            print(f"[warning] Failed to download image {i} for {asin}: {str(e)}")
            continue
        time.sleep(0.1)

    return saved


def extract_product_details(driver, product_url):
    """Visit product page and extract all required details."""
    asin = extract_asin_from_url(product_url)

    print(f"[info] Scraping product: {asin}")

    try:
        driver.get(product_url)
        time.sleep(2)  # Wait for page to load
    except Exception as e:
        print(f"[error] Failed to load {product_url}: {str(e)}")
        return None

    data = {
        "asin": asin,
        "product_url": product_url,
        "product_title": None,
        "brand": None,
        "price": None,
        "rating": None,
        "reviews_count": None,
        "main_seller": None,
        "other_sellers": [],
        "product_description": None,
        "best_sellers_rank": None,
        "images": []
    }

    # Extract product title
    try:
        title_selectors = [
            "span#productTitle",
            "h1#title span",
            "h1.a-size-large.product-title-word-break"
        ]
        for selector in title_selectors:
            try:
                title = driver.find_element(By.CSS_SELECTOR, selector)
                data["product_title"] = title.text.strip()
                if data["product_title"]:
                    break
            except:
                continue
    except Exception as e:
        print(f"[warning] Could not extract title: {str(e)}")

    # Extract brand
    try:
        brand_selectors = [
            "a#bylineInfo",
            "div#bylineInfo",
            "a.a-link-normal#brand",
            "tr.po-brand td.a-span9 span"
        ]
        for selector in brand_selectors:
            try:
                brand = driver.find_element(By.CSS_SELECTOR, selector)
                brand_text = brand.text.strip()
                # Remove "Visit the", "Brand:", etc.
                brand_text = brand_text.replace("Visit the ", "").replace("Brand: ", "").replace(" Store", "")
                data["brand"] = brand_text
                if data["brand"]:
                    break
            except:
                continue
    except Exception as e:
        print(f"[warning] Could not extract brand: {str(e)}")

    # Extract price
    try:
        price_selectors = [
            "span.a-price.aok-align-center span.a-offscreen",
            "span.a-price span.a-offscreen",
            "span#priceblock_ourprice",
            "span#priceblock_dealprice",
            "span.a-price-whole"
        ]
        for selector in price_selectors:
            try:
                price = driver.find_element(By.CSS_SELECTOR, selector)
                data["price"] = price.text.strip()
                if data["price"]:
                    break
            except:
                continue
    except Exception as e:
        print(f"[warning] Could not extract price: {str(e)}")

    # Extract rating
    try:
        rating_selectors = [
            "span.a-icon-alt",
            "i.a-icon-star span",
            "span[data-hook='rating-out-of-text']"
        ]
        for selector in rating_selectors:
            try:
                rating = driver.find_element(By.CSS_SELECTOR, selector)
                rating_text = rating.text.strip()
                if "out of 5" in rating_text:
                    data["rating"] = rating_text.split()[0]
                    break
            except:
                continue
    except Exception as e:
        print(f"[warning] Could not extract rating: {str(e)}")

    # Extract reviews count
    try:
        reviews_selectors = [
            "span#acrCustomerReviewText",
            "a#acrCustomerReviewLink span",
            "div#averageCustomerReviews span[data-hook='total-review-count']"
        ]
        for selector in reviews_selectors:
            try:
                reviews = driver.find_element(By.CSS_SELECTOR, selector)
                reviews_text = reviews.text.strip()
                # Extract number from "1,234 ratings" or "1,234"
                data["reviews_count"] = reviews_text.split()[0].replace(",", "")
                if data["reviews_count"]:
                    break
            except:
                continue
    except Exception as e:
        print(f"[warning] Could not extract reviews count: {str(e)}")

    # Extract main seller - Look for "Shipper / Seller" label
    try:
        # Try to find the seller next to "Shipper / Seller" label
        try:
            # Look for the span with "Shipper / Seller" text
            shipper_label = driver.find_elements(By.XPATH, "//span[@class='a-size-small a-color-tertiary' and contains(text(), 'Shipper / Seller')]")
            if shipper_label:
                # Get the next sibling or parent's next element
                parent = shipper_label[0].find_element(By.XPATH, "./..")
                seller_links = parent.find_elements(By.CSS_SELECTOR, "a")
                if seller_links:
                    data["main_seller"] = seller_links[0].text.strip()
        except:
            pass

        # Fallback to other selectors if not found
        if not data["main_seller"]:
            seller_selectors = [
                "div#merchant-info",
                "a#sellerProfileTriggerId",
                "div#tabular-buybox div.tabular-buybox-text[tabular-attribute-name='Sold by'] span",
                "div#tabular-buybox-truncate-0 span"
            ]
            for selector in seller_selectors:
                try:
                    seller = driver.find_element(By.CSS_SELECTOR, selector)
                    seller_text = seller.text.strip()
                    # Clean up text
                    if "Ships from" in seller_text:
                        seller_text = seller_text.split("Ships from")[0].strip()
                    if "Sold by" in seller_text:
                        seller_text = seller_text.split("Sold by")[-1].strip()
                    data["main_seller"] = seller_text
                    if data["main_seller"]:
                        break
                except:
                    continue
    except Exception as e:
        print(f"[warning] Could not extract main seller: {str(e)}")

    # Try to extract other sellers
    try:
        # Look for "X new from $Y" or other seller links
        other_sellers_selectors = [
            "div#mbc a.a-link-normal",
            "a#buybox-see-all-buying-choices",
            "div#all-offers-display a"
        ]

        # Click to see all buying options if available
        try:
            see_all_btn = driver.find_element(By.CSS_SELECTOR, "a#buybox-see-all-buying-choices")
            see_all_btn.click()
            time.sleep(1)

            # Extract seller names from the modal
            seller_elements = driver.find_elements(By.CSS_SELECTOR, "div#aod-offer-soldBy a, div#aod-offer-soldBy span")
            for elem in seller_elements:
                seller_name = elem.text.strip()
                if seller_name and seller_name != data["main_seller"] and seller_name not in data["other_sellers"]:
                    data["other_sellers"].append(seller_name)
        except:
            pass
    except Exception as e:
        print(f"[warning] Could not extract other sellers: {str(e)}")

    # Extract product description
    try:
        description_selectors = [
            "div#feature-bullets ul.a-unordered-list.a-vertical",
            "div#productDescription p",
            "div#productDescription",
            "div#feature-bullets"
        ]
        for selector in description_selectors:
            try:
                desc_elem = driver.find_element(By.CSS_SELECTOR, selector)
                desc_text = desc_elem.text.strip()
                if desc_text and len(desc_text) > 10:  # Make sure we have meaningful content
                    data["product_description"] = desc_text
                    break
            except:
                continue
    except Exception as e:
        print(f"[warning] Could not extract product description: {str(e)}")

    # Extract Best Sellers Rank
    try:
        # Look for the "Best Sellers Rank:" label
        try:
            # Find by exact text match
            rank_elements = driver.find_elements(By.XPATH, "//span[@class='a-text-bold' and contains(text(), 'Best Sellers Rank')]")
            if rank_elements:
                # Get the parent element which contains the full rank text
                parent = rank_elements[0].find_element(By.XPATH, "./..")
                rank_text = parent.text.strip()
                # Remove the "Best Sellers Rank:" label
                rank_text = rank_text.replace("Best Sellers Rank:", "").strip()
                data["best_sellers_rank"] = rank_text
        except:
            pass

        # Fallback: try other selectors
        if not data["best_sellers_rank"]:
            rank_selectors = [
                "li#SalesRank",
                "tr#SalesRank td.value",
                "div#detailBulletsWrapper_feature_div span:contains('Best Sellers Rank')"
            ]
            for selector in rank_selectors:
                try:
                    rank_elem = driver.find_element(By.CSS_SELECTOR, selector)
                    rank_text = rank_elem.text.strip()
                    if "Best Sellers Rank" in rank_text:
                        rank_text = rank_text.replace("Best Sellers Rank:", "").strip()
                    data["best_sellers_rank"] = rank_text
                    if data["best_sellers_rank"]:
                        break
                except:
                    continue
    except Exception as e:
        print(f"[warning] Could not extract Best Sellers Rank: {str(e)}")

    # Extract all product images
    try:
        # Main image
        try:
            main_img = driver.find_element(By.CSS_SELECTOR, "img#landingImage")
            img_url = main_img.get_attribute("src")
            if img_url and img_url not in data["images"]:
                data["images"].append(img_url)
        except:
            pass

        # Thumbnail images
        thumbnail_selectors = [
            "img.a-dynamic-image",
            "div#altImages img",
            "ul.a-unordered-list.a-nostyle img"
        ]

        for selector in thumbnail_selectors:
            try:
                imgs = driver.find_elements(By.CSS_SELECTOR, selector)
                for img in imgs:
                    img_url = img.get_attribute("src")
                    if not img_url:
                        img_url = img.get_attribute("data-old-hires")
                    if img_url and img_url not in data["images"] and "amazon.com/images" in img_url:
                        data["images"].append(img_url)
            except:
                continue
    except Exception as e:
        print(f"[warning] Could not extract images: {str(e)}")

    return data


def main(search_term):
    """Main function to orchestrate the scraping process."""
    driver = setup_driver()
    rows = []

    try:
        # Step 1: Search Amazon and get product URLs
        product_urls = search_amazon(driver, search_term)

        if not product_urls:
            print("[error] No products found!")
            return

        # Step 2: Visit each product page and extract details
        print(f"\n[info] Extracting details from {len(product_urls)} products...")

        for idx, url in enumerate(tqdm(product_urls, desc="Scraping products")):
            try:
                product_data = extract_product_details(driver, url)

                if not product_data:
                    continue

                # Download images
                saved_images = download_images(product_data["asin"], product_data["images"])

                # Create row for CSV
                row = {
                    "search_term": search_term,
                    "asin": product_data["asin"],
                    "product_title": product_data["product_title"],
                    "brand": product_data["brand"],
                    "price": product_data["price"],
                    "rating": product_data["rating"],
                    "reviews_count": product_data["reviews_count"],
                    "product_url": product_data["product_url"],
                    "main_seller": product_data["main_seller"],
                    "other_sellers": ";".join(product_data["other_sellers"]),
                    "product_description": product_data["product_description"],
                    "best_sellers_rank": product_data["best_sellers_rank"],
                    "image_files": ";".join(saved_images)
                }
                rows.append(row)

                print(f"[collected] {product_data['asin']} — {product_data['product_title'][:50]}...")

                # Delay between requests
                time.sleep(REQUEST_DELAY)

            except Exception as e:
                print(f"[error] Failed to process {url}: {str(e)}")
                continue

        # Step 3: Write to CSV
        if rows:
            df = pd.DataFrame(rows, columns=CSV_FIELDS)
            df.to_csv(CSV_PATH, index=False)
            print(f"\n[done] Saved {len(df)} products to {CSV_PATH}")
        else:
            print("[warning] No data was collected!")

    finally:
        driver.quit()
        print("[info] Browser closed")


if __name__ == "__main__":
    print(f"Amazon Direct Scraper")
    print(f"Search term: '{SEARCH_TERM}'")
    print(f"Target: First page products (up to 60)")
    print("=" * 50)
    main(SEARCH_TERM)
