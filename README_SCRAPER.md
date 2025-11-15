# Amazon Direct Scraper

A Python-based web scraper that searches Amazon for a given search term and extracts detailed product information from the first page results.

## Features

- Searches Amazon for any search term
- Extracts up to 60 products from the first page of results
- Visits each product page individually to extract detailed information
- Downloads all product images and organizes them in folders by ASIN
- Exports all data to CSV format

## Extracted Data

For each product, the scraper extracts:

- **Product Title** - Full product name
- **Brand** - Product brand/manufacturer
- **Price** - Current listing price
- **Rating** - Average customer rating
- **Reviews Count** - Total number of reviews
- **Main Seller** - Primary seller name
- **Other Sellers** - Additional sellers (if available)
- **Product Images** - All available product images
- **ASIN** - Amazon Standard Identification Number
- **Product URL** - Direct link to the product page

## Requirements

- Python 3.8+
- Chrome/Chromium browser installed
- ChromeDriver (automatically managed by Selenium)

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements_scraper.txt
```

2. Ensure Chrome browser is installed on your system

## Usage

Run the scraper with a search term:

```bash
python amazon_scraper.py "your search term"
```

### Examples

```bash
# Search for uncrustables
python amazon_scraper.py uncrustables

# Search for wireless headphones
python amazon_scraper.py "wireless headphones"

# Search for gaming laptop
python amazon_scraper.py "gaming laptop"
```

## Output

The scraper creates:

1. **CSV File** (`amazon_scraper_results.csv`) - Contains all extracted product data
2. **Images Folder** (`images/`) - Organized subfolders by ASIN containing product images

### Folder Structure

```
ecom_violation_agent/
├── amazon_scraper.py
├── requirements_scraper.txt
├── amazon_scraper_results.csv
└── images/
    ├── B07XYZ1234/
    │   ├── B07XYZ1234_0.jpg
    │   ├── B07XYZ1234_1.jpg
    │   └── B07XYZ1234_2.jpg
    └── B08ABC5678/
        ├── B08ABC5678_0.jpg
        └── B08ABC5678_1.jpg
```

## Configuration

You can modify these settings in the script:

- `PAGE_LOAD_TIMEOUT` - Maximum time to wait for page load (default: 15 seconds)
- `ELEMENT_WAIT_TIMEOUT` - Maximum time to wait for elements (default: 10 seconds)
- `REQUEST_DELAY` - Delay between product page requests (default: 2 seconds)
- `BASE_URL` - Amazon domain (default: amazon.com)

## Notes

- The scraper uses headless Chrome to avoid displaying the browser window
- Random delays are added between requests to be respectful to Amazon's servers
- The scraper extracts up to 60 products from the first search results page
- Image files are named using the format: `{ASIN}_{index}.jpg`

## Limitations

- Only scrapes the first page of search results
- May be affected by Amazon's anti-bot measures
- Requires stable internet connection
- Some product data may be missing depending on Amazon's page structure

## Troubleshooting

**Issue**: ChromeDriver not found
**Solution**: The latest version of Selenium automatically manages ChromeDriver. Ensure you have Chrome browser installed.

**Issue**: No products found
**Solution**: Try a different search term or check your internet connection. Amazon may also be blocking automated requests.

**Issue**: Missing data fields
**Solution**: Amazon's page structure varies by product. Some fields may not be available for all products.

## Legal Notice

This scraper is for educational purposes only. Please review Amazon's Terms of Service and robots.txt before using this tool. Be respectful of Amazon's servers by:

- Adding appropriate delays between requests
- Not running the scraper excessively
- Using the data responsibly

## Comparison with SerpAPI Version

Unlike the original `main.py` which uses SerpAPI (paid service), this scraper:

- ✅ Directly scrapes Amazon (no API costs)
- ✅ Visits actual product pages for more detailed data
- ✅ Extracts more seller information
- ✅ Downloads full-resolution images
- ❌ May be subject to rate limiting
- ❌ Requires Chrome browser installation
- ❌ Slower due to page loads
