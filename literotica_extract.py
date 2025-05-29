import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
from ebooklib import epub
import time
import sys
import re
import logging
import os
from urllib.parse import urljoin
from pathlib import Path

# ========== Logging Setup ==========
logging.basicConfig(
    filename='literotica_scraper.log',   # Log file path
    level=logging.INFO,                   # Capture INFO and above level logs
    format='%(asctime)s [%(levelname)s] %(message)s',
)
# Also output logs to console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logging.getLogger('').addHandler(console)

# User-Agent header for HTTP requests
headers = {
    "User-Agent": "Mozilla/5.0"
}

# ========== Scraper Functions ==========

def get_page(url):
    """
    Fetch the HTML content of a given URL and parse it with BeautifulSoup.
    
    Args:
        url (str): URL of the page to fetch
    
    Returns:
        BeautifulSoup object representing the HTML content
    
    Raises:
        requests.RequestException on network or HTTP errors
    """
    try:
        logging.info(f"Fetching URL: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses
        return BeautifulSoup(response.text, 'html.parser')
    except requests.RequestException as e:
        logging.error(f"Failed to fetch URL: {url}")
        logging.exception(e)
        raise

def extract_story_text(soup):
    """
    Extract the story text paragraphs from the page soup.
    
    Args:
        soup (BeautifulSoup): Parsed HTML page
    
    Returns:
        str: Concatenated story text paragraphs separated by blank lines
    """
    story_div = soup.find('div', class_='panel article aa_eQ')
    if not story_div:
        logging.warning("Could not find story div on page.")
        return ""
    paragraphs = story_div.find_all('p')
    text = "\n\n".join(p.get_text(strip=True) for p in paragraphs)
    logging.info(f"Extracted {len(paragraphs)} paragraphs from story.")
    return text

def find_next_page(soup):
    """
    Find the URL of the next page in a multi-page story.
    
    Args:
        soup (BeautifulSoup): Parsed HTML page
    
    Returns:
        str or None: Absolute URL of the next page, or None if last page
    """
    pagination_div = soup.find('div', class_='panel clearfix l_bH')
    if not pagination_div:
        logging.info("No pagination div found; assuming single page story.")
        return None
    next_link = pagination_div.find('a', title='Next Page')
    if next_link:
        next_url = urljoin("https://www.literotica.com", next_link['href'])
        logging.info(f"Next page URL found: {next_url}")
        return next_url
    logging.info("No next page link found; reached last page.")
    return None

def extract_title(soup):
    """
    Extract the story title from the page.
    
    Args:
        soup (BeautifulSoup): Parsed HTML page
    
    Returns:
        str: Story title text or fallback if not found
    """
    title_tag = soup.find('h1', class_='j_bm headline j_eQ')
    if title_tag:
        title = title_tag.text.strip()
        logging.info(f"Story title extracted: {title}")
        return title
    logging.warning("Title tag not found; using fallback title.")
    return "Untitled Story"

def sanitize_filename(name):
    """
    Sanitize a string to be safe for use as a filename or folder name.
    
    Args:
        name (str): Input string
    
    Returns:
        str: Sanitized string with only safe characters
    """
    sanitized = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).rstrip()
    logging.debug(f"Sanitized filename: {sanitized}")
    return sanitized

# ========== Save Functions ==========

def save_as_txt(title, content, filename):
    """
    Save story content to a UTF-8 encoded plain text file.
    
    Args:
        title (str): Story title
        content (str): Story text content
        filename (str): Output file path
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"{title}\n\n{content}")
        logging.info(f"TXT saved successfully: {filename}")
    except Exception as e:
        logging.error("Failed to save TXT file.")
        logging.exception(e)

def save_as_pdf(title, content, filename):
    """
    Save story content as a PDF file using fpdf.
    
    Args:
        title (str): Story title
        content (str): Story text content
        filename (str): Output file path
    """
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.multi_cell(0, 10, title)
        pdf.ln(10)
        pdf.set_font("Arial", '', 12)
        # Split content into paragraphs to preserve spacing
        for paragraph in content.split("\n\n"):
            pdf.multi_cell(0, 10, paragraph)
            pdf.ln()
        pdf.output(filename)
        logging.info(f"PDF saved successfully: {filename}")
    except Exception as e:
        logging.error("Failed to save PDF file.")
        logging.exception(e)

def save_as_epub(title, content, filename):
    """
    Save story content as an EPUB file using ebooklib.
    
    Args:
        title (str): Story title
        content (str): Story text content
        filename (str): Output file path
    """
    try:
        book = epub.EpubBook()
        book.set_title(title)
        book.add_author("Unknown")

        # Create one chapter with the full story text
        chapter = epub.EpubHtml(title=title, file_name='chap_1.xhtml', lang='en')
        # Wrap paragraphs in <p> tags for formatting
        html_content = "".join(f"<p>{line.strip()}</p>" for line in content.split("\n\n"))
        chapter.content = f"<h1>{title}</h1>{html_content}"

        book.add_item(chapter)
        book.toc = (epub.Link('chap_1.xhtml', title, 'chap_1'),)
        book.spine = ['nav', chapter]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        epub.write_epub(filename, book)
        logging.info(f"EPUB saved successfully: {filename}")
    except Exception as e:
        logging.error("Failed to save EPUB file.")
        logging.exception(e)

# ========== Utility Functions ==========

def is_valid_literotica_url(url):
    """
    Validate that a URL matches Literotica story pattern and is reachable.
    
    Args:
        url (str): URL string to validate
    
    Returns:
        bool: True if URL is valid and accessible, else False
    """
    pattern = r"^https:\/\/www\.literotica\.com\/s\/[a-zA-Z0-9-]+"
    if not re.match(pattern, url):
        logging.debug("URL pattern does not match Literotica story URL.")
        return False
    try:
        r = requests.head(url, headers=headers, timeout=5)
        if r.status_code == 200:
            return True
        else:
            logging.debug(f"URL returned status code {r.status_code}.")
            return False
    except Exception as e:
        logging.debug(f"Error during HEAD request: {e}")
        return False

def get_story_url():
    """
    Get story URL from CLI argument or prompt user until valid URL provided.
    
    Returns:
        str: Validated story URL
    """
    if len(sys.argv) > 1:
        input_url = sys.argv[1]
    else:
        input_url = ""
    while not is_valid_literotica_url(input_url):
        if input_url:
            print("❌ Invalid or unreachable Literotica story URL. Please try again.")
        input_url = input("Enter Literotica story URL: ").strip()
    logging.info(f"Validated story URL: {input_url}")
    return input_url

def get_output_format():
    """
    Prompt user to select output format: TXT, PDF, EPUB or All.
    
    Returns:
        str: Choice string "1", "2", "3", or "4"
    """
    print("\nSelect output format:")
    print("1) TXT")
    print("2) PDF")
    print("3) EPUB")
    print("4) All of the above")
    choice = ""
    while choice not in ("1", "2", "3", "4"):
        choice = input("Enter choice (1/2/3/4): ").strip()
    logging.info(f"User selected output format option: {choice}")
    return choice

def get_output_directory(story_title):
    """
    Ask user for optional parent folder, default current directory,
    then create and return story-specific output directory.
    
    Args:
        story_title (str): The story title to name the folder
    
    Returns:
        str: Full path to the created output directory
    """
    print("\nWhere would you like to save the files?")
    parent = input("Enter parent folder path (or leave blank for current directory): ").strip()
    if not parent:
        parent = os.getcwd()
    output_dir = os.path.join(parent, sanitize_filename(story_title))
    os.makedirs(output_dir, exist_ok=True)
    logging.info(f"Created output directory: {output_dir}")
    return output_dir

# ========== Main Function ==========

def main():
    """
    Main execution flow:
    - Get story URL (from arg or prompt)
    - Validate and scrape all story pages
    - Prompt output format and output directory
    - Save story in requested format(s)
    - Log and handle errors gracefully
    """
    try:
        start_url = get_story_url()
        format_choice = get_output_format()

        logging.info("Starting story scrape...")

        # Fetch first page and extract title
        soup = get_page(start_url)
        title = extract_title(soup)
        safe_title = sanitize_filename(title)

        full_story = ""
        current_url = start_url
        page_num = 1

        # Loop through all pages in the story
        while current_url:
            logging.info(f"Processing page {page_num}: {current_url}")
            soup = get_page(current_url)
            page_text = extract_story_text(soup)
            full_story += page_text + "\n\n"
            current_url = find_next_page(soup)
            page_num += 1
            time.sleep(1)  # polite delay between requests

        output_dir = get_output_directory(title)

        # Construct output filenames
        txt_path = os.path.join(output_dir, f"{safe_title}.txt")
        pdf_path = os.path.join(output_dir, f"{safe_title}.pdf")
        epub_path = os.path.join(output_dir, f"{safe_title}.epub")

        # Save based on user choice
        if format_choice == "1":
            save_as_txt(title, full_story, txt_path)
        elif format_choice == "2":
            save_as_pdf(title, full_story, pdf_path)
        elif format_choice == "3":
            save_as_epub(title, full_story, epub_path)
        elif format_choice == "4":
            save_as_txt(title, full_story, txt_path)
            save_as_pdf(title, full_story, pdf_path)
            save_as_epub(title, full_story, epub_path)

        logging.info("Scraping and saving completed successfully.")

    except Exception as e:
        logging.error("An unexpected error occurred during execution.")
        logging.exception(e)
        print("An error occurred. Please check the log file for details.")

if __name__ == "__main__":
    main()