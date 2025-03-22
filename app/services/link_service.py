import random
import string
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional
from fastapi import HTTPException

from app.models.models import Link, User
from app.models.schemas import LinkCreate, LinkUpdate
from app.db.redis import get_redis

# Constants
SHORT_CODE_LENGTH = 6
CUSTOM_ALIAS_MIN_LENGTH = 4


def generate_short_code(length: int = SHORT_CODE_LENGTH) -> str:
    """Generate a random short code for URLs."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def create_link(db: Session, link_data: LinkCreate, user: Optional[User] = None) -> Link:
    """Create a new shortened link."""
    # Check if the custom alias is provided and valid
    if link_data.custom_alias:
        if len(link_data.custom_alias) < CUSTOM_ALIAS_MIN_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Custom alias must be at least {CUSTOM_ALIAS_MIN_LENGTH} characters",
            )

        # Check if the custom alias already exists
        existing_alias = db.query(Link).filter(Link.custom_alias == link_data.custom_alias).first()
        if existing_alias:
            raise HTTPException(status_code=400, detail="Custom alias already exists")

        short_code = link_data.custom_alias
    else:
        # Generate a unique short code
        while True:
            short_code = generate_short_code()
            existing_link = db.query(Link).filter(Link.short_code == short_code).first()
            if not existing_link:
                break

    # Check if the URL already exists for this user
    if user:
        existing_url = (
            db.query(Link)
            .filter(
                Link.original_url == link_data.original_url,
                Link.user_id == user.id,
                Link.is_active == True,
            )
            .first()
        )

        if existing_url:
            return existing_url

    # Create new link
    db_link = Link(
        short_code=short_code,
        original_url=link_data.original_url,
        custom_alias=link_data.custom_alias,
        expires_at=link_data.expires_at,
        user_id=user.id if user else None,
    )

    db.add(db_link)
    db.commit()
    db.refresh(db_link)

    return db_link


def get_link_by_short_code(db: Session, short_code: str) -> Optional[Link]:
    """Get a link by its short code."""
    redis = get_redis()

    # Try to get from cache first
    cached_link = redis.get(f"link:{short_code}")
    if cached_link:
        # Update click count in DB asynchronously
        db_link = db.query(Link).filter(Link.short_code == short_code).first()
        if db_link:
            db_link.clicks += 1
            db_link.last_used_at = datetime.utcnow()
            db.commit()

            # Update cache with new click count
            redis.set(f"link:{short_code}", db_link.original_url, ex=3600)  # 1 hour expiry

        return db_link

    # Get from database
    db_link = db.query(Link).filter(Link.short_code == short_code).first()

    if db_link:
        # Check if link has expired
        if db_link.expires_at and db_link.expires_at < datetime.utcnow():
            db_link.is_active = False
            db.commit()
            return None

        # Update click count and last used timestamp
        db_link.clicks += 1
        db_link.last_used_at = datetime.utcnow()
        db.commit()

        # Cache the link
        redis.set(f"link:{short_code}", db_link.original_url, ex=3600)  # 1 hour expiry

    return db_link


def get_link_stats(db: Session, short_code: str) -> Optional[Link]:
    """Get statistics for a link."""
    return db.query(Link).filter(Link.short_code == short_code).first()


def update_link(db: Session, short_code: str, link_data: LinkUpdate, user: User) -> Optional[Link]:
    """Update an existing link."""
    db_link = db.query(Link).filter(Link.short_code == short_code).first()

    if not db_link:
        return None

    # Check if user is the owner of the link
    if db_link.user_id and db_link.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this link")

    # Check custom alias uniqueness if provided
    if link_data.custom_alias and link_data.custom_alias != db_link.custom_alias:
        if len(link_data.custom_alias) < CUSTOM_ALIAS_MIN_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Custom alias must be at least {CUSTOM_ALIAS_MIN_LENGTH} characters",
            )

        existing_alias = db.query(Link).filter(Link.custom_alias == link_data.custom_alias).first()
        if existing_alias:
            raise HTTPException(status_code=400, detail="Custom alias already exists")

        db_link.custom_alias = link_data.custom_alias
        db_link.short_code = link_data.custom_alias

    # Update other fields if provided
    if link_data.original_url:
        db_link.original_url = link_data.original_url

    if link_data.expires_at:
        db_link.expires_at = link_data.expires_at

    db.commit()
    db.refresh(db_link)

    # Update or invalidate cache
    redis = get_redis()
    redis.delete(f"link:{short_code}")

    return db_link


def delete_link(db: Session, short_code: str, user: User) -> bool:
    """Delete a link."""
    db_link = db.query(Link).filter(Link.short_code == short_code).first()

    if not db_link:
        return False

    # Check if user is the owner of the link
    if db_link.user_id and db_link.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this link")

    # Instead of deleting, mark as inactive
    db_link.is_active = False
    db.commit()

    # Invalidate cache
    redis = get_redis()
    redis.delete(f"link:{short_code}")

    return True


def search_by_original_url(db: Session, original_url: str) -> list[Link]:
    """Search for links by their original URL."""
    return db.query(Link).filter(Link.original_url == original_url, Link.is_active == True).all()


def cleanup_expired_links(db: Session) -> int:
    """Mark expired links as inactive."""
    now = datetime.utcnow()
    expired_links = db.query(Link).filter(Link.expires_at < now, Link.is_active == True).all()

    count = 0
    for link in expired_links:
        link.is_active = False
        count += 1

    db.commit()
    return count
