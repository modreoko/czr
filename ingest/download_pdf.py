import requests
from pathlib import Path
from lxml import etree
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import XML_FILTERED_DIR, TMP_PDF_DIR, CRZ_PDF_BASE_URL, DOWNLOAD_TIMEOUT

XML_DIR = XML_FILTERED_DIR
TMP_DIR = TMP_PDF_DIR

# Funkcia na stiahnutie PDF
def download_pdf(pdf_filename: str):
    url = CRZ_PDF_BASE_URL.format(filename=pdf_filename)
    dest = TMP_DIR / pdf_filename

    if dest.exists():
        print(f"PDF už existuje: {dest}")
        return dest

    try:
        print(f"Stiahnem: {pdf_filename}")
        with requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Stiahnuté: {dest}")
        return dest
    except Exception as e:
        print(f"Chyba pri sťahovaní {pdf_filename}: {e}")
        return None

# Hlavná funkcia – parsovanie XML a sťahovanie všetkých PDF
def main():
    xml_files = list(XML_DIR.glob("*.xml"))
    if not xml_files:
        raise FileNotFoundError(f"Žiadne XML súbory v adresári: {XML_DIR}")

    print(f"Nájdených XML súborov: {len(xml_files)}")

    for xml_path in xml_files:
        print(f"\nSpracúvam súbor: {xml_path.name}")
        try:
            tree = etree.parse(str(xml_path))
            root = tree.getroot()
            zmluvy = root.findall(".//zmluva")
            print(f"Nájdených zmlúv v {xml_path.name}: {len(zmluvy)}")

            for zmluva in zmluvy:
                nazov = zmluva.findtext("nazov")
                contract_id = zmluva.findtext("ID")
                print(f"\nZMLUVA ID {contract_id} – {nazov}")

                prilohy = zmluva.findall(".//priloha")
                for priloha in prilohy:
                    pdf_file = priloha.findtext("dokument")
                    if pdf_file:
                        download_pdf(pdf_file)
                    pdf_file = priloha.findtext("dokument1")
                    if pdf_file:
                        download_pdf(pdf_file)

        except Exception as e:
            print(f"⚠️ Chyba pri spracovaní {xml_path.name}: {e}")

if __name__ == "__main__":
    main()
