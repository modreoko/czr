#!/usr/bin/env python3
"""
Orchestrator pipeline pre postupné spúšťanie ingestion skriptov.

Spúšťa skripty v poradí:
1. download_xml.py      - Stiahne XML z CRZ a ofiltruje podľa ICO
2. download_pdf.py      - Stiahne PDF súbory z XML
3. ocr_pdf.py          - Spustí OCR na PDF súboroch
4. ingest_chunks_with_metadata.py - Ingests textové chunky s metadátami do Qdrant

Skript sa zastavuje ak niektorý z pipeline krokov zlyhá.

Usage:
    python -m ingest.pipeline              # bez logovania
    python -m ingest.pipeline --log        # s logovaním do log/debug.log
"""

import subprocess
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingest.pipeline_state import load_start_date, save_start_date
from ingest.logger import setup_logging, get_logger

# Script directory
SCRIPT_DIR = Path(__file__).parent

SCRIPTS = [
    ("download_xml.py", "Sťahovanie XML súborov"),
    ("download_pdf.py", "Sťahovanie PDF súborov"),
    ("ocr_pdf.py", "OCR spracovanie PDF"),
    ("ingest_chunks_with_metadata.py", "Ingestion do Qdrant"),
]

def run_script(script_name: str, description: str, logger: logging.Logger) -> bool:
    """
    Spustí skript a vracia True ak bol úspešný.

    Args:
        script_name: Názov skriptu
        description: Popis kroku pre logging
        logger: Logger instance

    Returns:
        True ak bol skript úspešný (exit code 0), False inak
    """
    script_path = SCRIPT_DIR / script_name

    if not script_path.exists():
        logger.error(f"❌ Chyba: Skript neexistuje – {script_path}")
        return False

    logger.info(f"\n{'=' * 60}")
    logger.info(f"🚀 Spúšťam: {description}")
    logger.info(f"   Skript: {script_path.name}")
    logger.info(f"   Čas: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'=' * 60}\n")

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=False,
            text=True,
            capture_output=True
        )

        # Log script output
        if result.stdout:
            logger.debug(f"STDOUT from {script_name}:\n{result.stdout}")
        if result.stderr:
            logger.debug(f"STDERR from {script_name}:\n{result.stderr}")

        if result.returncode == 0:
            logger.info(f"✅ Úspešne: {description}")
            return True
        else:
            logger.error(f"❌ Chyba: {description} (exit code: {result.returncode})")
            return False

    except Exception as e:
        logger.error(f"❌ Chyba pri spúšťaní skriptu: {e}")
        return False


def main(enable_logging: bool = False):
    """
    Spustí celý pipeline.

    Args:
        enable_logging: Ak True, ukladá výstupy do log/debug.log
    """
    # Initialize logging
    logger = setup_logging(enable_logging=enable_logging)

    if enable_logging:
        logger.info("🔵 LOGGING ENABLED - All outputs will be saved to log/debug.log")
    else:
        logger.info("⚪ LOGGING DISABLED - Outputs are not being saved")

    # Načítanie aktuálneho START_DATE na začiatku pipeline
    start_date = load_start_date()
    if start_date:
        logger.info(f"📅 Načítaný START_DATE: {start_date.strftime('%Y-%m-%d')}")
    else:
        logger.warning("⚠️  START_DATE nenájdený v pipeline_state")

    logger.info(f"\n{'=' * 60}")
    logger.info("🔄 ZAČÍNA PIPELINE")
    logger.info(f"   Čas: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"   Počet krokov: {len(SCRIPTS)}")
    logger.info(f"{'=' * 60}\n")

    completed_steps = []

    for script_name, description in SCRIPTS:
        if run_script(script_name, description, logger):
            completed_steps.append(description)
        else:
            logger.error(f"\n⏹️  Pipeline zastavený v kroku: {description}")
            logger.info(f"\nDokončené kroky ({len(completed_steps)}):")
            for i, step in enumerate(completed_steps, 1):
                logger.info(f"  {i}. ✅ {step}")
            return 1  # Exit with error

    # Všetky kroky úspešné – uloženie START_DATE na konci pipeline
    logger.info(f"\n{'=' * 60}")
    logger.info("✅ PIPELINE ÚSPEŠNE DOKONČENÝ")
    logger.info(f"   Čas: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"   Krokov: {len(completed_steps)}")
    for i, step in enumerate(completed_steps, 1):
        logger.info(f"   {i}. ✅ {step}")

    # Uloženie nového START_DATE na konci pipeline
    new_start_date = datetime.today()
    save_start_date(new_start_date)
    logger.info(f"\n📅 Uložený nový START_DATE pre ďalšie spustenie: {new_start_date.strftime('%Y-%m-%d')}")
    logger.info(f"{'=' * 60}\n")

    if enable_logging:
        logger.info(f"✅ Pipeline execution logged to: log/debug.log")

    return 0  # Success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pipeline orchestrator for contract ingestion and processing",
        epilog="Examples:\n"
               "  python -m ingest.pipeline         # Run without logging\n"
               "  python -m ingest.pipeline --log   # Run with logging to log/debug.log",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--log",
        action="store_true",
        help="Enable logging to log/debug.log (incremental)"
    )

    args = parser.parse_args()
    exit_code = main(enable_logging=args.log)
    sys.exit(exit_code)
