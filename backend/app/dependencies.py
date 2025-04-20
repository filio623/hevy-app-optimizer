from typing import Generator
from fastapi import Depends
# from sqlalchemy.orm import Session # Session might also be unused now

# Removed: from .core.database import SessionLocal
from .services.hevy_api import HevyAPI
from .services.workout_optimizer import WorkoutOptimizer
from .services.ai_workout_optimizer import AIWorkoutOptimizer
from .services.intent_service import IntentService

# Removed unused get_db function:
# def get_db() -> Generator:
#     try:
#         db = SessionLocal()
#         yield db
#     finally:
#         db.close()

# --- Create Singleton Instances --- 
# Create instances once when the module loads
_hevy_api_instance = HevyAPI()
_ai_optimizer_instance = AIWorkoutOptimizer(hevy_api=_hevy_api_instance)
_intent_service_instance = IntentService(hevy_api=_hevy_api_instance)

# --- Dependency Functions now return singletons --- 
def get_hevy_api() -> HevyAPI:
    """Returns the singleton HevyAPI instance."""
    # TODO: Add error handling if instance creation failed?
    return _hevy_api_instance

def get_workout_optimizer(hevy_api: HevyAPI = Depends(get_hevy_api)) -> WorkoutOptimizer:
    # Note: WorkoutOptimizer might not need to be a singleton if it's stateless,
    # but AIWorkoutOptimizer wraps it, so we only need the AI one as singleton.
    # If needed, create _workout_optimizer_instance similarly.
    # For now, creating it dynamically based on the singleton HevyAPI is fine.
    return WorkoutOptimizer(hevy_api)

def get_ai_optimizer() -> AIWorkoutOptimizer:
    """Returns the singleton AIWorkoutOptimizer instance."""
    # Note: Removed Depends(get_hevy_api) as instance already has it.
    return _ai_optimizer_instance

def get_intent_service() -> IntentService:
    """Returns the singleton IntentService instance."""
    # Note: Removed Depends(get_hevy_api) as instance already has it.
    return _intent_service_instance 