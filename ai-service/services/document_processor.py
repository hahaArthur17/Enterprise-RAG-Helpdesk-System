import re
import logging
import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger("ai-service")

# Try to import pytesseract for OCR; mark unavailable if not installed
try:
    import pytesseract
    from PIL import Image
    import io
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("pytesseract/Pillow not installed. OCR for scanned pages will be skipped.")


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

    # Remove garbled characters (non-printable except normal whitespace)
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


def process_pdf(file_path: str) -> list[str]:
    """
    Full PDF processing pipeline:
    1. Open with pdfplumber (better table detection than pypdf)
    2. Per page: extract tables -> convert to sentences
    3. Per page: extract text -> OCR if scanned -> clean
    4. Chunk all collected text
    """
    all_chunks: list[str] = []

    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            # --- Table extraction ---
            tables = page.extract_tables()
            for table in tables:
                sentence = _table_to_sentences(table)
                if sentence:
                    all_chunks.append(sentence)
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

            if text.strip():
                # Use a temporary list to chunk this page's text
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=500,
                    chunk_overlap=50,
                    separators=["\n\n", "\n", ".", " ", ""]
                )
                page_chunks = splitter.split_text(text)
                all_chunks.extend(page_chunks)

    logger.info(f"Document processed: {len(all_chunks)} total chunks")
    return all_chunks
