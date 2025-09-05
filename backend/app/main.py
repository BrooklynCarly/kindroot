from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="KindRoot API",
    description="API for KindRoot application",
    version="0.1.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to KindRoot API"}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Sample endpoint to test Google Sheets integration
@app.get("/api/sheets/test")
async def test_sheets_connection():
    # This will be implemented in the next steps
    return {"status": "Google Sheets integration not yet configured"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
