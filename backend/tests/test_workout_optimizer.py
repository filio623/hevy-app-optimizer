import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from backend.app.services.workout_optimizer import WorkoutOptimizer
from backend.app.services.hevy_api import HevyAPI

@pytest.fixture
def mock_hevy_api():
    """Create a mock HevyAPI instance for testing"""
    api = AsyncMock(spec=HevyAPI)
    return api

@pytest.fixture
def workout_optimizer(mock_hevy_api):
    """Create a WorkoutOptimizer instance with a mock HevyAPI"""
    return WorkoutOptimizer(mock_hevy_api)

class TestWorkoutOptimizer:
    @pytest.mark.asyncio
    async def test_analyze_workout_history_empty(self, workout_optimizer, mock_hevy_api):
        """Test analyzing workout history with no workouts"""
        # Mock the API responses
        mock_hevy_api.get_workout_events.return_value = {"events": []}
        
        # Call the method
        result = await workout_optimizer.analyze_workout_history(days=30)
        
        # Verify the result
        assert result["total_workouts"] == 0
        assert "No workout data available for analysis" in result["message"]
        
        # Verify the API was called correctly
        mock_hevy_api.get_workout_events.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_workout_history_with_data(self, workout_optimizer, mock_hevy_api):
        """Test analyzing workout history with sample workout data"""
        # Create sample workout data
        today = datetime.utcnow()
        yesterday = today - timedelta(days=1)
        
        # Mock the API responses
        mock_hevy_api.get_workout_events.return_value = {
            "events": [
                {"workout_id": "workout1"},
                {"workout_id": "workout2"}
            ]
        }
        
        mock_hevy_api.get_workout.side_effect = [
            {
                "workout": {
                    "id": "workout1",
                    "start_time": today.isoformat(),
                    "exercises": [
                        {
                            "exercise_template_id": "D04AC939",
                            "title": "Squat (Barbell)",
                            "sets": [
                                {
                                    "weight_kg": 100,
                                    "reps": 10
                                }
                            ]
                        }
                    ]
                }
            },
            {
                "workout": {
                    "id": "workout2",
                    "start_time": yesterday.isoformat(),
                    "exercises": [
                        {
                            "exercise_template_id": "D04AC939",
                            "title": "Squat (Barbell)",
                            "sets": [
                                {
                                    "weight_kg": 95,
                                    "reps": 12
                                }
                            ]
                        }
                    ]
                }
            }
        ]
        
        # Call the method
        result = await workout_optimizer.analyze_workout_history(days=30)
        
        # Verify the result
        assert result["total_workouts"] == 2
        assert "exercise_analysis" in result
        assert "recommendations" in result
        
        # Check exercise analysis
        exercise_analysis = result["exercise_analysis"]
        assert "D04AC939" in exercise_analysis
        assert exercise_analysis["D04AC939"]["name"] == "Squat (Barbell)"
        assert exercise_analysis["D04AC939"]["frequency"] == 2
        assert exercise_analysis["D04AC939"]["progression"] == "improving"
        
        # Verify the API was called correctly
        mock_hevy_api.get_workout_events.assert_called_once()
        assert mock_hevy_api.get_workout.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_optimization_suggestions(self, workout_optimizer, mock_hevy_api):
        """Test getting optimization suggestions"""
        # Mock the analyze_workout_history method
        with patch.object(workout_optimizer, 'analyze_workout_history') as mock_analyze:
            mock_analyze.return_value = {
                "total_workouts": 5,
                "exercise_analysis": {
                    "D04AC939": {
                        "name": "Squat (Barbell)",
                        "frequency": 3,
                        "average_weight": 100,
                        "average_reps": 10,
                        "progression": "improving",
                        "suggestion": "Great progress with Squat (Barbell)! Consider increasing weight by 2.5-5kg or adding an extra set."
                    }
                },
                "recommendations": [
                    "Consider adding more exercise variety to your workouts for balanced development."
                ]
            }
            
            # Call the method
            result = await workout_optimizer.get_optimization_suggestions(days=30)
            
            # Verify the result
            assert "analysis" in result
            assert "summary" in result
            assert "suggestions" in result
            assert "exercise_insights" in result
            assert "Based on analysis of 5 workouts over the past 30 days" in result["summary"]
            assert len(result["suggestions"]) > 0
            assert "D04AC939" in result["exercise_insights"]
            
            # Verify the analyze_workout_history method was called
            mock_analyze.assert_called_once_with(30) 