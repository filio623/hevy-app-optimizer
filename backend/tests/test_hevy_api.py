import pytest
from app.services.hevy_api import HevyAPI
from typing import Dict, Any
import requests
from datetime import datetime, timedelta
import asyncio

@pytest.fixture
def hevy_api():
    """Create a HevyAPI instance for testing"""
    return HevyAPI()

# Workout Endpoint Tests
class TestWorkoutEndpoints:
    @pytest.mark.asyncio
    async def test_get_workouts_pagination(self, hevy_api: HevyAPI):
        """Test workout pagination with different page sizes"""
        # Test default pagination
        response = await hevy_api.get_workouts()
        assert isinstance(response, dict)
        assert "data" in response
        assert "total" in response
        assert "page" in response
        assert "limit" in response
        assert "has_more" in response
        assert len(response["data"]) <= 10  # Default limit

        # Test custom page size
        response = await hevy_api.get_workouts(limit=2, page=1)
        assert len(response["data"]) <= 2
        
        # Test second page if available
        if response["has_more"]:
            response2 = await hevy_api.get_workouts(limit=2, page=2)
            assert response2["page"] == 2
            assert len(response2["data"]) <= 2

    @pytest.mark.asyncio
    async def test_get_all_workouts(self, hevy_api: HevyAPI):
        """Test fetching all workouts"""
        workouts = await hevy_api.get_all_workouts()
        assert isinstance(workouts, list)
        if workouts:
            workout = workouts[0]
            assert "id" in workout
            assert "title" in workout

    @pytest.mark.asyncio
    @pytest.mark.serial
    async def test_create_workout(self, hevy_api: HevyAPI):
        """Test creating a workout"""
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=60)
        workout_data = {
            "workout": {
                "title": "Test Workout",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "is_private": True,
                "exercises": [
                    {
                        "exercise_template_id": "D04AC939",
                        "notes": "Test exercise notes",
                        "sets": [
                            {
                                "reps": 10,
                                "type": "normal"
                            }
                        ]
                    }
                ]
            }
        }
        created = await hevy_api.create_workout(workout_data)
        assert isinstance(created, dict)
        assert "workout" in created
        assert isinstance(created["workout"], list)
        assert len(created["workout"]) > 0
        assert created["workout"][0]["title"] == "Test Workout"
        return created["workout"][0]["id"]

    @pytest.mark.asyncio
    @pytest.mark.serial
    async def test_update_workout(self, hevy_api: HevyAPI):
        """Test updating a workout"""
        # First create a workout
        workout_id = await self.test_create_workout(hevy_api)
        
        # Add rate limiting delay
        await asyncio.sleep(2)
        
        # Update the workout
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=30)
        update_data = {
            "workout": {
                "title": "Updated Test Workout",
                "description": "Updated workout description",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "is_private": True,
                "exercises": [
                    {
                        "exercise_template_id": "D04AC939",
                        "notes": "Updated exercise notes",
                        "sets": [
                            {
                                "type": "normal",
                                "weight_kg": 100,
                                "reps": 10
                            }
                        ]
                    }
                ]
            }
        }
        updated = await hevy_api.update_workout(workout_id, update_data)
        assert isinstance(updated, dict)
        assert "workout" in updated
        assert isinstance(updated["workout"], list)
        assert len(updated["workout"]) > 0
        assert updated["workout"][0]["title"] == "Updated Test Workout"
        assert updated["workout"][0]["description"] == "Updated workout description"

    @pytest.mark.asyncio
    async def test_get_workout_count(self, hevy_api: HevyAPI):
        """Test getting total workout count"""
        count = await hevy_api.get_workout_count()
        assert isinstance(count, int)
        assert count >= 0

    @pytest.mark.asyncio
    @pytest.mark.serial
    async def test_get_workout_events(self, hevy_api: HevyAPI):
        """Test getting workout events"""
        try:
            # Calculate date 30 days ago
            since_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
            response = await hevy_api.get_workout_events(since_date)
            assert isinstance(response, dict)
            assert "events" in response
            assert isinstance(response["events"], list)
            assert "page" in response
            assert "page_count" in response
            
            # Check the structure of an event if there are any
            if response["events"]:
                event = response["events"][0]
                assert "type" in event
                assert "workout" in event
                assert isinstance(event["workout"], dict)
                assert "id" in event["workout"]
                assert "title" in event["workout"]
        except Exception as e:
            pytest.fail(f"Failed to get workout events: {str(e)}")

# Routine Endpoint Tests
class TestRoutineEndpoints:
    @pytest.mark.asyncio
    async def test_get_routines_pagination(self, hevy_api: HevyAPI):
        """Test routine pagination"""
        response = await hevy_api.get_routines(limit=2, page=1)
        assert isinstance(response, dict)
        assert "data" in response
        assert "total" in response
        assert len(response["data"]) <= 2

    @pytest.mark.asyncio
    async def test_get_all_routines(self, hevy_api: HevyAPI):
        """Test fetching all routines"""
        routines = await hevy_api.get_all_routines()
        assert isinstance(routines, list)
        if routines:
            routine = routines[0]
            assert "id" in routine
            assert "name" in routine

    @pytest.mark.asyncio
    @pytest.mark.serial
    async def test_create_routine(self, hevy_api: HevyAPI):
        """Test creating a routine"""
        routine_data = {
            "routine": {
                "title": "Test Routine",
                "folder_id": None,
                "notes": "Test notes",
                "exercises": [
                    {
                        "exercise_template_id": "D04AC939",
                        "notes": "Test exercise notes",
                        "rest_seconds": 90,
                        "sets": [
                            {
                                "reps": 10,
                                "type": "normal"
                            }
                        ]
                    }
                ]
            }
        }
        routine = await hevy_api.create_routine(routine_data)
        assert isinstance(routine, dict)
        assert "routine" in routine
        assert isinstance(routine["routine"], list)
        assert len(routine["routine"]) > 0
        assert routine["routine"][0]["title"] == "Test Routine"
        return routine["routine"][0]["id"]

    @pytest.mark.asyncio
    @pytest.mark.serial
    async def test_update_routine(self, hevy_api: HevyAPI):
        """Test updating a routine"""
        # First create a routine
        routine_id = await self.test_create_routine(hevy_api)
        
        # Add rate limiting delay
        await asyncio.sleep(2)
        
        # Update the routine
        update_data = {
            "routine": {
                "title": "Updated Test Routine",
                "notes": "Updated test notes",
                "exercises": [
                    {
                        "exercise_template_id": "D04AC939",
                        "superset_id": None,
                        "rest_seconds": 120,
                        "notes": "Updated exercise notes",
                        "sets": [
                            {
                                "type": "normal",
                                "weight_kg": 100,
                                "reps": 12,
                                "distance_meters": None,
                                "duration_seconds": None,
                                "custom_metric": None
                            }
                        ]
                    }
                ]
            }
        }
        updated = await hevy_api.update_routine(routine_id, update_data)
        assert isinstance(updated, dict)
        assert "routine" in updated
        assert isinstance(updated["routine"], list)
        assert len(updated["routine"]) > 0
        assert updated["routine"][0]["title"] == "Updated Test Routine"
        return updated["routine"][0]["id"]

    @pytest.mark.asyncio
    async def test_get_workout_count(self, hevy_api: HevyAPI):
        """Test getting total workout count"""
        count = await hevy_api.get_workout_count()
        assert isinstance(count, int)
        assert count >= 0

# Exercise Template Endpoint Tests
class TestExerciseTemplateEndpoints:
    @pytest.mark.asyncio
    async def test_get_exercise_templates_pagination(self, hevy_api: HevyAPI):
        """Test exercise template pagination"""
        response = await hevy_api.get_exercise_templates(limit=2, page=1)
        assert isinstance(response, dict)
        assert "data" in response
        assert "total" in response
        assert "page" in response
        assert "limit" in response
        assert "has_more" in response
        assert len(response["data"]) <= 2

    @pytest.mark.asyncio
    async def test_get_all_exercise_templates(self, hevy_api: HevyAPI):
        """Test fetching all exercise templates"""
        templates = await hevy_api.get_all_exercise_templates()
        assert isinstance(templates, list)
        if templates:
            template = templates[0]
            assert "id" in template
            assert "name" in template

    @pytest.mark.asyncio
    async def test_get_single_exercise_template(self, hevy_api: HevyAPI):
        """Test fetching a single exercise template"""
        templates = await hevy_api.get_exercise_templates(limit=1)
        if templates["data"]:
            template_id = templates["data"][0]["id"]
            template = await hevy_api.get_exercise_template(template_id)
            assert isinstance(template, dict)
            assert template["id"] == template_id

# Routine Folder Endpoint Tests
class TestRoutineFolderEndpoints:
    @pytest.mark.asyncio
    @pytest.mark.serial
    async def test_create_routine_folder(self, hevy_api: HevyAPI):
        """Test creating a routine folder"""
        folder_data = {
            "routine_folder": {
                "title": "Test Folder"
            }
        }
        created = await hevy_api.create_routine_folder(folder_data)
        assert isinstance(created, dict)
        assert "routine_folder" in created
        assert isinstance(created["routine_folder"], dict)
        assert "id" in created["routine_folder"]
        assert "title" in created["routine_folder"]
        assert created["routine_folder"]["title"] == "Test Folder"
        return created["routine_folder"]["id"]

    @pytest.mark.asyncio
    @pytest.mark.serial
    async def test_routine_folder_operations(self, hevy_api: HevyAPI):
        """Test routine folder operations"""
        # Create a folder
        folder_id = await self.test_create_routine_folder(hevy_api)
        
        # Add rate limiting delay
        await asyncio.sleep(2)
        
        # Get the folder
        folder = await hevy_api.get_routine_folder(folder_id)
        assert isinstance(folder, dict)
        assert "id" in folder
        assert "title" in folder
        assert folder["title"] == "Test Folder"
        assert "created_at" in folder
        assert "updated_at" in folder
        assert "index" in folder

    @pytest.mark.asyncio
    @pytest.mark.serial
    async def test_get_routines_in_folder(self, hevy_api: HevyAPI):
        """Test getting routines in a folder"""
        # First create a folder
        folder_id = await self.test_create_routine_folder(hevy_api)
        
        # Add rate limiting delay
        await asyncio.sleep(2)
        
        # Get routines in the folder
        routines = await hevy_api.get_routines_in_folder(folder_id)
        assert isinstance(routines, list)

# Error Case Tests
class TestErrorCases:
    @pytest.mark.asyncio
    async def test_invalid_workout_id(self, hevy_api: HevyAPI):
        """Test handling of invalid workout ID"""
        with pytest.raises(requests.exceptions.HTTPError):
            await hevy_api.get_workout("invalid_id")

    @pytest.mark.asyncio
    async def test_invalid_routine_id(self, hevy_api: HevyAPI):
        """Test handling of invalid routine ID"""
        with pytest.raises(requests.exceptions.HTTPError):
            await hevy_api.get_routine("invalid_id")

    @pytest.mark.asyncio
    async def test_invalid_template_id(self, hevy_api: HevyAPI):
        """Test handling of invalid exercise template ID"""
        with pytest.raises(requests.exceptions.HTTPError):
            await hevy_api.get_exercise_template("invalid_id")

    @pytest.mark.asyncio
    async def test_invalid_folder_id(self, hevy_api: HevyAPI):
        """Test handling of invalid routine folder ID"""
        with pytest.raises(requests.exceptions.HTTPError):
            await hevy_api.get_routine_folder("invalid_id") 