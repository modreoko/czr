from lxml import etree
from pathlib import Path
import sys
import logging

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import XML_FILTERED_DIR
from ingest.logger import get_logger

# Get logger
logger = get_logger()

XML_DIR = XML_FILTERED_DIR

def load_metadata():
    contracts = {}

    xml_files = sorted(XML_DIR.glob("*.xml"))

    if not xml_files:
        raise FileNotFoundError(f"Ziadne XML subory v {XML_DIR}")

    logger.info(f"[FILE] Nacitavam XML subory: {len(xml_files)}")

    for xml_file in xml_files:
        try:
            tree = etree.parse(str(xml_file))
        except Exception as e:
            logger.warning(f"[WARNING] Preskakujem poskodeny XML: {xml_file.name} ({e})")
            continue

        root = tree.getroot()

        for zmluva in root.findall(".//zmluva"):
            zmluva_id = zmluva.findtext("ID")
            if not zmluva_id:
                continue

            # ak uz zmluva existuje, len doplnime PDF
            if zmluva_id not in contracts:
                contracts[zmluva_id] = {
                    "zmluva_id": zmluva_id,
                    "datum": zmluva.findtext("datum"),
                    "datum_ucinnost": zmluva.findtext("datum_ucinnost"),
                    "zs1": zmluva.findtext("zs1"),
                    "zs2": zmluva.findtext("zs2"),
                    "nazov": zmluva.findtext("nazov"),
                    "predmet": zmluva.findtext("predmet"),
                    "suma_zmluva": zmluva.findtext("suma_zmluva"),
                    "suma_spolu": zmluva.findtext("suma_spolu"),
                    "pdfs": []
                }

            for priloha in zmluva.findall(".//priloha"):
                pdf = priloha.findtext("dokument") or priloha.findtext("dokument1")
                if pdf and pdf not in contracts[zmluva_id]["pdfs"]:
                    contracts[zmluva_id]["pdfs"].append(pdf)

    logger.info(f"[OK] Nacitanych zmlúv: {len(contracts)}")
    return contracts
