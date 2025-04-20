import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_workout_analysis():
    """Test the workout analysis endpoint"""
    print("\n=== Testing Workout Analysis ===")
    response = requests.get(f"{BASE_URL}/optimizer/analysis?days=30")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Total Workouts: {data.get('total_workouts', 0)}")
        print(f"Message: {data.get('message', '')}")
        print(f"Exercise Stats: {len(data.get('exercise_stats', {}))} exercises")
    else:
        print(f"Error: {response.text}")

def test_optimization_suggestions():
    """Test the optimization suggestions endpoint"""
    print("\n=== Testing Optimization Suggestions ===")
    response = requests.get(f"{BASE_URL}/optimizer/suggestions?days=30")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Summary: {data.get('summary', '')}")
        print(f"Workout Frequency: {data.get('workout_frequency', '')}")
        print(f"Suggestions: {len(data.get('suggestions', []))} suggestions")
        print(f"Exercise Suggestions: {len(data.get('exercise_suggestions', {}))} exercises")
    else:
        print(f"Error: {response.text}")

def test_ai_optimization_insights():
    """Test the AI optimization insights endpoint"""
    print("\n=== Testing AI Optimization Insights ===")
    response = requests.get(f"{BASE_URL}/optimizer/ai-insights?days=30")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Summary: {data.get('summary', '')}")
        print(f"Recommendations: {len(data.get('recommendations', []))} recommendations")
    else:
        print(f"Error: {response.text}")

def test_chat_about_workout_optimization():
    """Test the chat endpoint"""
    print("\n=== Testing Chat About Workout Optimization ===")
    message = "How can I improve my bench press?"
    response = requests.post(
        f"{BASE_URL}/optimizer/chat",
        json={"message": message}
    )
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {data.get('response', '')[:200]}...")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    print("Testing Hevy Workout Optimizer API Endpoints")
    print("===========================================")
    
    test_workout_analysis()
    test_optimization_suggestions()
    test_ai_optimization_insights()
    test_chat_about_workout_optimization()
    
    print("\nAll tests completed!") 