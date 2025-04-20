from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..services.workout_optimizer import WorkoutOptimizer
from ..services.ai_workout_optimizer import AIWorkoutOptimizer
from ..dependencies import get_workout_optimizer, get_ai_optimizer

router = APIRouter()

@router.get("/history")
async def analyze_workout_history(
    days: int = Query(30, description="Number of days of history to analyze"),
    workout_optimizer: WorkoutOptimizer = Depends(get_workout_optimizer)
) -> Dict[str, Any]:
    """
    Analyze workout history for the specified number of days.
    Returns basic statistics and insights.
    """
    return await workout_optimizer.analyze_workout_history(days)

@router.get("/ai-insights")
async def get_ai_insights(
    days: int = Query(30, description="Number of days of history to analyze"),
    ai_optimizer: AIWorkoutOptimizer = Depends(get_ai_optimizer)
) -> Dict[str, Any]:
    """
    Get AI-enhanced insights and recommendations based on workout history.
    """
    return await ai_optimizer.get_ai_optimization_insights(days)

@router.post("/optimize")
async def optimize_workout(
    workout_data: Dict[str, Any],
    ai_optimizer: AIWorkoutOptimizer = Depends(get_ai_optimizer)
) -> Dict[str, Any]:
    """
    Get optimization suggestions for a specific workout plan.
    """
    return await ai_optimizer.get_workout_specific_response(
        "Please analyze this workout and suggest optimizations.",
        workout_data
    )

@router.get("/progress/{exercise_id}")
async def analyze_exercise_progress(
    exercise_id: str,
    days: int = Query(90, description="Number of days of history to analyze"),
    workout_optimizer: WorkoutOptimizer = Depends(get_workout_optimizer)
) -> Dict[str, Any]:
    """
    Analyze progress for a specific exercise over time.
    """
    analysis = await workout_optimizer.analyze_workout_history(days)
    exercise_data = analysis.get("exercise_analysis", {}).get(exercise_id)
    
    if not exercise_data:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for exercise {exercise_id}"
        )
    
    return exercise_data

@router.get("/recommendations")
async def get_recommendations(
    focus_area: Optional[str] = Query(None, description="Specific area to focus on (e.g., 'strength', 'hypertrophy')"),
    equipment: Optional[List[str]] = Query(None, description="Available equipment"),
    ai_optimizer: AIWorkoutOptimizer = Depends(get_ai_optimizer)
) -> Dict[str, Any]:
    """
    Get personalized workout recommendations based on history and preferences.
    """
    context = {
        "focus_area": focus_area,
        "equipment": equipment
    }
    
    return await ai_optimizer.get_workout_specific_response(
        "Please provide workout recommendations based on the specified preferences.",
        context
    ) 