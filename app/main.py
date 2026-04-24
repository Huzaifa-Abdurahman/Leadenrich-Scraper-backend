import os
import sys
import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Optimized Logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("leadenrich")

# Load environment
load_dotenv()

# Import routes
try:
    from app.routes import upload, auth
except ImportError:
    from routes import upload, auth

# Initialize FastAPI
app = FastAPI(title="LeadEnrich - Neural Extraction Engine")


# CORS support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(upload.router, prefix="/api")
app.include_router(auth.router, prefix="/api")


@app.get("/")
async def root():
    return {"status": "ENGINE_ACTIVE", "system": "NEURAL_EXTRACTION_V2"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
