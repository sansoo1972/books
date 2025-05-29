import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import time
import sys
import os
from urllib.parse import urljoin, urlparse

headers = {
    "User-Agent": "Mozilla/5.0"
}

def get_page(url):
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return BeautifulSoup(response.text, 'html.parser')

def extract_story_text(soup):
    story_div = soup.find('div', class_='panel article aa_eQ')
    if not story_div:
        return ""
    paragraphs = story_div.find_all('p')
    story_text = ""
    for p in paragraphs:
        story_text += p.get_text(strip=True) + "\n\n"
    return story_text

def find_next_page(soup):
    pagination = soup.find('div', class_='panel clearfix l_bH')
    if not pagination:
        return None
    next_link = pagination.find('a', title='Next Page')
    if next_link and 'href' in next_link.attrs:
        return urljoin("https://www.literotica.com", next_link['href'])
    return None

def extract_title(soup):
    title_tag = soup.find('h1', class_='j_bm headline j_eQ')
    return title_tag.text.strip() if title_tag else "Story"

def sanitize_filename(name):
    return "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).rstrip()

def save_as_txt(title, content, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"{title}\n\n{content}")

def save_as_pdf(title, content, filename):
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

def main():
    if len(sys.argv) < 2:
        print("Usage: python literotica_scraper.py <story_url>")
        return

    start_url = sys.argv[1]
    print(f"Starting from: {start_url}")

    soup = get_page(start_url)
    title = extract_title(soup)
    safe_title = sanitize_filename(title)

    full_story = ""
    current_url = start_url
    page_num = 1

    while current_url:
        print(f"Fetching page {page_num}...")
        soup = get_page(current_url)
        full_story += extract_story_text(soup)
        next_page = find_next_page(soup)
        if next_page == current_url:
            break
        current_url = next_page
        page_num += 1
        time.sleep(1)

    txt_file = f"{safe_title}.txt"
    pdf_file = f"{safe_title}.pdf"

    save_as_txt(title, full_story, txt_file)
    save_as_pdf(title, full_story, pdf_file)

    print(f"Done! Saved to:\n- {txt_file}\n- {pdf_file}")

if __name__ == "__main__":
    main()
