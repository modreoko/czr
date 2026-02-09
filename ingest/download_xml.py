import os
import requests
import zipfile
from datetime import datetime, timedelta, time
from pathlib import Path
from lxml import etree
import xml.etree.ElementTree as ET
import time as tm
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    XML_DIR, XML_FILTERED_DIR, ICO_FILE, CRZ_EXPORT_URL
)

# rozsah dátumov
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime.today()

DATA_DIR = XML_DIR
FILTERED_DATA_DIR = XML_FILTERED_DIR
BASE_URL = CRZ_EXPORT_URL
print(f"📄 ICO_FILE: {ICO_FILE}")
print(f"📄 ICO_FILE exists: {ICO_FILE.exists()}")

exit_if_missing = not ICO_FILE.exists()
if exit_if_missing:
    raise FileNotFoundError(f"Súbor s ICO neexistuje: {ICO_FILE}")

# =========================
# NAČÍTANIE ICO
# =========================

with open(ICO_FILE, "r", encoding="utf-8") as f:
    allowed_icos = set(line.strip() for line in f if line.strip())

print(f"🔹 Načítaných ICO: {len(allowed_icos)}")

# =========================
# POMOCNÉ FUNKCIE
# =========================

def wait_for_rate_limit():
    """Určuje čakanie podľa času a limitov servera."""
    now = datetime.now()
    if time(6, 0) <= now.time() <= time(20, 0):
        # deň
        tm.sleep(0.4)  # ~2.5 req/s = bezpečne pod limit 10/s
    else:
        # noc
        tm.sleep(0.35)  # ~3 req/s = bezpečne pod limit 10/s
        

def download_zip_for_date(dt: datetime):
    """Stiahne ZIP súbor pre daný dátum."""
    date_str = dt.strftime("%Y-%m-%d")
    url = BASE_URL.format(date=date_str)
    zip_path = DATA_DIR / f"{date_str}.zip"
    xml_path = DATA_DIR / f"{date_str}.xml"

    if xml_path.exists():
        print(f"✅ XML pre {date_str} už existuje, preskakujem")
        return xml_path

    try:
        print(f"⬇️  Sťahujem {url}")
        resp = requests.get(url, timeout=60)
        if resp.status_code != 200:
            print(f"⚠️ ZIP pre {date_str} neexistuje (HTTP {resp.status_code})")
            return None

        # uloženie ZIP
        with open(zip_path, "wb") as f:
            f.write(resp.content)

        # rozbalenie
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # predpokladáme, že ZIP obsahuje jeden XML súbor
            xml_files = [f for f in zip_ref.namelist() if f.endswith(".xml")]
            if not xml_files:
                print(f"⚠️ ZIP pre {date_str} neobsahuje XML súbor")
                return None
            zip_ref.extract(xml_files[0], DATA_DIR)
            extracted_path = DATA_DIR / xml_files[0]

        # vymazanie ZIP po rozbalení
        zip_path.unlink()
        print(f"✅ Rozbalené a uložené {extracted_path.name}")

        return extracted_path

    except Exception as e:
        print(f"❌ Chyba pri sťahovaní {date_str}: {e}")
        return None

def filter_xml_by_ico(xml_file: Path, allowed_icos: set):
    parser = etree.XMLParser(recover=True, encoding='utf-8')
    tree = etree.parse(str(xml_file), parser)
    root = tree.getroot()

    filtered_root = etree.Element(root.tag)

    for zmluva in root.findall("zmluva"):
        ico1 = zmluva.findtext("ico1", default="")
        ico2 = zmluva.findtext("ico", default="")
        if ico1 in allowed_icos or ico2 in allowed_icos:
            filtered_root.append(zmluva)

    if len(filtered_root):
        filtered_path = FILTERED_DATA_DIR / f"{xml_file.stem}.xml"
        etree.ElementTree(filtered_root).write(str(filtered_path), encoding="utf-8", xml_declaration=True)
        print(f"✅ Filtrované zmluvy uložené: {filtered_path.name}")
    else:
        print(f"ℹ️ Žiadne zmluvy z ICO v {xml_file.name}, nič sa neuložilo")

# =========================
# Hlavný cyklus
# =========================

current_date = START_DATE
while current_date <= END_DATE:
    xml_file = download_zip_for_date(current_date)
    if xml_file:
        filter_xml_by_ico(xml_file, allowed_icos)
    wait_for_rate_limit()
    current_date += timedelta(days=1)

print("✅ Hotovo – všetky XML súbory spracované")
