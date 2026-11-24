"""Create a user or change a role. Self-registration only ever creates technicians.

    python scripts/create_user.py --email boss@acme.in --name "Asha Rao" --role manager --org "Acme Service" --password '...'
    python scripts/create_user.py --email someone@acme.in --role manager        # promote an existing user
"""
import argparse, getpass, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import select
from app.core.security import hash_password
from app.db.models import Organisation, User
from app.db.session import SessionLocal

p = argparse.ArgumentParser()
p.add_argument('--email', required=True); p.add_argument('--name'); p.add_argument('--role', choices=['technician', 'manager', 'admin'], required=True)
p.add_argument('--org'); p.add_argument('--password')
p.add_argument('--if-exists', action='store_true', help='only change an existing account; do nothing (exit 0) if the email is not registered')
a = p.parse_args()
db = SessionLocal()
org = None
if a.org:
    org = db.scalar(select(Organisation).where(Organisation.name == a.org)) or Organisation(name=a.org); db.add(org); db.flush()
u = db.scalar(select(User).where(User.email == a.email.lower()))
if u:
    u.role = a.role
    if org: u.organisation_id = org.id
    print(f'Updated {u.email}: role={u.role}')
elif a.if_exists:
    print('No account with that email yet; nothing changed. Register it in the app first.'); sys.exit(0)
else:
    pw = a.password or getpass.getpass('Password: ')
    if len(pw) < 8: sys.exit('Password must be at least 8 characters.')
    u = User(full_name=a.name or a.email.split('@')[0], email=a.email.lower(), password_hash=hash_password(pw), role=a.role, organisation_id=org.id if org else None)
    db.add(u); print(f'Created {u.email}: role={u.role}')
db.commit()
