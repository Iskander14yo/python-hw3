from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    DateTime,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression, func

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    links = relationship("Link", back_populates="owner")


class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String, nullable=False)
    original_url = Column(Text, nullable=False)
    custom_alias = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    clicks = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    owner = relationship("User", back_populates="links")

    # unique constraint on short_code and is_active (if True)
    __table_args__ = (
        Index(
            "short_code", "is_active", unique=True, postgresql_where=expression.true() == is_active
        ),
    )
