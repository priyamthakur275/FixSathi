import os
from pathlib import Path
ROOT = Path(os.environ.get('FIXSAATHI_DATA_DIR') or Path(__file__).resolve().parents[2] / 'data')
RAW, PROCESSED, SYNTHETIC, SCHEMAS = ROOT / 'raw', ROOT / 'processed', ROOT / 'synthetic', ROOT / 'schemas'
