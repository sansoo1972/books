import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
from ebooklib import epub
import time
import sys
import re
import logging
from urllib.parse import urljoin

# ========== Logging Setup ==========
logging.basicConfig(
    filename='literotica_scraper.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logging.getLogger('').addHandler(console)

headers = {
    "User-Agent": "Mozilla/5.0"
}

# ========== Scraper Functions ==========
def get_page(url):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.RequestException as e:
        logging.error(f"Failed to fetch: {url}")
        logging.exception(e)
        raise

def extract_story_text(soup):
    story_div = soup.find('div', class_='panel article aa_eQ')
    if not story_div:
        logging.warning("Story div not found.")
        return ""
    paragraphs = story_div.find_all('p')
    return "\n\n".join(p.get_text(strip=True) for p in paragraphs)

def find_next_page(soup):
    pagination = soup.find('div', class_='panel clearfix l_bH')
    if not pagination:
        return None
    next_link = pagination.find('a', title='Next Page')
    return urljoin("https://www.literotica.com", next_link['href']) if next_link else None

def extract_title(soup):
    title_tag = soup.find('h1', class_='j_bm headline j_eQ')
    return title_tag.text.strip() if title_tag else "Story"

def sanitize_filename(name):
    return "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).rstrip()

# ========== Save Functions ==========
def save_as_txt(title, content, filename):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"{title}\n\n{content}")
        logging.info(f"Saved TXT: {filename}")
    except Exception as e:
        logging.error("TXT save failed")
        logging.exception(e)

def save_as_pdf(title, content, filename):
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
        logging.info(f"Saved PDF: {filename}")
    except Exception as e:
        logging.error("PDF save failed")
        logging.exception(e)

def save_as_epub(title, content, filename):
    try:
        book = epub.EpubBook()
        book.set_title(title)
        book.add_author("Unknown")

        chapter = epub.EpubHtml(title=title, file_name='chap_1.xhtml', lang='en')
        html_paragraphs = "".join(f"<p>{line.strip()}</p>" for line in content.split("\n\n"))
        chapter.content = f"<h1>{title}</h1>{html_paragraphs}"

        book.add_item(chapter)
        book.toc = (epub.Link('chap_1.xhtml', title, 'chap_1'),)
        book.spine = ['nav', chapter]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        epub.write_epub(filename, book)
        logging.info(f"Saved EPUB: {filename}")
    except Exception as e:
        logging.error("EPUB save failed")
        logging.exception(e)

# ========== Utility ==========
def is_valid_literotica_url(url):
    pattern = r"^https:\/\/www\.literotica\.com\/s\/[a-zA-Z0-9-]+"
    if not re.match(pattern, url):
        return False
    try:
        r = requests.head(url, headers=headers, timeout=5)
        return r.status_code == 200
    except Exception:
        return False

def get_story_url():
    if len(sys.argv) > 1:
        input_url = sys.argv[1]
    else:
        input_url = ""
    while not is_valid_literotica_url(input_url):
        if input_url:
            print("❌ Invalid or unreachable URL. Try again.")
        input_url = input("Enter Literotica story URL: ").strip()
    return input_url

def get_output_format():
    print("\nSelect output format:")
    print("1) TXT")
    print("2) PDF")
    print("3) EPUB")
    choice = ""
    while choice not in ("1", "2", "3"):
        choice = input("Enter choice (1/2/3): ").strip()
    return choice

# ========== Main ==========
def main():
    try:
        start_url = get_story_url()
        format_choice = get_output_format()

        logging.info(f"Starting scrape: {start_url}")
        soup = get_page(start_url)
        title = extract_title(soup)
        safe_title = sanitize_filename(title)

        full_story = ""
        current_url = start_url
        page_num = 1

        while current_url:
            logging.info(f"Page {page_num}: {current_url}")
            soup = get_page(current_url)
            full_story += extract_story_text(soup) + "\n\n"
            current_url = find_next_page(soup)
            page_num += 1
            time.sleep(1)

        if format_choice == "1":
            save_as_txt(title, full_story, f"{safe_title}.txt")
        elif format_choice == "2":
            save_as_pdf(title, full_story, f"{safe_title}.pdf")
        elif format_choice == "3":
            save_as_epub(title, full_story, f"{safe_title}.epub")

        print("\n✅ Done!")
        logging.info("Scraping complete.")

    except Exception as e:
        logging.error("Fatal error.")
        logging.exception(e)
        print("\n❌ Something went wrong. See 'literotica_scraper.log' for details.")

if __name__ == "__main__":
    main()