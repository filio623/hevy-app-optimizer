from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from ..services.workout_optimizer import WorkoutOptimizer
from ..services.ai_workout_optimizer import AIWorkoutOptimizer
from ..dependencies import get_workout_optimizer, get_ai_optimizer

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@router.get("/analysis", response_model=Dict[str, Any])
async def get_workout_analysis(
    days: int = Query(30, description="Number of days of workout history to analyze"),
    optimizer: WorkoutOptimizer = Depends(get_workout_optimizer)
):
    """
    Get workout analysis for the specified number of days.
    """
    try:
        analysis = await optimizer.analyze_workout_history(days)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing workout history: {str(e)}")

@router.get("/suggestions", response_model=Dict[str, Any])
async def get_optimization_suggestions(
    days: int = Query(30, description="Number of days of workout history to analyze"),
    optimizer: WorkoutOptimizer = Depends(get_workout_optimizer)
):
    """
    Get workout optimization suggestions based on recent workout history.
    """
    try:
        suggestions = await optimizer.get_optimization_suggestions(days)
        return suggestions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting optimization suggestions: {str(e)}")

@router.get("/ai-insights", response_model=Dict[str, Any])
async def get_ai_optimization_insights(
    days: int = Query(30, description="Number of days of workout history to analyze"),
    ai_optimizer: AIWorkoutOptimizer = Depends(get_ai_optimizer)
):
    """
    Get AI-enhanced workout optimization insights.
    """
    try:
        insights = await ai_optimizer.get_ai_optimization_insights(days)
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting AI insights: {str(e)}")

@router.post("/chat", response_model=Dict[str, Any])
async def chat_about_workout_optimization(
    request: ChatRequest = Body(...),
    ai_optimizer: AIWorkoutOptimizer = Depends(get_ai_optimizer)
):
    """
    Chat with the AI about workout optimization.
    """
    try:
        response = await ai_optimizer.chat_about_workout_optimization(request.message)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in chat: {str(e)}") 