from pathlib import Path
from lxml import etree
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import XML_DIR

XML_PATH = XML_DIR / "zmluvy.xml"

def main():
    if not XML_PATH.exists():
        raise FileNotFoundError(f"XML súbor neexistuje: {XML_PATH}")

    tree = etree.parse(str(XML_PATH))
    root = tree.getroot()

    zmluvy = root.findall(".//zmluva")

    print(f"Nájdených zmlúv: {len(zmluvy)}")
    print("=" * 60)

    for zmluva in zmluvy:
        contract_id = zmluva.findtext("ID")
        ico = zmluva.findtext("ico")
        ico1 = zmluva.findtext("ico1")
        nazov = zmluva.findtext("nazov")
        datum = zmluva.findtext("datum")
        datum_ucinnost = zmluva.findtext("datum_ucinnost")

        print(f"ZMLUVA ID:  {contract_id}")
        print(f"ICO odber:  {ico1}")
        print(f"ICO dodal:  {ico}")
        print(f"Názov:      {nazov}")
        print(f"Dátum:      {datum}")
        print(f"Účinnosť:   {datum_ucinnost}")

        prilohy = zmluva.findall(".//priloha")
        print(f"Počet príloh: {len(prilohy)}")

        for priloha in prilohy:
            priloha_id = priloha.findtext("ID")
            priloha_nazov = priloha.findtext("nazov")
            pdf_file = priloha.findtext("dokument1")
            velkost = priloha.findtext("velkost1")

            print("  - Príloha ID:", priloha_id)
            print("    Názov:    ", priloha_nazov)
            print("    PDF:      ", pdf_file)
            print("    Veľkosť:  ", velkost)

        print("-" * 60)


if __name__ == "__main__":
    main()
