from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from starlette.responses import RedirectResponse

from app.core.auth import get_current_active_user, get_optional_current_user
from app.db.database import get_db
from app.models.models import User
from app.models.schemas import LinkCreate, Link, LinkUpdate, LinkStats
from app.services.link_service import (
    create_link,
    get_link_by_short_code,
    get_link_stats,
    update_link,
    delete_link,
    search_by_original_url,
)

router = APIRouter(tags=["links"])


@router.post("/links/shorten", response_model=Link)
async def shorten_url(
    link_data: LinkCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Create a new shortened URL."""
    return create_link(db, link_data, current_user)


@router.get("/{short_code}", response_class=RedirectResponse, status_code=307)
async def redirect_to_url(short_code: str, db: Session = Depends(get_db)):
    """Redirect to the original URL."""
    link = get_link_by_short_code(db, short_code)
    if not link or not link.is_active:
        raise HTTPException(status_code=404, detail="Link not found or expired")

    return link.original_url


@router.get("/links/{short_code}", response_model=Link)
async def get_link_info(short_code: str, db: Session = Depends(get_db)):
    """Get information about a specific link."""
    link = get_link_by_short_code(db, short_code)
    if not link or not link.is_active:
        raise HTTPException(status_code=404, detail="Link not found or expired")

    return link


@router.get("/links/{short_code}/stats", response_model=LinkStats)
async def get_link_statistics(short_code: str, db: Session = Depends(get_db)):
    """Get statistics for a link."""
    link = get_link_stats(db, short_code)
    if not link or not link.is_active:
        raise HTTPException(status_code=404, detail="Link not found or expired")

    return LinkStats(
        short_code=link.short_code,
        original_url=link.original_url,
        created_at=link.created_at,
        last_used_at=link.last_used_at,
        clicks=link.clicks,
    )


@router.put("/links/{short_code}", response_model=Link)
async def update_link_info(
    short_code: str,
    link_data: LinkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a link."""
    updated_link = update_link(db, short_code, link_data, current_user)
    if not updated_link:
        raise HTTPException(status_code=404, detail="Link not found")

    return updated_link


@router.delete("/links/{short_code}", status_code=204)
async def remove_link(
    short_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a link."""
    result = delete_link(db, short_code, current_user)
    if not result:
        raise HTTPException(status_code=404, detail="Link not found")

    return Response(status_code=204)


@router.get("/links/search", response_model=List[Link])
async def search_links(original_url: str, db: Session = Depends(get_db)):
    """Search for links by original URL."""
    links = search_by_original_url(db, original_url)
    return links
