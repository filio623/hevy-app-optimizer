from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from .hevy_api import HevyAPI

class WorkoutOptimizer:
    """
    Service for analyzing workout data and providing optimization suggestions.
    """
    
    def __init__(self, hevy_api: HevyAPI):
        """
        Initialize the WorkoutOptimizer with a HevyAPI instance.
        
        Args:
            hevy_api: An instance of HevyAPI to fetch workout data
        """
        self.hevy_api = hevy_api
    
    async def analyze_workout_history(self, days: int = 30) -> Dict[str, Any]:
        """
        Analyze workout history for the specified number of days.
        
        Args:
            days: Number of days of workout history to analyze
            
        Returns:
            Dict containing analysis results
        """
        # Calculate the date range
        end_date = datetime.utcnow().replace(tzinfo=None)  # Make naive datetime
        start_date = end_date - timedelta(days=days)
        
        print(f"Analyzing workouts from {start_date.isoformat()} to {end_date.isoformat()}")
        
        try:
            # Try using get_workouts instead of get_workout_events
            workouts_response = await self.hevy_api.get_workouts(limit=100, page=1)
            print(f"Workouts response: {workouts_response}")
            
            # Extract workouts from the response
            workouts = []
            if "data" in workouts_response:
                workouts = workouts_response["data"]
            
            print(f"Found {len(workouts)} workouts directly")
            
            # Filter workouts by date
            filtered_workouts = []
            for workout in workouts:
                if "start_time" in workout:
                    # Convert to naive datetime for comparison
                    workout_date = datetime.fromisoformat(workout["start_time"].replace("Z", "+00:00"))
                    workout_date = workout_date.replace(tzinfo=None)
                    if start_date <= workout_date <= end_date:
                        filtered_workouts.append(workout)
            
            print(f"Filtered to {len(filtered_workouts)} workouts within date range")
            
            # Analyze the workouts
            return self._analyze_workouts(filtered_workouts)
        except Exception as e:
            print(f"Error in analyze_workout_history: {str(e)}")
            return {
                "total_workouts": 0,
                "message": f"Error analyzing workout history: {str(e)}"
            }
    
    def _analyze_workouts(self, workouts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a list of workouts to extract insights.
        
        Args:
            workouts: List of workout data
            
        Returns:
            Dict containing analysis results
        """
        if not workouts:
            return {
                "total_workouts": 0,
                "message": "No workout data available for analysis."
            }
        
        # Basic statistics
        total_workouts = len(workouts)
        
        # Calculate workout frequency
        if total_workouts > 1:
            # Sort workouts by date
            sorted_workouts = sorted(workouts, key=lambda w: w.get("start_time", ""))
            first_workout_date = datetime.fromisoformat(sorted_workouts[0].get("start_time", "").replace("Z", "+00:00"))
            last_workout_date = datetime.fromisoformat(sorted_workouts[-1].get("start_time", "").replace("Z", "+00:00"))
            days_between = (last_workout_date - first_workout_date).days + 1
            workouts_per_week = (total_workouts / days_between) * 7
        else:
            workouts_per_week = 0
        
        # Group workouts by exercise type
        exercise_stats = {}
        for workout in workouts:
            for exercise in workout.get("exercises", []):
                exercise_id = exercise.get("exercise_template_id")
                if not exercise_id:
                    continue
                
                if exercise_id not in exercise_stats:
                    exercise_stats[exercise_id] = {
                        "name": exercise.get("title", "Unknown Exercise"),
                        "count": 0,
                        "total_weight": 0,
                        "total_reps": 0,
                        "sets": [],
                        "dates": [],
                        "progression": []
                    }
                
                stats = exercise_stats[exercise_id]
                stats["count"] += 1
                
                # Track workout dates
                workout_date = workout.get("start_time", "")
                if workout_date:
                    stats["dates"].append(workout_date)
                
                # Collect set data
                for set_data in exercise.get("sets", []):
                    weight = set_data.get("weight_kg", 0)
                    reps = set_data.get("reps", 0)
                    
                    # Handle None values
                    weight = weight if weight is not None else 0
                    reps = reps if reps is not None else 0
                    
                    stats["total_weight"] += weight
                    stats["total_reps"] += reps
                    stats["sets"].append({
                        "weight": weight,
                        "reps": reps,
                        "date": workout_date
                    })
        
        # Calculate progression for each exercise
        for exercise_id, stats in exercise_stats.items():
            if len(stats["sets"]) > 1:
                # Sort sets by date
                sorted_sets = sorted(stats["sets"], key=lambda s: s.get("date", ""))
                
                # Calculate progression
                for i in range(1, len(sorted_sets)):
                    prev_set = sorted_sets[i-1]
                    curr_set = sorted_sets[i]
                    
                    # Only compare if both sets have valid weights and reps
                    if prev_set["weight"] is not None and curr_set["weight"] is not None:
                        weight_diff = curr_set["weight"] - prev_set["weight"]
                        if weight_diff > 0:
                            stats["progression"].append(f"Increased weight by {weight_diff:.1f}kg")
                        elif weight_diff < 0:
                            stats["progression"].append(f"Decreased weight by {abs(weight_diff):.1f}kg")
                    
                    if prev_set["reps"] is not None and curr_set["reps"] is not None:
                        reps_diff = curr_set["reps"] - prev_set["reps"]
                        if reps_diff > 0:
                            stats["progression"].append(f"Increased reps by {reps_diff}")
                        elif reps_diff < 0:
                            stats["progression"].append(f"Decreased reps by {abs(reps_diff)}")
        
        # Calculate average stats
        for exercise_id, stats in exercise_stats.items():
            valid_sets = [s for s in stats["sets"] if s["weight"] is not None and s["reps"] is not None]
            if valid_sets:
                stats["avg_weight"] = sum(s["weight"] for s in valid_sets) / len(valid_sets)
                stats["avg_reps"] = sum(s["reps"] for s in valid_sets) / len(valid_sets)
            else:
                stats["avg_weight"] = 0
                stats["avg_reps"] = 0
        
        return {
            "total_workouts": total_workouts,
            "workouts_per_week": round(workouts_per_week, 1),
            "exercise_stats": exercise_stats,
            "message": f"Analyzed {total_workouts} workouts with {len(exercise_stats)} different exercises."
        }
    
    def _generate_exercise_suggestion(self, exercise_name: str, progression: List[str], avg_weight: float, avg_reps: float) -> str:
        """
        Generate a personalized suggestion for a specific exercise based on progression data.
        
        Args:
            exercise_name: Name of the exercise
            progression: List of progression changes (e.g., "Increased weight by 2.5kg")
            avg_weight: Average weight used for the exercise
            avg_reps: Average reps performed for the exercise
            
        Returns:
            A personalized suggestion string
        """
        if not progression:
            return f"Keep tracking your progress with {exercise_name}. Try to gradually increase weight or reps."
        
        # Analyze progression patterns
        weight_increases = sum(1 for p in progression if "Increased weight" in p)
        weight_decreases = sum(1 for p in progression if "Decreased weight" in p)
        rep_increases = sum(1 for p in progression if "Increased reps" in p)
        rep_decreases = sum(1 for p in progression if "Decreased reps" in p)
        
        # Determine overall trend
        if weight_increases > weight_decreases and rep_increases >= rep_decreases:
            trend = "improving"
        elif weight_decreases > weight_increases and rep_decreases >= rep_increases:
            trend = "declining"
        else:
            trend = "stable"
        
        # Generate suggestion based on trend
        if trend == "improving":
            if weight_increases > rep_increases:
                return f"Great progress with {exercise_name}! You're consistently increasing weight. Consider adding more reps to build endurance."
            else:
                return f"Good work on {exercise_name}! You're increasing reps well. Try adding more weight to build strength."
        
        elif trend == "declining":
            if weight_decreases > rep_decreases:
                return f"For {exercise_name}, you've been decreasing weight. Consider a deload week to recover, then gradually increase weight again."
            else:
                return f"You've been decreasing reps on {exercise_name}. Focus on maintaining form and gradually increasing reps back to your previous level."
        
        else:  # stable
            return f"Your {exercise_name} performance is stable. Try a progressive overload approach: increase weight by 2.5kg or add 2 reps to your sets."
    
    def _generate_recommendations(self, exercise_stats: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        Generate overall workout recommendations based on exercise analysis.
        
        Args:
            exercise_stats: Dictionary containing statistics for each exercise
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Analyze workout frequency
        total_exercises = len(exercise_stats)
        if total_exercises == 0:
            return ["Start tracking your workouts to receive personalized recommendations."]
        
        # Check for exercise variety
        if total_exercises < 5:
            recommendations.append("Try incorporating more variety into your workouts. Aim for at least 5 different exercises.")
        
        # Analyze exercise frequency
        exercise_frequencies = [stats["count"] for stats in exercise_stats.values()]
        avg_frequency = sum(exercise_frequencies) / total_exercises if exercise_frequencies else 0
        
        if avg_frequency < 2:
            recommendations.append("You're not repeating exercises often enough. Consistency is key for progress.")
        
        # Check for progression
        exercises_with_progression = sum(1 for stats in exercise_stats.values() if stats["progression"])
        if exercises_with_progression < total_exercises * 0.5:
            recommendations.append("Focus on progressive overload. Try to gradually increase weight or reps for at least half of your exercises.")
        
        # Analyze rest periods
        exercises_with_short_rest = sum(1 for stats in exercise_stats.values() if stats.get("rest_seconds", 0) < 60)
        if exercises_with_short_rest > total_exercises * 0.3:
            recommendations.append("You might be resting too little between sets. Aim for 60-90 seconds of rest for most exercises.")
        
        # Check for balanced training
        upper_body_exercises = sum(1 for stats in exercise_stats.values() if any(muscle in stats["name"].lower() for muscle in ["chest", "back", "shoulder", "arm", "bicep", "tricep"]))
        lower_body_exercises = sum(1 for stats in exercise_stats.values() if any(muscle in stats["name"].lower() for muscle in ["leg", "squat", "deadlift", "calf"]))
        core_exercises = sum(1 for stats in exercise_stats.values() if any(muscle in stats["name"].lower() for muscle in ["core", "ab", "plank"]))
        
        if upper_body_exercises > lower_body_exercises * 1.5:
            recommendations.append("Your workout might be upper-body focused. Consider adding more leg exercises for balanced training.")
        elif lower_body_exercises > upper_body_exercises * 1.5:
            recommendations.append("Your workout might be lower-body focused. Consider adding more upper body exercises for balanced training.")
        
        if core_exercises < 2:
            recommendations.append("Consider adding more core exercises to strengthen your midsection.")
        
        # Add general recommendations if we don't have enough specific ones
        if len(recommendations) < 3:
            recommendations.append("Stay consistent with your workouts and focus on proper form.")
            recommendations.append("Consider tracking your nutrition to support your training goals.")
        
        return recommendations
    
    async def get_optimization_suggestions(self, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive workout optimization suggestions based on recent workout history.
        
        Args:
            days: Number of days of workout history to analyze
            
        Returns:
            Dictionary containing optimization suggestions and analysis
        """
        # Analyze workout history
        analysis = await self.analyze_workout_history(days)
        
        # Generate exercise-specific suggestions
        exercise_suggestions = {}
        for exercise_id, stats in analysis.get("exercise_stats", {}).items():
            suggestion = self._generate_exercise_suggestion(
                stats["name"],
                stats.get("progression", []),
                stats.get("avg_weight", 0),
                stats.get("avg_reps", 0)
            )
            exercise_suggestions[exercise_id] = {
                "name": stats["name"],
                "suggestion": suggestion,
                "stats": {
                    "count": stats["count"],
                    "avg_weight": round(stats.get("avg_weight", 0), 1),
                    "avg_reps": round(stats.get("avg_reps", 0), 1),
                    "progression": stats.get("progression", [])[-3:] if stats.get("progression") else []
                }
            }
        
        # Generate overall recommendations
        recommendations = self._generate_recommendations(analysis.get("exercise_stats", {}))
        
        # Compile the complete report
        return {
            "summary": f"Based on analysis of {analysis['total_workouts']} workouts over the past {days} days.",
            "workout_frequency": f"{analysis.get('workouts_per_week', 0)} workouts per week",
            "suggestions": recommendations,
            "exercise_suggestions": exercise_suggestions,
            "message": analysis.get("message", "Analysis complete.")
        } 