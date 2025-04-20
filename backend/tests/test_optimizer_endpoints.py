import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_workout_analysis():
    """Test getting workout analysis"""
    response = client.get("/api/optimizer/analysis?days=30")
    assert response.status_code == 200
    data = response.json()
    assert "total_workouts" in data
    assert isinstance(data["total_workouts"], int)
    
    # If there are workouts, check for exercise stats
    if data["total_workouts"] > 0:
        assert "exercise_stats" in data
        assert isinstance(data["exercise_stats"], dict)
    else:
        # If no workouts, check for appropriate message
        assert "message" in data
        assert "No workout data available" in data["message"]

def test_get_optimization_suggestions():
    """Test getting optimization suggestions"""
    response = client.get("/api/optimizer/suggestions?days=30")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "workout_frequency" in data
    assert "suggestions" in data
    assert "exercise_suggestions" in data
    assert "message" in data

def test_get_ai_optimization_insights():
    """Test getting AI optimization insights"""
    response = client.get("/api/optimizer/ai-insights?days=30")
    assert response.status_code == 200
    data = response.json()
    assert "workout_analysis" in data
    assert "ai_insights" in data
    assert "recommendations" in data
    assert "exercise_insights" in data
    assert "summary" in data

def test_chat_about_workout_optimization():
    """Test chatting about workout optimization"""
    response = client.post("/api/optimizer/chat", json={"message": "How can I improve my bench press?"})
    assert response.status_code == 200
    data = response.json()
    assert "response" in data 