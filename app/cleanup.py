#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timedelta

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models.models import Link


def cleanup_expired_links():
    """Mark expired links as inactive."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        # Find links with expiration date in the past
        expired_links = db.query(Link).filter(Link.expires_at < now, Link.is_active == True).all()

        count = 0
        for link in expired_links:
            link.is_active = False
            count += 1

        if count > 0:
            db.commit()
            print(f"Marked {count} expired links as inactive.")
        else:
            print("No expired links found.")

        # Also cleanup links that haven't been used for a long time
        inactive_days = int(os.getenv("LINK_INACTIVE_DAYS", "30"))
        cutoff_date = now - timedelta(days=inactive_days)

        unused_links = (
            db.query(Link).filter(Link.last_used_at < cutoff_date, Link.is_active == True).all()
        )

        count = 0
        for link in unused_links:
            link.is_active = False
            count += 1

        if count > 0:
            db.commit()
            print(f"Marked {count} unused links as inactive (not used for {inactive_days} days).")
        else:
            print(f"No links unused for {inactive_days} days found.")

    finally:
        db.close()


if __name__ == "__main__":
    cleanup_expired_links()
