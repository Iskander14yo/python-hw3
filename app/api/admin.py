from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.core.auth import get_current_admin_user
from app.services import admin_service
from app.models.schemas import Link, User

router = APIRouter(tags=["admin"], prefix="/admin")


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin_user)
):
    success = admin_service.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found or is admin")
    return {"message": "User deleted successfully"}


@router.get("/links/recent", response_model=List[Link])
def get_recent_links(db: Session = Depends(get_db), _: User = Depends(get_current_admin_user)):
    return admin_service.get_recent_links(db)


@router.delete("/links/{short_code}")
def delete_link(
    short_code: str, db: Session = Depends(get_db), _: User = Depends(get_current_admin_user)
):
    success = admin_service.force_delete_link(db, short_code)
    if not success:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"message": "Link deleted successfully"}


@router.get("/users", response_model=List[User])
def get_all_users(db: Session = Depends(get_db), _: User = Depends(get_current_admin_user)):
    return admin_service.get_all_users(db)
