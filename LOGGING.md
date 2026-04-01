# Logging Guide

This document explains the logging system used in the zmluvy pipeline.

## Overview

The pipeline includes an optional logging system that captures all output to a centralized log file. Logging is disabled by default and only enabled when explicitly requested.

## File Structure

```
ingest/
├── logger.py              # Centralized logging configuration
└── pipeline.py            # Main pipeline (uses logger)

log/
└── debug.log             # Incremental log file (created when logging is enabled)
```

## How to Enable Logging

### Using the Pipeline Orchestrator

Run the pipeline with the `--log` flag:

```bash
# Without logging (default)
python -m ingest.pipeline

# With logging to log/debug.log
python -m ingest.pipeline --log
```

### Help Information

```bash
python -m ingest.pipeline --help
```

Output:
```
usage: pipeline.py [-h] [--log]

Pipeline orchestrator for contract ingestion and processing

options:
  -h, --help  show this help message and exit
  --log       Enable logging to log/debug.log (incremental)

Examples:
  python -m ingest.pipeline         # Run without logging
  python -m ingest.pipeline --log   # Run with logging to log/debug.log
```

## Log File Format

**Location**: `c:\projects\zmluvy\log\debug.log`

**Format**:
```
YYYY-MM-DD HH:MM:SS | LEVEL    | logger_name | message
```

**Example**:
```
2026-04-01 10:15:23 | INFO     | zmluvy | 🔵 LOGGING STARTED - 2026-04-01 10:15:23
2026-04-01 10:15:23 | INFO     | zmluvy | 📝 Log file: c:\projects\zmluvy\log\debug.log
2026-04-01 10:15:23 | INFO     | zmluvy | ⚪ LOGGING DISABLED - Outputs are not being saved
2026-04-01 10:15:23 | INFO     | zmluvy | 📅 Načítaný START_DATE: 2026-01-24
2026-04-01 10:15:24 | DEBUG    | zmluvy | STDOUT from download_xml.py:
```

## Log Levels

The logger captures messages at different levels:

| Level | Symbol | Usage |
|-------|--------|-------|
| INFO | ℹ️ | General information about pipeline execution |
| DEBUG | 🔍 | Detailed information, script output |
| WARNING | ⚠️ | Warning messages (e.g., missing files) |
| ERROR | ❌ | Error messages, failed steps |

## Incremental Logging

The log file is **incremental**, meaning:

- ✅ Each run **appends** to the existing log file
- ✅ No previous logs are overwritten
- ✅ Complete history of all pipeline executions is preserved
- ℹ️ Log file grows over time (consider archiving old logs if needed)

### Example Log History

```log
2026-04-01 10:15:23 | INFO | zmluvy | ============================================================
2026-04-01 10:15:23 | INFO | zmluvy | 🔄 ZAČÍNA PIPELINE
2026-04-01 10:15:23 | INFO | zmluvy | Čas: 2026-04-01 10:15:23
...
2026-04-01 10:45:30 | INFO | zmluvy | ✅ PIPELINE ÚSPEŠNE DOKONČENÝ
2026-04-01 10:45:30 | INFO | zmluvy | ============================================================

[... next run ...]

2026-04-02 11:20:45 | INFO | zmluvy | ============================================================
2026-04-02 11:20:45 | INFO | zmluvy | 🔄 ZAČÍNA PIPELINE
...
```

## What Gets Logged

### Always Logged (with `--log` flag):

1. **Pipeline Start/End**
   - Start time and number of steps
   - Completion status

2. **Script Execution**
   - Which script is running
   - Script start time
   - Success/failure status

3. **State Management**
   - Loaded START_DATE
   - Updated START_DATE after completion

4. **Subprocess Output**
   - STDOUT from each script (DEBUG level)
   - STDERR from each script (DEBUG level)

### Not Logged:

- If `--log` flag is NOT used, nothing is written to the file
- Only console output appears in real-time

## Logging in Your Own Scripts

If you want to integrate logging into your own scripts, use the logger module:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ingest.logger import get_logger

# Get the configured logger
logger = get_logger()

# Use it
logger.info("Processing started")
logger.debug("Detailed information")
logger.warning("Something unexpected")
logger.error("An error occurred")
```

## Log File Rotation

The log file grows indefinitely. To manage log size, you can:

### Option 1: Manual Cleanup

Delete or archive old logs:
```bash
# Delete debug.log
rm log/debug.log

# Or move to archive
mv log/debug.log log/debug-2026-04-01.log
```

### Option 2: Automatic Rotation (Future Enhancement)

Implement `RotatingFileHandler` in `logger.py` for automatic rotation by size or date.

## Troubleshooting

### Log file is not created

- ✅ Make sure you use `--log` flag when running pipeline
- ✅ Log file is only created when logging is enabled
- ✅ Check that `/log` directory exists (created automatically)

### Log file is empty

- Possible: No error occurred, only console output
- Solution: Run with `--log` flag to confirm logging is enabled

### Log file grows too large

- Solution: Archive or delete old logs manually
- Future: Implement log rotation in logger.py

## Examples

### Example 1: Run Pipeline with Logging

```bash
$ python -m ingest.pipeline --log

⚪ LOGGING DISABLED - Outputs are not being saved  # <- This is printed to console
📅 Načítaný START_DATE: 2026-01-24

============================================================
🔄 ZAČÍNA PIPELINE
   Čas: 2026-04-01 10:15:23
   Počet krokov: 4
============================================================

🚀 Spúšťam: Sťahovanie XML súborov
...
```

Output is also saved to `log/debug.log`

### Example 2: Check Previous Runs

```bash
# View last 50 lines of log
tail -50 log/debug.log

# View specific date's executions
grep "2026-04-01" log/debug.log

# Count errors
grep "❌" log/debug.log | wc -l
```

## Configuration

Logging configuration is in `ingest/logger.py`:

- **LOG_DIR**: `c:\projects\zmluvy\log`
- **LOG_FILE**: `c:\projects\zmluvy\log\debug.log`
- **Format**: `%(asctime)s | %(levelname)-8s | %(name)s | %(message)s`
- **Encoding**: UTF-8
- **Mode**: Append (incremental)

To customize logging, edit `ingest/logger.py` and modify:
- `setup_logging()` function
- `LOG_DIR` constant
- Log format string
