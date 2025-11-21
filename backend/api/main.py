# backend/api/main.py

"""
FastAPI Main Application - GR Cup CLI API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import API_TITLE, API_DESCRIPTION, API_VERSION
from backend.api.routes import cli
import json


# Create FastAPI app
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware (for frontend access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cli.router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "🏎️ GR Cup CLI API",
        "version": API_VERSION,
        "docs": "/docs",
        "health": "/api/v1/cli/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
