from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..services.hevy_api import HevyAPI
from ..dependencies import get_hevy_api

router = APIRouter()

@router.get("/events")
async def get_workout_events(
    days: int = Query(30, description="Number of days of history to fetch"),
    hevy_api: HevyAPI = Depends(get_hevy_api)
) -> Dict[str, Any]:
    """
    Get workout events for the specified number of days.
    """
    start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
    return await hevy_api.get_workout_events(start_date)

@router.get("/{workout_id}")
async def get_workout(
    workout_id: str,
    hevy_api: HevyAPI = Depends(get_hevy_api)
) -> Dict[str, Any]:
    """
    Get details for a specific workout.
    """
    return await hevy_api.get_workout(workout_id)

@router.post("/")
async def create_workout(
    workout_data: Dict[str, Any],
    hevy_api: HevyAPI = Depends(get_hevy_api)
) -> Dict[str, Any]:
    """
    Create a new workout.
    """
    return await hevy_api.create_workout(workout_data)

@router.put("/{workout_id}")
async def update_workout(
    workout_id: str,
    workout_data: Dict[str, Any],
    hevy_api: HevyAPI = Depends(get_hevy_api)
) -> Dict[str, Any]:
    """
    Update an existing workout.
    """
    return await hevy_api.update_workout(workout_id, workout_data)

@router.get("/routines/")
async def get_routines(
    hevy_api: HevyAPI = Depends(get_hevy_api)
) -> Dict[str, Any]:
    """
    Get all routines.
    """
    return await hevy_api.get_routines()

@router.post("/routines/")
async def create_routine(
    routine_data: Dict[str, Any],
    hevy_api: HevyAPI = Depends(get_hevy_api)
) -> Dict[str, Any]:
    """
    Create a new routine.
    """
    return await hevy_api.create_routine(routine_data)

@router.put("/routines/{routine_id}")
async def update_routine(
    routine_id: str,
    routine_data: Dict[str, Any],
    hevy_api: HevyAPI = Depends(get_hevy_api)
) -> Dict[str, Any]:
    """
    Update an existing routine.
    """
    return await hevy_api.update_routine(routine_id, routine_data)

@router.delete("/routines/{routine_id}")
async def delete_routine(
    routine_id: str,
    hevy_api: HevyAPI = Depends(get_hevy_api)
) -> Dict[str, str]:
    """
    Delete a routine.
    """
    await hevy_api.delete_routine(routine_id)
    return {"status": "success", "message": f"Routine {routine_id} deleted"} 