"""Create working .env files for local runs, with freshly generated secrets.

    python scripts/setup_env.py             # writes backend/.env (manual run)
    python scripts/setup_env.py --compose   # also writes .env in the project root (docker compose: ports, database password)

Never overwrites an existing file unless --force is given. The Gemini key is left for you to paste in yourself
(GEMINI_API_KEY in backend/.env); the app runs without it (AI features answer AI_NOT_CONFIGURED and demo scenarios still work).
"""
import argparse, re, secrets
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent


def write(src: Path, dst: Path, force: bool, subs: dict[str, str]) -> str | None:
    if dst.exists() and not force:
        print(f'{dst} already exists. Use --force to replace it.'); return None
    text = src.read_text()
    for k, v in subs.items():
        text = re.sub(rf'^{k}=.*$', f'{k}={v}', text, flags=re.M)
    dst.write_text(text); dst.chmod(0o600)
    print(f'Wrote {dst}.')
    return text


def main():
    p = argparse.ArgumentParser(); p.add_argument('--compose', action='store_true'); p.add_argument('--force', action='store_true')
    p.add_argument('--database-url', help='e.g. postgresql+psycopg://postgres:postgres@localhost:5432/fixsaathi')
    a = p.parse_args()
    subs = {'SECRET_KEY': secrets.token_urlsafe(64)}
    if a.database_url:
        subs['DATABASE_URL'] = a.database_url
    text = write(BACKEND / '.env.example', BACKEND / '.env', a.force, subs)
    if a.compose:  # compose overrides DATABASE_URL for the container; the root file holds ports and the database password
        write(ROOT / '.env.example', ROOT / '.env', a.force, {'POSTGRES_PASSWORD': secrets.token_hex(24)})
    print('Next: open backend/.env and paste your Gemini key after GEMINI_API_KEY= (no quotes, no spaces). The app also runs without it.')
    if text and not a.compose:
        db = re.search(r'^DATABASE_URL=(.*)$', text, flags=re.M)
        print(f'Database: {db.group(1) if db else "(not set)"}  <- change it if your PostgreSQL user or password differs.')


if __name__ == '__main__':
    main()
