import requests
from pathlib import Path
from lxml import etree
import sys
import traceback
from datetime import datetime
import logging

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import XML_FILTERED_DIR, TMP_PDF_DIR, CRZ_PDF_BASE_URL, DOWNLOAD_TIMEOUT
from ingest.pipeline_state import load_start_date
from ingest.logger import get_logger

# Get logger
logger = get_logger()

XML_DIR = XML_FILTERED_DIR
TMP_DIR = TMP_PDF_DIR

# Funkcia na stiahnutie PDF
def download_pdf(pdf_filename: str):
    url = CRZ_PDF_BASE_URL.format(filename=pdf_filename)
    dest = TMP_DIR / pdf_filename

    if dest.exists():
        logger.debug(f"PDF už existuje: {dest}")
        return dest

    try:
        logger.debug(f"Stiahnem: {pdf_filename}")
        with requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        logger.debug(f"Stiahnuté: {dest}")
        return dest
    except Exception as e:
        logger.error(f"Chyba pri sťahovaní {pdf_filename}: {e}")
        return None

# Hlavna funkcia - parsovanie XML a stahovanie vsetkych PDF
def main():
    # Nacitanie START_DATE z pipeline state
    start_date = load_start_date()
    if not start_date:
        logger.warning("[WARNING] START_DATE nenajdeny, spracuvam vsetky XML subory")
        start_date = datetime.min

    xml_files = list(XML_DIR.glob("*.xml"))
    if not xml_files:
        raise FileNotFoundError(f"Ziadne XML subory v adresari: {XML_DIR}")

    logger.info(f"Najdanych XML suborov: {len(xml_files)}")
    logger.info(f"Filtrujem iba subory od: {start_date.strftime('%Y-%m-%d')}")

    # Filtrovanie XML suborov podla datumu
    filtered_files = []
    for xml_path in xml_files:
        try:
            date_str = xml_path.stem  # nazov bez .xml
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if file_date >= start_date:
                filtered_files.append(xml_path)
        except ValueError:
            # Ak subor nema spravny format datumu, ignorujeme ho
            pass

    logger.info(f"Spracuvam {len(filtered_files)} XML suborov")

    for xml_path in filtered_files:
        logger.info(f"\nSpracuvam subor: {xml_path.name}")
        try:
            tree = etree.parse(str(xml_path))
            root = tree.getroot()
            zmluvy = root.findall(".//zmluva")
            logger.debug(f"Najdanych zmlúv v {xml_path.name}: {len(zmluvy)}")

            for zmluva in zmluvy:
                nazov = zmluva.findtext("nazov")
                contract_id = zmluva.findtext("ID")
                logger.debug(f"\nZMLUVA ID {contract_id} - {nazov}")

                prilohy = zmluva.findall(".//priloha")
                for priloha in prilohy:
                    pdf_file = priloha.findtext("dokument")
                    if pdf_file:
                        download_pdf(pdf_file)
                    pdf_file = priloha.findtext("dokument1")
                    if pdf_file:
                        download_pdf(pdf_file)

        except Exception as e:
            logger.error(f"[WARNING] Chyba pri spracovani {xml_path.name}: {e}")

if __name__ == "__main__":
    try:
        main()
        logger.info("[OK] Vsetky PDF stahnute uspesne")
        sys.exit(0)
    except Exception as e:
        logger.error(f"[ERROR] Chyba pri stahovani PDF: {e}")
        sys.exit(1)
