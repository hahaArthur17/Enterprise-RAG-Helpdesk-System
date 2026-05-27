import re
import logging
import pdfplumber

logger = logging.getLogger("ai-service")

# Try to import pytesseract for OCR; mark unavailable if not installed
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("pytesseract not installed. OCR for scanned pages will be skipped.")


def _is_scanned_page(text: str) -> bool:
    """A page is likely scanned if extracted text is very short or has high garbage ratio."""
    if len(text.strip()) < 50:
        return True
    alpha_chars = sum(c.isalpha() or c.isspace() for c in text)
    if len(text) > 0 and alpha_chars / len(text) < 0.5:
        return True
    return False


def _ocr_page(page) -> str:
    """Render a PDF page to image and run Tesseract OCR."""
    if not OCR_AVAILABLE:
        return ""
    try:
        img = page.to_image(resolution=300).original
        return pytesseract.image_to_string(img)
    except Exception as e:
        logger.warning(f"OCR failed for a page: {e}")
        return ""


def _clean_text(text: str) -> str:
    """Remove page headers, footers, page numbers, duplicates, and garbled characters."""
    # Remove page numbers like "- 3 -" or "Page 3" at line boundaries
    text = re.sub(r"^\s*-?\s*\d+\s*-?\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*Page\s+\d+\s*$", "", text, flags=re.MULTILINE)

    # Remove repeated header/footer lines (same line appearing 3+ times)
    lines = text.split("\n")
    seen: dict[str, int] = {}
    for line in lines:
        stripped = line.strip()
        if stripped:
            seen[stripped] = seen.get(stripped, 0) + 1
    repeated = {line for line, count in seen.items() if count >= 3}
    lines = [line for line in lines if line.strip() not in repeated]
    text = "\n".join(lines)

    # Remove garbled characters (non-printable except normal whitespace and CJK)
    text = re.sub(r"[^\x20-\x7E\n\r\t一-鿿　-〿＀-￯]", "", text)

    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _table_to_sentences(table: list[list]) -> str:
    """Convert a table (list of rows) into natural language sentences."""
    if not table or len(table) < 2:
        return ""
    headers = table[0]
    sentences = []
    for row in table[1:]:
        parts = []
        for header, cell in zip(headers, row):
            if header and cell:
                parts.append(f"{header}: {cell}")
        if parts:
            sentences.append("; ".join(parts) + ".")
    return " ".join(sentences)


def process_pdf(file_path: str, source_filename: str) -> list[dict]:
    """
    Full PDF processing pipeline.

    Returns a list of page records, each containing:
    {
        "page_number": int,
        "text": str,           # cleaned text (may be empty)
        "table_texts": [str],  # table chunks as natural language
    }
    """
    pages: list[dict] = []

    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            table_texts: list[str] = []

            # --- Table extraction ---
            tables = page.extract_tables()
            for table in tables:
                sentence = _table_to_sentences(table)
                if sentence:
                    table_texts.append(sentence)
                    logger.info(f"Page {page_num}: extracted table as chunk")

            # --- Text extraction ---
            text = page.extract_text() or ""

            # OCR fallback for scanned pages
            if _is_scanned_page(text):
                ocr_text = _ocr_page(page)
                if ocr_text.strip():
                    text = ocr_text
                    logger.info(f"Page {page_num}: used OCR for scanned page")
                else:
                    logger.info(f"Page {page_num}: scanned page, OCR produced no text")

            # Clean the text
            text = _clean_text(text)

            pages.append(
                {
                    "page_number": page_num,
                    "text": text,
                    "table_texts": table_texts,
                }
            )

    total_tables = sum(len(p["table_texts"]) for p in pages)
    logger.info(
        f"Document '{source_filename}' processed: "
        f"{len(pages)} pages, {total_tables} table chunks"
    )
    return pages
