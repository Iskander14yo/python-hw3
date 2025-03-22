import os
from sqlalchemy.orm import Session

from app.models.models import User, Link
from app.db.redis import get_redis


def delete_user(db: Session, user_id: int) -> bool:
    """Delete a user and all their associated links."""
    user = db.query(User).filter(User.id == user_id).first()

    if not user or user.is_admin:
        return False

    # First, mark all user's links as inactive
    user_links = db.query(Link).filter(Link.user_id == user_id).all()
    redis = get_redis()

    for link in user_links:
        link.is_active = False
        # Invalidate cache for each link
        redis.delete(f"link:{link.short_code}")

    # Delete the user
    db.delete(user)
    db.commit()

    return True


def get_recent_links(db: Session, limit: int | None = None) -> list[Link]:
    """
    Get the most recent links regardless of their expiration status.
    Limit is taken from environment variable ADMIN_LINKS_LIMIT if not specified.
    """
    if limit is None:
        limit = int(os.getenv("ADMIN_LINKS_LIMIT", "100"))

    links = db.query(Link).order_by(Link.created_at.desc()).limit(limit).all()

    return links


def get_all_users(db: Session) -> list[User]:
    """Get all users in the system."""
    return db.query(User).all()


def force_delete_link(db: Session, short_code: str) -> bool:
    """
    Forcefully delete a link as an admin, bypassing user ownership checks.
    """
    link = db.query(Link).filter(Link.short_code == short_code, Link.is_active == True).first()

    if not link:
        return False

    # Mark as inactive
    link.is_active = False
    db.commit()

    # Invalidate cache
    redis = get_redis()
    redis.delete(f"link:{short_code}")

    return True
