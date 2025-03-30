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
    cache_key = f"link:{short_code}"

    # Try to get from cache first
    cached_original_url = redis.get(cache_key)
    if cached_original_url:
        # Cache hit: still need to query DB to check activity/expiration and update stats
        # This avoids returning stale data if link was deactivated/expired but cache not yet invalidated
        db_link = (
            db.query(Link).filter(Link.short_code == short_code, Link.is_active == True).first()
        )
        if db_link:
            now = datetime.now() # Use consistent timezone
            # Check expiration again even on cache hit
            if db_link.expires_at and db_link.expires_at < now:
                 db_link.is_active = False
                 db.commit()
                 redis.delete(cache_key) # Invalidate cache for expired link
                 return None

            if is_redirect:
                db_link.clicks += 1
                db_link.last_used_at = now
                db.commit()
                # No need to update cache here, original_url hasn't changed
            return db_link # Return the full object from DB
        else:
            # Link active in cache but not found/active in DB (edge case, e.g., manual cleanup)
            redis.delete(cache_key) # Clean up inconsistent cache entry
            return None

    # Cache miss: Get from database
    db_link = db.query(Link).filter(Link.short_code == short_code, Link.is_active == True).first()

    if db_link:
        now = datetime.now() # Use consistent timezone
        # Check if link has expired
        if db_link.expires_at and db_link.expires_at < now:
            db_link.is_active = False
            db.commit()
            # Don't cache an expired link
            return None

        if is_redirect:
            # Update click count and last used timestamp
            db_link.clicks += 1
            db_link.last_used_at = now
            db.commit() # Commit stats update before caching

        # Cache the original_url
        redis.set(cache_key, db_link.original_url, ex=redis_ttl)

    return db_link


def get_link_stats(db: Session, short_code: str) -> Optional[Link]:
    """Get statistics for a link."""
    # No caching involved here, just a direct DB query
    return db.query(Link).filter(Link.short_code == short_code, Link.is_active == True).first()


def update_link(db: Session, short_code: str, link_data: LinkUpdate, user: User) -> Optional[Link]:
    """Update an existing link."""
    db_link = db.query(Link).filter(Link.short_code == short_code, Link.is_active == True).first()

    if not db_link:
        return None

    # Check if user is the owner of the link
    if db_link.user_id and db_link.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this link")

    redis = get_redis()
    original_cache_key = f"link:{db_link.short_code}" # Key based on current short_code before update
    new_cache_key = None

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
        db_link.short_code = link_data.custom_alias # Update short_code to new alias
        new_cache_key = f"link:{db_link.short_code}" # Prepare new key for invalidation

    # Update other fields if provided
    if link_data.original_url:
        db_link.original_url = link_data.original_url
        # If original URL changes, the cached value needs update/invalidation

    if link_data.expires_at:
         now = datetime.now() # Use consistent timezone
         if link_data.expires_at <= now:
             raise HTTPException(status_code=400, detail="Expiration date must be in the future")
         db_link.expires_at = link_data.expires_at

    db.commit()
    db.refresh(db_link)

    # Invalidate cache for the original short code
    redis.delete(original_cache_key)

    # If the short_code changed (new alias), invalidate the new cache key too
    if new_cache_key:
        redis.delete(new_cache_key)

    # Consider re-caching if only original_url or expires_at changed, but delete is safest
    # redis.set(original_cache_key, db_link.original_url, ex=...) # Option to re-cache immediately

    return db_link


def delete_link(db: Session, short_code: str, user: User) -> bool:
    """Delete a link (mark as inactive)."""
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
    redis.delete(f"link:{short_code}") # Use the short_code that was used to find the link

    return True


def search_by_original_url(db: Session, original_url: str) -> list[Link]:
    """Search for links by their original URL."""
    # No caching needed for this search operation
    return db.query(Link).filter(Link.original_url == original_url, Link.is_active == True).all()


def cleanup_expired_links(db: Session) -> int:
    """Mark expired links as inactive and invalidate cache."""
    now = datetime.now() # Use consistent timezone
    expired_links = db.query(Link).filter(Link.expires_at < now, Link.is_active == True).all()
    redis = get_redis()

    count = 0
    if not expired_links: # Avoid unnecessary commit if nothing changed
        return 0

    for link in expired_links:
        link.is_active = False
        # Invalidate cache for the expired link
        redis.delete(f"link:{link.short_code}")
        count += 1

    db.commit() # Commit all changes at once
    return count
