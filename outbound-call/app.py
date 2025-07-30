# app.py
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from api.routes import router
from utils.scheduler import CallScheduler
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = CallScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    try:
        # Startup
        logger.info("Starting Lead Management Backend...")
        await scheduler.start_scheduler()
        logger.info("Application started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down application...")
        await scheduler.stop_scheduler()
        logger.info("Application shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="Lead Management Backend",
    description="AI-powered lead calling system with Retell API integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Lead Management Backend API",
        "version": "1.0.0",
        "status": "running"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
        log_level="info"
    )
