import fitz  # PyMuPDF
import re
from bs4 import BeautifulSoup
from ebooklib import epub

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    paragraphs = []

    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] == 0:  # text block
                lines = []
                for line in block["lines"]:
                    line_text = " ".join([span["text"] for span in line["spans"]])
                    lines.append(line_text.strip())

                if lines:
                    paragraph = " ".join(lines)
                    paragraphs.append(paragraph.strip())

    return paragraphs

def clean_hyphenation(paragraphs):
    cleaned = []
    for para in paragraphs:
        # Fix hyphenated words at line breaks: "inter-\nnational" -> "international"
        para = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', para)
        cleaned.append(para)
    return cleaned

def paragraphs_to_html(paragraphs):
    soup = BeautifulSoup("", "html.parser")
    for para in paragraphs:
        p = soup.new_tag("p")
        p.string = para
        soup.append(p)
    return str(soup)

def create_epub(html_content, output_file):
    book = epub.EpubBook()
    book.set_identifier("id123456")
    book.set_title("Converted PDF")
    book.set_language("en")
    book.add_author("Auto-Converted")

    chapter = epub.EpubHtml(title="Chapter 1", file_name="chap_01.xhtml", lang="en")
    chapter.content = html_content

    book.add_item(chapter)
    book.toc = (epub.Link('chap_01.xhtml', 'Chapter 1', 'chap1'),)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav', chapter]

    epub.write_epub(output_file, book)
    print(f"✅ EPUB created: {output_file}")

# --- MAIN EXECUTION ---
import sys
import os

if len(sys.argv) < 2:
    print("Usage: python pdf_to_epub.py input.pdf [output.epub]")
    sys.exit(1)

pdf_path = os.path.expanduser(sys.argv[1])
output_path = os.path.expanduser(sys.argv[2]) if len(sys.argv) > 2 else "output.epub"

paragraphs = extract_text_from_pdf(pdf_path)
paragraphs = clean_hyphenation(paragraphs)
html = paragraphs_to_html(paragraphs)
create_epub(html, output_path)