import os
import random
import string
from datetime import datetime, timedelta, timezone
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
        existing_alias = (
            db.query(Link)
            .filter(Link.custom_alias == link_data.custom_alias, Link.is_active == True)
            .first()
        )
        if existing_alias:
            raise HTTPException(status_code=400, detail="Custom alias already exists")

        short_code = link_data.custom_alias
    else:
        # Generate a unique short code
        while True:
            short_code = generate_short_code()
            existing_link = (
                db.query(Link)
                .filter(Link.short_code == short_code, Link.is_active == True)
                .first()
            )
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

    # Handle expiration date
    now = datetime.now(timezone.utc)
    if link_data.expires_at:
        # Validate that expires_at is in the future
        if link_data.expires_at <= now:
            raise HTTPException(status_code=400, detail="Expiration date must be in the future")
        expires_at = link_data.expires_at
    else:
        # Set default expiration based on LINK_INACTIVE_DAYS
        inactive_days = int(os.getenv("LINK_INACTIVE_DAYS", "30"))
        expires_at = now + timedelta(days=inactive_days)

    # Create new link
    db_link = Link(
        short_code=short_code,
        original_url=link_data.original_url,
        custom_alias=link_data.custom_alias,
        expires_at=expires_at,
        user_id=user.id if user else None,
    )

    db.add(db_link)
    db.commit()
    db.refresh(db_link)

    return db_link


def get_link_by_short_code(
    db: Session, short_code: str, is_redirect: bool = True
) -> Optional[Link]:
    """Get a link by its short code."""
    redis = get_redis()
    redis_ttl = int(os.getenv("REDIS_CACHE_TTL", "3600"))

    # Try to get from cache first
    cached_link = redis.get(f"link:{short_code}")
    if cached_link:
        # Update click count in DB asynchronously
        db_link = (
            db.query(Link).filter(Link.short_code == short_code, Link.is_active == True).first()
        )
        if db_link and is_redirect:
            db_link.clicks += 1
            db_link.last_used_at = datetime.now()
            db.commit()

            # Update cache with new click count
            # redis.set(f"link:{short_code}", db_link.original_url, ex=redis_ttl)

        return db_link

    # Get from database
    db_link = db.query(Link).filter(Link.short_code == short_code, Link.is_active == True).first()

    if db_link and is_redirect:
        # Check if link has expired
        if db_link.expires_at and db_link.expires_at < datetime.now():
            db_link.is_active = False
            db.commit()
            return None

        # Update click count and last used timestamp
        db_link.clicks += 1
        db_link.last_used_at = datetime.now()
        db.commit()

        # Cache the link
        redis.set(f"link:{short_code}", db_link.original_url, ex=redis_ttl)

    return db_link


def get_link_stats(db: Session, short_code: str) -> Optional[Link]:
    """Get statistics for a link."""
    return db.query(Link).filter(Link.short_code == short_code, Link.is_active == True).first()


def update_link(db: Session, short_code: str, link_data: LinkUpdate, user: User) -> Optional[Link]:
    """Update an existing link."""
    db_link = db.query(Link).filter(Link.short_code == short_code, Link.is_active == True).first()

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

        existing_alias = (
            db.query(Link)
            .filter(Link.custom_alias == link_data.custom_alias, Link.is_active == True)
            .first()
        )
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
    db_link = db.query(Link).filter(Link.short_code == short_code, Link.is_active == True).first()

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
    now = datetime.now()
    expired_links = db.query(Link).filter(Link.expires_at < now, Link.is_active == True).all()

    count = 0
    for link in expired_links:
        link.is_active = False
        count += 1

    db.commit()
    return count
