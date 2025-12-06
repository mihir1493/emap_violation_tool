# EMAP_VIOLATION_TOOL
A simple tool to flag 3P across ecommerce websites
Issue: Unauthorized 3rd-party resellers buy products in bulk (often from Costco, Sam’s Club, or regional distributors) and then resell them on Amazon, eBay, Walmart.com, etc. undercutting official pricing and damaging brand equity.

### Overview 
![logic](https://github.com/mihir1493/emap_violation_tool/blob/main/emap_violation_overview.png)

### How to replicate:
1. Create a virtual environment and install the necessary packages
2. Run >> python amazon_scraper.py "search term" >> script with the kewyord which populates a csv and folder with images for each ASIN present on the 1st page results (note: edit the script to use SERP API or 3rd party scraper to avoid blocking and cycle through as many search pages as you wish)
3. Flag the 3P retailers that are not allowed to sell your items (usually avaliable through a internal reseller authorization policy)
4. Edge Cases >> Run image_similarity_model_build.py to extract features and use search.py to perform similarity search on test images
   * Certain sellers avoid using brand keywords and mentions to evade delisting - essentially modifying product images to distort or hide brand logos.
   * To counter these we train a simple image model to classify and flag ASINs that use/sell our brand products
   * To accomplish this we use a VGG16 model to train on a folder that has our official brand/product images - in this case you can use extract.pics website to obtain bulk images for training
   * This feature vector loaded in the model file is use to estimate item similarity (cosine) against the ASIN that weren't flaged as a part of step 3
   * Loop the process for ASIN and each image in the scraped folder
   * Specify a similairty threshold to flag those images as brand - once done apply a simple logic - where ASIN is flagged as Brand but Seller not in RAP - Flag and report those sellers
6. Optional - Deployment and Automated Reporting using the listed platform specific policies

