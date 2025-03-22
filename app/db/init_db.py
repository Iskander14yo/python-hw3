from sqlalchemy.orm import Session
import os

from app.db.database import get_db
from app.models.models import User
from app.services.user_service import create_user
from app.models.schemas import UserCreate


def init_db(db: Session) -> None:
    """Initialize the database with seed data."""
    # Create an admin user if ADMIN_USERNAME and ADMIN_PASSWORD are provided
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")

    if admin_username and admin_password:
        # Check if admin user already exists
        admin_user = db.query(User).filter(User.username == admin_username).first()
        if not admin_user:
            admin = UserCreate(username=admin_username, email=admin_email, password=admin_password)
            create_user(db, admin, is_admin=True)
            print(f"Created admin user: {admin_username}")
        else:
            print(f"Admin user already exists: {admin_username}")


def main() -> None:
    """Initialize database."""
    db = next(get_db())
    init_db(db)


if __name__ == "__main__":
    main()
