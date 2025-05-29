import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import time
import sys
import re
import logging
from urllib.parse import urljoin

# Set up logging
logging.basicConfig(
    filename='literotica_scraper.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s: %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

# Use a user-agent header to simulate a real browser
headers = {
    "User-Agent": "Mozilla/5.0"
}

def get_page(url):
    """Fetch and parse a web page from the given URL."""
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.RequestException as e:
        logging.error(f"Failed to fetch page: {url}")
        logging.exception(e)
        raise

def extract_story_text(soup):
    """Extract and return all paragraph text from the story content div."""
    story_div = soup.find('div', class_='panel article aa_eQ')
    if not story_div:
        logging.warning("Could not find story content on this page.")
        return ""
    paragraphs = story_div.find_all('p')
    story_text = ""
    for p in paragraphs:
        story_text += p.get_text(strip=True) + "\n\n"
    return story_text

def find_next_page(soup):
    """Find the URL of the next page in a multi-page story."""
    pagination = soup.find('div', class_='panel clearfix l_bH')
    if not pagination:
        return None
    next_link = pagination.find('a', title='Next Page')
    if next_link and 'href' in next_link.attrs:
        return urljoin("https://www.literotica.com", next_link['href'])
    return None

def extract_title(soup):
    """Extract the story title from the H1 tag."""
    title_tag = soup.find('h1', class_='j_bm headline j_eQ')
    return title_tag.text.strip() if title_tag else "Story"

def sanitize_filename(name):
    """Sanitize a string to be used safely as a filename."""
    return "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).rstrip()

def save_as_txt(title, content, filename):
    """Save story content as a plain text file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"{title}\n\n{content}")
        logging.info(f"Saved text file: {filename}")
    except Exception as e:
        logging.error("Failed to save .txt file")
        logging.exception(e)

def save_as_pdf(title, content, filename):
    """Save story content as a PDF file."""
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.multi_cell(0, 10, title)
        pdf.ln(10)

        pdf.set_font("Arial", '', 12)
        for paragraph in content.split("\n\n"):
            pdf.multi_cell(0, 10, paragraph)
            pdf.ln()
        pdf.output(filename)
        logging.info(f"Saved PDF file: {filename}")
    except Exception as e:
        logging.error("Failed to save PDF")
        logging.exception(e)

def is_valid_literotica_url(url):
    """Check if the URL matches the Literotica story pattern and is reachable."""
    pattern = r"^https:\/\/www\.literotica\.com\/s\/[a-zA-Z0-9-]+"
    if not re.match(pattern, url):
        return False
    try:
        r = requests.head(url, headers=headers, allow_redirects=True, timeout=5)
        return r.status_code == 200
    except Exception:
        return False

def get_story_url():
    """Prompt the user for a valid Literotica story URL if none is passed via CLI."""
    if len(sys.argv) > 1:
        input_url = sys.argv[1]
    else:
        input_url = ""

    while not is_valid_literotica_url(input_url):
        if input_url:
            print("❌ Invalid or unreachable URL. Please try again.")
        input_url = input("Enter a valid Literotica story URL (e.g., https://www.literotica.com/s/example-title): ").strip()
    return input_url

def main():
    try:
        start_url = get_story_url()
        logging.info(f"Starting to scrape: {start_url}")

        soup = get_page(start_url)
        title = extract_title(soup)
        safe_title = sanitize_filename(title)

        full_story = ""
        current_url = start_url
        page_num = 1

        while current_url:
            logging.info(f"Fetching page {page_num}: {current_url}")
            soup = get_page(current_url)
            full_story += extract_story_text(soup)
            next_page = find_next_page(soup)
            if next_page == current_url:
                break
            current_url = next_page
            page_num += 1
            time.sleep(1)  # Be kind to the server

        txt_file = f"{safe_title}.txt"
        pdf_file = f"{safe_title}.pdf"

        save_as_txt(title, full_story, txt_file)
        save_as_pdf(title, full_story, pdf_file)

        print("\n✅ Done!")
        print(f"- Text saved as: {txt_file}")
        print(f"- PDF saved as: {pdf_file}")

    except Exception as e:
        logging.error("An unexpected error occurred during execution.")
        logging.exception(e)
        print("\n❌ An error occurred. Check 'literotica_scraper.log' for details.")
        print("Troubleshooting tips:")
        print("- Make sure the URL is correct and points to a Literotica story.")
        print("- Check your internet connection.")
        print("- Make sure Literotica.com isn't blocking or rate-limiting you.")

if __name__ == "__main__":
    main()