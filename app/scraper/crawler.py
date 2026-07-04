import json
import time
from pathlib import Path
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

# ----------------------------
# CONFIGURATION
# ----------------------------
homepage = "https://www.webkeyindia.com/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ----------------------------
# STEP 1 & 2: Open Homepage and Collect Links
# ----------------------------
all_urls = []
try:
    print(f"Opening homepage: {homepage}")
    response = requests.get(homepage, headers=headers, timeout=10)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a")
        
        for link in links:
            href = link.get("href")
            if href:
                # Convert relative URLs to absolute URLs (e.g. "/about" -> "https://.../about")
                full_url = urljoin(homepage, href)
                
                if (
                    "webkeyindia.com" in full_url
                    and "#" not in full_url
                    and "tel:" not in full_url
                    and "mailto:" not in full_url
                ):
                    all_urls.append(full_url)
                    
        # Remove duplicates
        all_urls = list(set(all_urls))
except Exception as e:
    print(f"Error loading homepage: {e}")

print(f"\nTotal Unique URLs Found: {len(all_urls)}")

# ----------------------------
# STEP 3 & 4: Loop Through and Scrape Text
# ----------------------------
pages = []

for url in all_urls:
    try:
        print(f"Scraping: {url}")
        
        # 2-second buffer to mimic your original delay
        time.sleep(2) 
        
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            page_soup = BeautifulSoup(res.text, "html.parser")
            
            # Extract title
            page_title = page_soup.title.string if page_soup.title else ""
            
            # Extract plain text from the <body> tag (removes HTML tags and scripts)
            if page_soup.body:
                page_text = page_soup.body.get_text(separator=" ", strip=True)
            else:
                page_text = page_soup.get_text(separator=" ", strip=True)

            pages.append({
                "url": url,
                "title": page_title.strip() if page_title else "",
                "content": page_text
            })
        else:
            print(f"Skipped {url} (Status Code: {res.status_code})")
            
    except Exception as e:
        print(f"Error scraping {url}: {e}")

# ----------------------------
# STEP 5: Finish & Save
# ----------------------------
output_file = Path("data/raw/pages.json")
output_file.parent.mkdir(parents=True, exist_ok=True)

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(pages, f, indent=4, ensure_ascii=False)

print(f"\nSaved {len(pages)} pages to {output_file}")