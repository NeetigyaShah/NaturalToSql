
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints.sql_generator import router
from app.db.database import engine, test_connection
from app.db.models import Base
from contextlib import asynccontextmanager

# Create database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if test_connection():
        print("✅ Database connection successful")
    else:
        print("❌ Database connection failed")
    yield
    # Shutdown (if needed)

app = FastAPI(
    title="NaturaltoSQL API",
    description="AI-Powered SQL Query Generator",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Added 127.0.0.1
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Include routers
app.include_router(router, prefix="/api", tags=["SQL Generator"])

@app.get("/")
async def root():
    return {"message": "NaturaltoSQL API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)