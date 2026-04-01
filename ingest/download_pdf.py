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

# Hlavná funkcia – parsovanie XML a sťahovanie všetkých PDF
def main():
    # Načítanie START_DATE z pipeline state
    start_date = load_start_date()
    if not start_date:
        logger.warning("⚠️ START_DATE nenájdený, spracúvam všetky XML súbory")
        start_date = datetime.min

    xml_files = list(XML_DIR.glob("*.xml"))
    if not xml_files:
        raise FileNotFoundError(f"Žiadne XML súbory v adresári: {XML_DIR}")

    logger.info(f"Nájdených XML súborov: {len(xml_files)}")
    logger.info(f"Filtrujem iba súbory od: {start_date.strftime('%Y-%m-%d')}")

    # Filtrovanie XML súborov podľa dátumu
    filtered_files = []
    for xml_path in xml_files:
        try:
            date_str = xml_path.stem  # názov bez .xml
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if file_date >= start_date:
                filtered_files.append(xml_path)
        except ValueError:
            # Ak súbor nemá správny formát dátumu, ignorujeme ho
            pass

    logger.info(f"Spracúvam {len(filtered_files)} XML súborov")

    for xml_path in filtered_files:
        logger.info(f"\nSpracúvam súbor: {xml_path.name}")
        try:
            tree = etree.parse(str(xml_path))
            root = tree.getroot()
            zmluvy = root.findall(".//zmluva")
            logger.debug(f"Nájdených zmlúv v {xml_path.name}: {len(zmluvy)}")

            for zmluva in zmluvy:
                nazov = zmluva.findtext("nazov")
                contract_id = zmluva.findtext("ID")
                logger.debug(f"\nZMLUVA ID {contract_id} – {nazov}")

                prilohy = zmluva.findall(".//priloha")
                for priloha in prilohy:
                    pdf_file = priloha.findtext("dokument")
                    if pdf_file:
                        download_pdf(pdf_file)
                    pdf_file = priloha.findtext("dokument1")
                    if pdf_file:
                        download_pdf(pdf_file)

        except Exception as e:
            logger.error(f"⚠️ Chyba pri spracovaní {xml_path.name}: {e}")

if __name__ == "__main__":
    try:
        main()
        logger.info("✅ Všetky PDF stiahnuté úspešne")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Chyba pri sťahovaní PDF: {e}")
        sys.exit(1)
