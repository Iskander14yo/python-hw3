from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import engine, Base, get_db
from app.api import auth, links
from app.services.link_service import cleanup_expired_links


# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="URL Shortener API",
    description="A service that allows users to shorten URLs, get analytics, and manage them.",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(links.router)


@app.get("/")
async def root():
    return {"message": "Welcome to URL Shortener API"}


@app.on_event("startup")
async def startup_event():
    # Cleanup expired links on startup
    db = next(get_db())
    cleanup_expired_links(db)
