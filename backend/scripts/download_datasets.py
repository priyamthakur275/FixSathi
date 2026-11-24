"""Fetch the datasets that can be fetched automatically, and print instructions for the rest.

    python scripts/download_datasets.py            # ApplianceDB via git (pinned commit recorded)

Only the CSV data files and licence/provenance docs are kept from ApplianceDB (not the HTML site).
"""
import json, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
from _paths import RAW

APPLIANCEDB = 'https://github.com/ApplianceDB/ApplianceDB-public'
KEEP = ['error_codes.csv', 'repair_procedures.csv', 'replacement_parts.csv', 'LICENSE', 'COMMERCIAL_LICENSE.md', 'SOURCES.md', 'DATA_DICTIONARY.md', 'README.md']


def appliancedb() -> None:
    dest = RAW / 'appliancedb'; dest.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        subprocess.run(['git', 'clone', '--depth', '1', '-q', APPLIANCEDB, t], check=True)
        commit = subprocess.run(['git', '-C', t, 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
        for f in KEEP:
            shutil.copy2(Path(t) / f, dest / f)
    (dest / 'FETCH_INFO.json').write_text(json.dumps({'url': APPLIANCEDB, 'commit': commit, 'fetched_at': datetime.now(timezone.utc).isoformat(),
                                                      'license': 'ODbL-1.0 (data), CC BY 4.0 (docs)'}, indent=1))
    print(f'ApplianceDB fetched at commit {commit} -> {dest}')


MANUAL = """
Manual downloads (not automated):
- Open Repair Alliance: request the CSV at https://openrepair.org/open-data/downloads/ (form). Save the EEE file as
  data/raw/openrepair/<name>.csv and run process_datasets.py. Licence CC BY-SA 4.0.
- LBNL HVAC fault data (https://faultdetection.lbl.gov/data/): commercial HVAC sensor time series; not imported (see docs/DATASET_SOURCES.md).
- MIMII (https://zenodo.org/record/3384388): ~100 GB industrial machine audio, CC BY-SA 4.0; not imported. Register clips in dataset_media if used later.
"""

if __name__ == '__main__':
    try:
        appliancedb()
    except subprocess.CalledProcessError as e:
        sys.exit(f'ApplianceDB download failed: {e}')
    print(MANUAL)
