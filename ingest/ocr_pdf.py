from pathlib import Path
from pdf2image import convert_from_path
import pytesseract
import shutil
import sys
import logging

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import TMP_PDF_DIR, TMP_TXT_DIR
from ingest.logger import get_logger

# Get logger
logger = get_logger()

# ------------------------
# Cesty
# ------------------------
TMP_DIR = TMP_PDF_DIR      # PDF súbory
TXT_DIR = TMP_TXT_DIR      # Výstupné texty
TXT_DIR.mkdir(exist_ok=True)

# Tesseract a Poppler
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\poppler-25.12.0\Library\bin"

# ------------------------
# Funkcia OCR
# ------------------------
def ocr_pdf(pdf_path: Path):
    txt_path = TXT_DIR / f"{pdf_path.stem}.txt"

    if txt_path.exists():
        logger.debug(f"OCR už hotový: {txt_path}")
        # Ak TXT existuje, PDF môžeme rovno zmazať
        pdf_path.unlink()
        return txt_path

    logger.debug(f"OCR: {pdf_path}")
    try:
        # Konverzia PDF -> obrázky
        pages = convert_from_path(str(pdf_path), poppler_path=POPPLER_PATH)
        full_text = ""
        for i, page in enumerate(pages, start=1):
            text = pytesseract.image_to_string(page, lang="slk+eng")
            full_text += text + "\n"

        # Uloženie textu
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)

        logger.debug(f"Text uložený: {txt_path}")

        # PDF sa zmaže po úspešnom OCR
        pdf_path.unlink()
        logger.debug(f"PDF zmazané: {pdf_path}")

        return txt_path

    except Exception as e:
        logger.error(f"Chyba OCR: {pdf_path} -> {e}")
        return None

# ------------------------
# Hlavná funkcia
# ------------------------
def main():
    pdf_files = sorted(TMP_DIR.glob("*.pdf"))
    logger.info(f"Najdene PDF subory: {len(pdf_files)}")

    # Filtrovanie - spracuvam iba PDF, pre ktore neexistuje TXT
    new_pdf_files = []
    processed_pdf_files = []

    for pdf_file in pdf_files:
        txt_path = TXT_DIR / f"{pdf_file.stem}.txt"
        if txt_path.exists():
            processed_pdf_files.append(pdf_file)
        else:
            new_pdf_files.append(pdf_file)

    logger.info(f"Novych PDF na spracovanie: {len(new_pdf_files)}")
    logger.info(f"Uz spracovanych (preskakujem): {len(processed_pdf_files)}")

    for pdf_file in new_pdf_files:
        ocr_pdf(pdf_file)

    # Vycistenie starych PDF suborov (ktore uz maju TXT)
    for pdf_file in processed_pdf_files:
        if pdf_file.exists():
            pdf_file.unlink()
            logger.debug(f"Zmazane stare PDF: {pdf_file.name}")

if __name__ == "__main__":
    try:
        main()
        logger.info("[OK] OCR vsetkych PDF hotovy")
        sys.exit(0)
    except Exception as e:
        logger.error(f"[ERROR] Chyba pri OCR: {e}")
        sys.exit(1)
