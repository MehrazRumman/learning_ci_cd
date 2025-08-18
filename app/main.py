from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime
from .models import HealthResponse

# Initialize FastAPI app
app = FastAPI(
    title="FastAPI CI/CD Learning Project",
    description="A FastAPI application designed to help learn CI/CD practices",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_model=HealthResponse, tags=["Health"])
async def root():
    """Health check endpoint"""
    return HealthResponse(
        message="FastAPI CI/CD Learning Project is running!",
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
