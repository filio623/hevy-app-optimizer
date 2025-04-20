import os
import requests
import asyncio
import httpx
import traceback
from typing import Optional, Dict, Any, List, TypedDict
from dotenv import load_dotenv
from ..core.config import get_settings

load_dotenv()

KG_TO_LBS = 2.20462 # Conversion Factor

class PaginatedResponse(TypedDict):
    """Type definition for paginated API responses"""
    data: List[Dict[str, Any]]
    total: int
    page: int
    limit: int
    has_more: bool

class HevyAPI:
    """
    A client for interacting with the Hevy API.
    Documentation: https://api.hevyapp.com/docs/
    """
    BASE_URL = "https://api.hevyapp.com/v1"
    
    def __init__(self):
        """Initialize the Hevy API client with authentication."""
        settings = get_settings()
        self.api_key = settings.HEVY_API_KEY
        if not self.api_key:
            raise ValueError("HEVY_API_KEY environment variable is not set")
        
        self.headers = {
            "api-key": self.api_key,
            "Accept": "application/json"
        }
        self.client = httpx.AsyncClient(headers=self.headers)
    
    async def get_workouts(self, limit: int = 10, page: int = 1) -> Dict[str, Any]:
        """
        Fetch recent workouts with pagination.
        
        Args:
            limit (int): Number of workouts to return per page (default: 10)
            page (int): Page number to fetch (default: 1)
            
        Returns:
            Dict containing:
                - data: List of workout data
                - total: Total number of workouts
                - page: Current page number
                - limit: Items per page
                - has_more: Whether there are more pages
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/workouts",
                headers=self.headers,
                params={"limit": limit, "page": page}
            )
            response.raise_for_status()
            data = response.json()
            
            # Transform response to match our standard format
            workouts = data.get("workouts", [])

            # --- Add lbs Conversion ---
            for workout in workouts:
                for exercise in workout.get("exercises", []):
                    for set_data in exercise.get("sets", []):
                        weight_kg = set_data.get("weight_kg")
                        if weight_kg is not None:
                            set_data['weight_lbs'] = weight_kg * KG_TO_LBS
                        else:
                            # Explicitly set to None if kg is None
                            set_data['weight_lbs'] = None
            # --- End Conversion ---

            return {
                "data": workouts[:limit],  # Ensure we don't return more than requested
                "total": data.get("total", len(workouts)),
                "page": data.get("page", page),
                "limit": limit,
                "has_more": page < data.get("page_count", 1)
            }
        except requests.exceptions.RequestException as e:
            print(f"Error details: {str(e)}")
            if hasattr(e.response, 'text'):
                print(f"Response body: {e.response.text}")
            raise

    async def get_all_workouts(self) -> List[Dict[str, Any]]:
        """
        Fetch all workouts by automatically handling pagination.
        
        Returns:
            List of all workout data
        """
        all_workouts = []
        page = 1
        limit = 100  # Use a larger limit to minimize API calls
        
        while True:
            response = await self.get_workouts(limit=limit, page=page)
            workouts = response.get("workouts", [])
            if not workouts:
                break
                
            all_workouts.extend(workouts)
            
            if page >= response.get("page_count", 1):
                break
                
            page += 1
            await asyncio.sleep(1)  # Rate limiting delay
            
        return all_workouts

    # --- REFACTORED: Use httpx --- 
    async def get_routines(self, limit: int = 10, page: int = 1) -> PaginatedResponse:
        """
        Fetch user's workout routines with pagination using httpx.
        Uses pageSize parameter.
        """
        page_size = min(limit, 10) # Assuming 10 is max based on other endpoints
        print(f"--- HevyAPI (httpx): Fetching routines page {page} with pageSize {page_size} ---")
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/routines",
                params={"pageSize": page_size, "page": page}
            )
            response.raise_for_status()
            data = response.json()
            
            routines = data.get("routines", [])
            page_count = data.get("page_count", 1)
            current_page = data.get("page", page)
            total_routines = page_count * page_size # Approximation
            
            return {
                "data": routines,
                "total": total_routines,
                "page": current_page,
                "limit": page_size,
                "has_more": current_page < page_count
            }
        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching routines: {e.response.status_code} - {e.response.text}")
            return {"data": [], "total": 0, "page": page, "limit": page_size, "has_more": False}
        except Exception as e:
            print(f"Error fetching routines (httpx): {str(e)}")
            traceback.print_exc()
            return {"data": [], "total": 0, "page": page, "limit": page_size, "has_more": False}

    async def get_all_routines(self) -> List[Dict[str, Any]]:
        """
        Fetch all routines by automatically handling pagination.
        
        Returns:
            List of all routine data
        """
        all_routines = []
        page = 1
        limit = 10  # Use API max limit
        
        while True:
            response = await self.get_routines(limit=limit, page=page)
            all_routines.extend(response["data"])
            
            if not response["has_more"]:
                break
                
            page += 1
            
        return all_routines

    async def get_exercises(self, limit: int = 100, page: int = 1) -> PaginatedResponse:
        """
        Fetch available exercises with pagination.
        
        Args:
            limit (int): Number of exercises to return per page (default: 100)
            page (int): Page number to fetch (default: 1)
            
        Returns:
            PaginatedResponse containing:
                - data: List of exercise data
                - total: Total number of exercises
                - page: Current page number
                - limit: Items per page
                - has_more: Whether there are more pages
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/exercises",
                headers=self.headers,
                params={"limit": limit, "page": page}
            )
            response.raise_for_status()
            data = response.json()
            
            # Standardize pagination logic
            current_page = data.get("page", page)
            page_count = data.get("page_count", 1) # Assume page_count is returned
            has_more_calculated = current_page < page_count

            return {
                "data": data.get("data", []),
                "total": data.get("total", 0), # Or estimate as page_count * limit
                "page": current_page,
                "limit": data.get("limit", limit),
                "has_more": has_more_calculated
            }
        except requests.exceptions.RequestException as e:
            print(f"Error fetching exercises: {str(e)}") # Added context to error msg
            if hasattr(e.response, 'text'):
                print(f"Response body: {e.response.text}")
            # Return empty response on error
            return {"data": [], "total": 0, "page": page, "limit": limit, "has_more": False}

    async def get_all_exercises(self) -> List[Dict[str, Any]]:
        """
        Fetch all exercises by automatically handling pagination.
        
        Returns:
            List of all exercise data
        """
        all_exercises = []
        page = 1
        limit = 100  # Use a larger limit to minimize API calls
        
        while True:
            response = await self.get_exercises(limit=limit, page=page)
            all_exercises.extend(response["data"])
            
            if not response["has_more"]:
                break
                
            page += 1
            
        return all_exercises

    async def get_workout(self, workout_id: str) -> Dict[str, Any]:
        """
        Fetch details for a specific workout.
        
        Args:
            workout_id (str): The unique identifier of the workout
            
        Returns:
            Dict containing detailed workout information
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/workouts/{workout_id}",
                headers=self.headers
            )
            response.raise_for_status()
            workout = response.json()

            # --- Add lbs Conversion ---
            if workout: # Check if workout data exists
                for exercise in workout.get("exercises", []):
                    for set_data in exercise.get("sets", []):
                        weight_kg = set_data.get("weight_kg")
                        if weight_kg is not None:
                            set_data['weight_lbs'] = weight_kg * KG_TO_LBS
                        else:
                            set_data['weight_lbs'] = None
            # --- End Conversion ---

            return workout
        except requests.exceptions.RequestException as e:
            print(f"Error details: {str(e)}")
            if hasattr(e.response, 'text'):
                print(f"Response body: {e.response.text}")
            raise
    
    async def update_workout(self, workout_id: str, workout_data: Dict) -> Dict:
        """
        Update an existing workout.
        
        Args:
            workout_id (str): The unique identifier of the workout to update
            workout_data (Dict): Updated workout data
            
        Returns:
            Dict containing the updated workout information
        """
        try:
            # Don't wrap the data if it's already wrapped
            data = workout_data if "workout" in workout_data else {"workout": workout_data}
            response = requests.put(
                f"{self.BASE_URL}/workouts/{workout_id}",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error details: {str(e)}")
            if hasattr(e.response, 'text'):
                print(f"Response body: {e.response.text}")
            raise
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make an HTTP request to the Hevy API.
        
        Args:
            method (str): HTTP method (GET, POST, PUT, DELETE)
            endpoint (str): API endpoint path
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Dict containing the API response
        """
        try:
            response = requests.request(
                method,
                f"{self.BASE_URL}{endpoint}",
                headers=self.headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error details: {str(e)}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                print(f"Response body: {e.response.text}")
            raise

    async def create_workout(self, workout_data: Dict) -> Dict:
        """Create a new workout"""
        response = await self._make_request("POST", "/workouts", json=workout_data)
        return response

    async def get_routine(self, routine_id: str) -> Dict[str, Any]:
        """
        Fetch details for a specific routine.
        
        Args:
            routine_id (str): The unique identifier of the routine
            
        Returns:
            Dict containing detailed routine information
        """
        print(f"--- HevyAPI (httpx): Fetching routine ID {routine_id} --- ")
        try:
            # --- ADDED: Log exact URL and headers before request --- 
            request_url = f"{self.BASE_URL}/routines/{routine_id}"
            print(f"--- Making GET request to: {request_url} ---")
            print(f"--- With Headers: {self.client.headers} ---")
            
            # --- UPDATED: Use async httpx client --- 
            response = await self.client.get(
                request_url # Use the logged URL
                # No headers needed here, client was initialized with them
            )
            response.raise_for_status()
            return response.json()
        # --- UPDATED: Handle httpx specific errors --- 
        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching routine {routine_id}: {e.response.status_code} - {e.response.text}")
            raise # Re-raise to be handled by caller
        except Exception as e:
            print(f"Error fetching routine {routine_id} (httpx): {str(e)}")
            traceback.print_exc()
            raise # Re-raise to be handled by caller
    
    async def create_routine(self, routine_data: Dict) -> Dict:
        """Create a new routine"""
        response = await self._make_request("POST", "/routines", json={"routine": routine_data["routine"]})
        return response

    async def update_routine(self, routine_id: str, routine_data: dict) -> dict:
        """Update a routine"""
        url = f"/routines/{routine_id}"
        print(f"Updating routine at URL: {self.BASE_URL}{url}")
        print(f"Update payload: {routine_data}")
        response = await self._make_request("PUT", url, json={"routine": routine_data["routine"]})
        print(f"Update response: {response}")
        return response

    async def get_exercise(self, exercise_id: str) -> Dict[str, Any]:
        """
        Fetch details for a specific exercise.
        
        Args:
            exercise_id (str): The unique identifier of the exercise
            
        Returns:
            Dict containing detailed exercise information
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/exercises/{exercise_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error details: {str(e)}")
            if hasattr(e.response, 'text'):
                print(f"Response body: {e.response.text}")
            raise
    
    async def search_exercises(self, query: str, limit: int = 10, page: int = 1) -> PaginatedResponse:
        """
        Search for exercises by name with pagination.
        
        Args:
            query (str): Search term to find exercises
            limit (int): Maximum number of results to return per page (default: 10)
            page (int): Page number to fetch (default: 1)
            
        Returns:
            PaginatedResponse containing:
                - data: List of matching exercise data
                - total: Total number of matches
                - page: Current page number
                - limit: Items per page
                - has_more: Whether there are more pages
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/exercises/search",
                headers=self.headers,
                params={"q": query, "limit": limit, "page": page}
            )
            response.raise_for_status()
            data = response.json()

            # Standardize pagination logic
            current_page = data.get("page", page)
            page_count = data.get("page_count", 1) # Assume page_count is returned
            has_more_calculated = current_page < page_count

            return {
                "data": data.get("data", []),
                "total": data.get("total", 0), # Or estimate
                "page": current_page,
                "limit": data.get("limit", limit),
                "has_more": has_more_calculated
            }
        except requests.exceptions.RequestException as e:
            print(f"Error searching exercises: {str(e)}") # Added context to error msg
            if hasattr(e.response, 'text'):
                print(f"Response body: {e.response.text}")
            # Return empty response on error
            return {"data": [], "total": 0, "page": page, "limit": limit, "has_more": False}

    async def search_all_exercises(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for all matching exercises by automatically handling pagination.
        
        Args:
            query (str): Search term to find exercises
            
        Returns:
            List of all matching exercise data
        """
        all_matches = []
        page = 1
        limit = 100  # Use a larger limit to minimize API calls
        
        while True:
            response = await self.search_exercises(query=query, limit=limit, page=page)
            all_matches.extend(response["data"])
            
            if not response["has_more"]:
                break
                
            page += 1
            
        return all_matches

    async def get_exercise_templates(self, limit: int = 10, page: int = 1) -> PaginatedResponse:
        """
        Fetch available exercise templates with pagination using httpx.
        Uses pageSize parameter as required by this specific endpoint.
        """
        page_size = min(limit, 10)
        print(f"--- HevyAPI (httpx): Fetching exercise templates page {page} with pageSize {page_size} ---")
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/exercise_templates",
                params={"pageSize": page_size, "page": page}
            )
            response.raise_for_status()
            data = response.json()
            
            templates = data.get("exercise_templates", [])
            page_count = data.get("page_count", 1)
            current_page = data.get("page", page)
            total_templates = page_count * page_size

            return {
                "data": templates,
                "total": total_templates, 
                "page": current_page,
                "limit": page_size,
                "has_more": current_page < page_count
            }
        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching exercise templates: {e.response.status_code} - {e.response.text}")
            return {"data": [], "total": 0, "page": page, "limit": page_size, "has_more": False}
        except Exception as e:
            print(f"Error fetching exercise templates (httpx): {str(e)}")
            traceback.print_exc() # Print traceback for unexpected errors
            return {"data": [], "total": 0, "page": page, "limit": page_size, "has_more": False}
            
    async def get_all_exercise_templates(self) -> List[Dict[str, Any]]:
        """
        Fetch all exercise templates by automatically handling pagination.
        Returns only essential fields (title, id, primary_muscle_group) to save tokens.
        
        Returns:
            List of dictionaries, each containing {'title': str, 'id': str, 'primary_muscle_group': str}
        """
        extracted_templates = [] # Changed variable name
        page = 1
        limit = 10 # Use API max page size
        print("--- HevyAPI: Fetching ALL exercise templates (extracting title/id/muscle)... ---")
        while True:
            try:
                response = await self.get_exercise_templates(limit=limit, page=page)
                page_data = response.get("data", [])
                if not page_data:
                    print(f"--- HevyAPI: No template data returned for page {page}. Stopping. ---")
                    break
                
                # Extract only necessary fields
                for template in page_data:
                    extracted_templates.append({
                        'title': template.get('title', 'Unknown'),
                        'id': template.get('id'),
                        'primary_muscle_group': template.get('primary_muscle_group')
                    })
                    
                print(f"--- HevyAPI: Fetched page {page}, total extracted templates now {len(extracted_templates)} ---")
                
                if not response.get("has_more"):
                    print("--- HevyAPI: No more pages indicated. Finished fetching templates. ---")
                    break
                    
                page += 1
                await asyncio.sleep(0.2) 
            except Exception as e:
                 print(f"Error fetching page {page} of exercise templates: {e}")
                 break 
        print(f"--- HevyAPI: Finished fetching ALL exercise templates. Total extracted: {len(extracted_templates)} ---")
        return extracted_templates # Return the list of extracted dicts

    async def get_exercise_template(self, template_id: str) -> Dict[str, Any]:
        """
        Fetch details for a specific exercise template.
        
        Args:
            template_id (str): The unique identifier of the exercise template
            
        Returns:
            Dict containing detailed exercise template information
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/exercise_templates/{template_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error details: {str(e)}")
            if hasattr(e.response, 'text'):
                print(f"Response body: {e.response.text}")
            raise

    async def get_workout_count(self) -> int:
        """Get the total number of workouts on the account."""
        try:
            response = requests.get(
                f"{self.BASE_URL}/workouts/count",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json().get("count", 0)
        except requests.exceptions.RequestException as e:
            print(f"Error details: {str(e)}")
            if hasattr(e.response, 'text'):
                print(f"Response body: {e.response.text}")
            raise

    async def get_workout_events(self, since_date: str) -> Dict:
        """Get workout events since a date"""
        response = await self._make_request("GET", "/workouts/events", params={"since": since_date})
        return response

    async def get_routine_folders(self, limit: int = 10, page: int = 1) -> PaginatedResponse:
        """
        Get a paginated list of routine folders (workout programs).
        
        Args:
            limit (int): Number of folders to return per page (default: 10)
            page (int): Page number to fetch (default: 1)
            
        Returns:
            PaginatedResponse containing:
                - data: List of routine folder data
                - total: Total number of folders
                - page: Current page number
                - limit: Items per page
                - has_more: Whether there are more pages
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/routine_folders",
                headers=self.headers,
                params={"pageSize": limit, "page": page}
            )
            response.raise_for_status()
            data = response.json()
            
            # Transform response to match our expected format
            folders = data.get("routine_folders", [])
            page_count = data.get("page_count", 1)
            current_page = data.get("page", page)
            
            return {
                "data": folders,
                "total": len(folders),
                "page": current_page,
                "limit": limit,
                "has_more": current_page < page_count
            }
        except requests.exceptions.RequestException as e:
            print(f"Error details: {str(e)}")
            if hasattr(e.response, 'text'):
                print(f"Response body: {e.response.text}")
            raise

    async def create_routine_folder(self, folder_data: Dict) -> Dict:
        """
        Create a new routine folder (workout program).
        
        Args:
            folder_data (Dict): Data for the new folder, containing:
                - routine_folder: Dict with:
                    - title: Name of the program (e.g., "PPL Split", "Upper/Lower")
                    - notes: Optional description of the program
                    
        Returns:
            Dict containing the created folder information
        """
        response = await self._make_request("POST", "/routine_folders", json=folder_data)
        return response

    async def update_routine_folder(self, folder_id: str, folder_data: Dict) -> Dict:
        """
        Update an existing routine folder (workout program).
        
        Args:
            folder_id (str): The unique identifier of the folder to update
            folder_data (Dict): Updated folder data, containing:
                - routine_folder: Dict with:
                    - title: Updated name of the program
                    - notes: Updated description of the program
                    
        Returns:
            Dict containing the updated folder information
        """
        response = await self._make_request("PUT", f"/routine_folders/{folder_id}", json=folder_data)
        return response

    async def delete_routine_folder(self, folder_id: str) -> None:
        """
        Delete a routine folder (workout program).
        
        Args:
            folder_id (str): The unique identifier of the folder to delete
        """
        try:
            response = requests.delete(
                f"{self.BASE_URL}/routine_folders/{folder_id}",
                headers=self.headers
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error details: {str(e)}")
            if hasattr(e.response, 'text'):
                print(f"Response body: {e.response.text}")
            raise

    async def get_routine_folder(self, folder_id: str) -> Dict[str, Any]:
        """
        Get a single routine folder's details (workout program).
        
        Args:
            folder_id (str): The unique identifier of the folder
            
        Returns:
            Dict containing detailed folder information including:
                - id: Folder identifier
                - title: Program name
                - notes: Program description
                - routines: List of routines in the program
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/routine_folders/{folder_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error details: {str(e)}")
            if hasattr(e.response, 'text'):
                print(f"Response body: {e.response.text}")
            raise

    async def get_routines_in_folder(self, folder_id: str) -> List[Dict[str, Any]]:
        """
        Get all routines in a specific folder (workout program).
        
        Args:
            folder_id (str): The unique identifier of the folder
            
        Returns:
            List of routines in the folder
        """
        folder = await self.get_routine_folder(folder_id)
        return folder.get("routines", [])

    # --- ADDED: Method to determine current program --- 
    async def get_current_program_details(self) -> Optional[Dict[str, Any]]:
        """
        Determines the user's current workout program based on the most recent workout.
        Fetches the program folder, the current routine, and all routines within that folder.

        Returns:
            Dict containing {'folder': folder_details, 'routines': list_of_routines_in_folder, 'current_routine': routine_details} or None if not found.
        """
        print("--- HevyAPI: Attempting to determine current program details ---")
        try:
            # 1. Get most recent workout
            workouts_response = await self.get_workouts(limit=1, page=1)
            if not workouts_response or not workouts_response.get("data"):
                print("--- HevyAPI: No recent workouts found. Cannot determine program. ---")
                return None
            recent_workout = workouts_response["data"][0]
            workout_title = recent_workout.get("title")
            print(f"--- HevyAPI: Most recent workout title: '{workout_title}' ---")
            if not workout_title:
                 print("--- HevyAPI: Recent workout has no title. Cannot match to routine. ---")
                 return None

            # 2. Find the routine matching the last workout title
            matching_routine = await self.find_routine_by_title(workout_title)
            if not matching_routine:
                print(f"--- HevyAPI: Could not find routine matching title '{workout_title}'. ---")
                return None
            folder_id = matching_routine.get("folder_id")
            print(f"--- HevyAPI: Matching routine '{matching_routine.get('title')}' found (ID: {matching_routine.get('id')}), Folder ID: {folder_id} ---")
            if not folder_id:
                print("--- HevyAPI: Matching routine is not in a folder. Cannot determine program. ---")
                return None

            # 3. Find the routine folder (program)
            matching_folder = await self.find_routine_folder_by_id(folder_id)
            if not matching_folder:
                print(f"--- HevyAPI: Could not find routine folder with ID {folder_id}. ---")
                return None
            print(f"--- HevyAPI: Matching folder (program) '{matching_folder.get('title')}' found. ---")

            # 4. Get all routines within that program folder
            program_routines = await self.get_routines_in_folder(folder_id)
            print(f"--- HevyAPI: Found {len(program_routines)} routines in folder ID {folder_id}. ---")

            return {
                "folder": matching_folder,
                "routines": program_routines,
                "current_routine": matching_routine # The routine that matched the last workout
            }

        except Exception as e:
            print(f"--- HevyAPI: Error in get_current_program_details: {e} ---")
            # Optionally re-raise or log traceback
            return None

    async def find_routine_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Helper to find a specific routine by its exact title, searching across pages."""
        page = 1
        while True:
            routines_response = await self.get_routines(page=page)
            if not routines_response or not routines_response.get("data"):
                return None # No more routines
            for routine in routines_response["data"]:
                if routine.get("title") == title:
                    return routine
            if not routines_response.get("has_more"):
                return None # Reached end without finding
            page += 1
            await asyncio.sleep(0.1) # Avoid potential rate limits

    async def find_routine_folder_by_id(self, folder_id: str) -> Optional[Dict[str, Any]]:
        """Helper to find a specific routine folder by ID, searching across pages."""
        page = 1
        while True:
            folders_response = await self.get_routine_folders(page=page)
            if not folders_response or not folders_response.get("data"):
                return None # No more folders
            for folder in folders_response["data"]:
                if folder.get("id") == folder_id:
                    return folder
            # Check pagination based on total and page size (assuming API provides page_count or similar)
            # Simple check if data is empty or assume no more pages if API doesn't give clear indication
            # For now, using a simple check - needs improvement based on actual API response structure for folders pagination
            current_page_count = len(folders_response.get("data", []))
            limit = folders_response.get("limit", 100) # Use the actual limit from response if available
            if current_page_count < limit: # Simple assumption: if less than limit fetched, it's the last page
                 return None # Reached end without finding

            page += 1
            await asyncio.sleep(0.1) # Avoid potential rate limits

    async def get_routines_in_folder(self, folder_id: str) -> List[Dict[str, Any]]:
        """Helper to get all routines belonging to a specific folder ID, handling pagination."""
        routines_in_folder = []
        page = 1
        while True:
            routines_response = await self.get_routines(page=page)
            if not routines_response or not routines_response.get("data"):
                break # No more routines
            for routine in routines_response["data"]:
                if routine.get("folder_id") == folder_id:
                    routines_in_folder.append(routine)
            if not routines_response.get("has_more"):
                break # Reached end
            page += 1
            await asyncio.sleep(0.1) # Avoid potential rate limits
        return routines_in_folder 