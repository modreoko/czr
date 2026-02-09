from pathlib import Path
from pdf2image import convert_from_path
import pytesseract
import shutil
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import TMP_PDF_DIR, TMP_TXT_DIR

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
        print(f"OCR už hotový: {txt_path}")
        # Ak TXT existuje, PDF môžeme rovno zmazať
        pdf_path.unlink()
        return txt_path

    print(f"OCR: {pdf_path}")
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

        print(f"Text uložený: {txt_path}")
        
        # PDF sa zmaže po úspešnom OCR
        pdf_path.unlink()
        print(f"PDF zmazané: {pdf_path}")

        return txt_path

    except Exception as e:
        print(f"Chyba OCR: {pdf_path} -> {e}")
        return None

# ------------------------
# Hlavná funkcia
# ------------------------
def main():
    pdf_files = sorted(TMP_DIR.glob("*.pdf"))
    print(f"Nájdené PDF súbory: {len(pdf_files)}")

    for pdf_file in pdf_files:
        ocr_pdf(pdf_file)

if __name__ == "__main__":
    main()
