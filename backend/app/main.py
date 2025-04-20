from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import httpx
from contextlib import asynccontextmanager
import traceback

from .routers import chat_router, workouts_router, analysis_router, optimizer_router
from .services.hevy_api import HevyAPI
from .services.workout_optimizer import WorkoutOptimizer
from .services.ai_workout_optimizer import AIWorkoutOptimizer

# Load environment variables
load_dotenv()

# Initialize services
hevy_api = HevyAPI()
workout_optimizer = WorkoutOptimizer(hevy_api)
ai_optimizer = AIWorkoutOptimizer(hevy_api)

# --- UPDATED: Lifespan context manager for startup/shutdown events ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    print("--- FastAPI App Startup: Initializing HTTP client and loading cache... ---")
    # Initialize the client passed to HevyAPI (or re-init if needed)
    # Ensure the client is initialized before loading cache
    app.state.http_client = httpx.AsyncClient(headers=hevy_api.headers) # Store client in app state if needed elsewhere
    hevy_api.client = app.state.http_client # Ensure HevyAPI uses this client
    
    # Load template cache using the initialized client via HevyAPI instance
    # --- ADDED Try/Except for robust startup logging ---
    try:
        await AIWorkoutOptimizer.load_templates_cache(hevy_api)
        print("--- FastAPI App Startup: Cache loading call completed. ---")
    except Exception as e:
        print(f"--- FastAPI App Startup: !!! FAILED to load template cache: {e} !!! ---")
        traceback.print_exc() # Print full traceback on startup error
        # Optionally re-raise or handle differently if needed
    # --- END Try/Except ---
    
    print("--- FastAPI App Startup: Lifespan startup phase complete. Yielding... ---")
    yield
    # Code to run on shutdown
    print("--- FastAPI App Shutdown: Closing HTTP client... ---")
    await app.state.http_client.aclose()
    print("--- FastAPI App Shutdown: HTTP client closed. --- ")

# Create FastAPI app and attach lifespan
app = FastAPI(
    title="Hevy Workout Optimizer API",
    description="API for analyzing and optimizing workouts using AI",
    version="1.0.0",
    lifespan=lifespan # Assign the lifespan manager
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(workouts_router, prefix="/api/workouts", tags=["workouts"])
app.include_router(analysis_router, prefix="/api/analysis", tags=["analysis"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(optimizer_router, prefix="/api/optimizer", tags=["optimizer"])

@app.get("/")
async def root():
    """Root endpoint to verify API is running"""
    return {
        "status": "online",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 