from typing import Dict, Any, List, Optional
import json
import os
import sys
import openai
import re # Import regex
from .hevy_api import HevyAPI

# Placeholder for getting AI response - we might centralize this later
# Ensure OPENAI_API_KEY is set in your environment variables or .env file
async def get_ai_response(prompt: str, system_prompt: str = None) -> str:
    # It's good practice to handle potential missing API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables.")
        return "Configuration Error: Missing OpenAI API Key." # Return error message

    # Use a non-async client if running in a synchronous context,
    # but since FastAPI uses async, AsyncClient is appropriate here.
    client = openai.AsyncOpenAI(api_key=api_key)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",  # Updated model to 4o-mini
            messages=messages
        )
        response_content = completion.choices[0].message.content
        # Clean up potential markdown code blocks if the model wraps the key
        response_content = response_content.strip().strip('`')
        return response_content
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        # Provide a more informative error or fallback
        return "ERROR_AI_CALL" # Indicate an error during the AI call


class IntentService:
    """
    Service for classifying user intents and gathering relevant context.
    """
    def __init__(self, hevy_api: HevyAPI):
        # Define the intents your application will handle (reflecting our discussion)
        self.intents = {
            # Information Retrieval
            "WORKOUT_INFO":         "Get information about specific workouts (e.g., 'what was my last workout?', 'details about workout X')",
            "EXERCISE_INFO":        "Get information about specific exercises (e.g., 'how to do bench press', 'what muscles does squat work?')",
            "ROUTINE_INFO":         "Get information about specific workout routines (e.g., 'details of my Upper A routine', 'show me the Lower B workout')",
            "PROGRAM_INFO":         "Get information about workout programs/folders (e.g., 'list my programs', 'what is my current program?', 'details of Upper/Lower split program')",
            "GENERAL_INFO":         "Get general fitness information or definitions (e.g., 'what is hypertrophy?', 'benefits of cardio')",

            # Analysis
            "WORKOUT_ANALYSIS":     "Analyze specific workouts or performance over time (e.g., 'analyze my last bench session', 'how is my progress on squats?')",
            "PROGRAM_ANALYSIS":     "Analyze the entire current workout program structure or effectiveness (e.g., 'analyze my program', 'is my routine balanced?')",
            "EXERCISE_ANALYSIS":    "Analyze performance or technique for a specific exercise (e.g., 'analyze my bench press form based on data', 'what was my best bench ever?')",
            "COMPARATIVE_ANALYSIS": "Compare user's performance or program against research, standards, or goals (e.g., 'how does my progress compare?', 'is my volume enough for hypertrophy based on research?')",

            # Modifications / Actions
            "EXERCISE_SWAP":        "Request to replace specific exercises in a routine (e.g., 'swap leg press for squats', 'find alternative for exercise X')",
            "PROGRAM_CREATE":       "Request to create a new workout program (e.g., 'create a 3-day split for me', 'build a beginner program')",
            "ROUTINE_UPDATE":       "Request to update or modify an existing routine (e.g., 'add another set to bench press', 'change rest times', 'remove exercise Y')",
            "SUGGESTION_IMPLEMENT": "User confirms or agrees to implement a specific change previously suggested by the AI, often following a question or list of options provided by the AI (e.g., 'ok, apply that change', 'yes, update my routine with that suggestion', 'Use option B', 'Let's go with Skullcrushers', 'Ok do it')",

            # Fallback / Meta
            "UNKNOWN":              "The user's intent is unclear, ambiguous, or not related to the app's fitness capabilities.",
            "GREETING":             "The user is simply greeting, making small talk, or saying goodbye."
        }
        # Store the injected HevyAPI instance
        self.hevy_api = hevy_api

    # --- ADDED: Helper to extract exercise name --- 
    def _extract_exercise_name(self, message: str) -> Optional[str]:
        """Extraction of exercise name following swap-related keywords, handling trailing punctuation."""
        keywords = [
            "swap", 
            "alternative for", 
            "alternatives for", 
            "replace", 
            "instead of"
        ]
        
        exercise_name = None
        
        for keyword in keywords:
            # Use regex to find the keyword and capture the text after it
            # (?i) makes it case-insensitive
            # Capture group ([\w\s\(\)-]+?) is non-greedy to stop at the first punctuation/end
            pattern = rf"(?i)\b{keyword}\s+([\w\s\(\)-]+?)(?:[\.\?!\"\']|\Z)" 
            match = re.search(pattern, message)
            
            if match:
                potential_name = match.group(1).strip()
                # Basic validation
                if 0 < len(potential_name) < 100:
                    exercise_name = potential_name
                    break # Stop after first match
                    
        if exercise_name:
            print(f"--- _extract_exercise_name: Found potential name: '{exercise_name}' ---")
        else:
            print(f"--- _extract_exercise_name: Could not reliably extract name from '{message}' ---")
            
        return exercise_name

    # --- ADDED: Helper to extract routine name --- 
    def _extract_routine_name(self, message: str) -> Optional[str]:
        """Attempts to extract a routine name, often following 'in the' or 'from my'."""
        message_lower = message.lower()
        # --- UPDATED REGEX v5: Removed routine/workout/program from stop list --- 
        # Looks for keywords, optional 'the'/'my', captures subsequent words greedily.
        # Stops capturing *before* common follow-up verbs/prepositions or punctuation.
        match = re.search(r"(?:in|from)\s+(?:the|my)?\s+([\w\s\(\)-]+)\s*(?:\bfor\b|\bcan\b|,|\?|!|$)", message_lower)
        
        routine_name = None
        if match:
            # Extract the captured group (the potential name)
            potential_name = match.group(1).strip()
            # Capitalize appropriately (simple title case)
            # Avoid title casing if it looks like an acronym (e.g., PPL)
            if not potential_name.isupper() or len(potential_name) < 2:
                routine_name = potential_name.title() 
            else:
                 routine_name = potential_name # Keep PPL as PPL
            print(f"--- _extract_routine_name: Found potential name: '{routine_name}' ---")
        else:
            print(f"--- _extract_routine_name: Could not reliably extract name from '{message}' ---")
            
        return routine_name

    async def classify_intent(self, message: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """
        Classify the user's intent based on their message using an AI model,
        optionally considering the last assistant message for context.
        """
        print(f"--- Classifying Intent for: '{message}' ---")

        # --- ADDED: Strip potential surrounding quotes from message --- 
        message_content = message.strip().strip('"').strip("'")
        print(f"--- Stripped message content for prompt: '{message_content}' ---")

        # --- ADDED: Get last assistant message --- 
        last_assistant_message = None
        if conversation_history and len(conversation_history) > 0:
            # Iterate backwards to find the last assistant message
            for i in range(len(conversation_history) - 1, -1, -1):
                if conversation_history[i].get('role') == 'assistant':
                    last_assistant_message = conversation_history[i].get('content')
                    # Limit length to avoid excessive prompt size
                    if last_assistant_message and len(last_assistant_message) > 500:
                         last_assistant_message = last_assistant_message[:500] + "..."
                    print("--- Including last assistant message (truncated) in classification prompt context. ---")
                    break
        
        # --- Conditionally construct the prompt --- 
        prompt_parts = [
            "Analyze the user message below and determine its primary intent. Choose EXACTLY ONE intent key from the list provided.",
            "\nAvailable Intents:",
            "```json",
            json.dumps(self.intents, indent=2),
            "```"
        ]
        
        # --- ONLY add history section if it exists --- 
        if last_assistant_message:
            prompt_parts.extend([
                "\nPrevious Assistant Message (if relevant):",
                '"""',
                last_assistant_message,
                '"""'
            ])
            # --- MORE EXPLICIT INSTRUCTION FOR CONFIRMATIONS --- 
            instruction = "IMPORTANT: The previous assistant message likely presented options or asked a question. Analyze the User Message below. " \
                          "If it directly answers the question, selects an option (e.g., \'Use Box Jump\', \'Go with the second one\', \'Select Assisted Pistol Squats\'), " \
                          "or clearly confirms a previously suggested action (e.g., \'Ok do it\', \'Yes please apply that\'), " \
                          "then the intent MUST be `SUGGESTION_IMPLEMENT`. " \
                          "Otherwise, analyze the user message based on the other intent definitions. " \
                          "Output ONLY the single most appropriate Intent Key."
        else:
            instruction = "Based *only* on the user message and the intent definitions, output the single most appropriate Intent Key (e.g., `WORKOUT_INFO`, `PROGRAM_ANALYSIS`, `PROGRAM_INFO`). Do not add any explanation or surrounding text."
        
        prompt_parts.extend([
            "\nUser Message:",
            message_content, # Use stripped version here
            "\n\nInstructions:", # Added header for clarity
            instruction,
            "\n\nIntent Key:"
        ])
        
        prompt = "\n".join(prompt_parts)

        system_prompt = "You are an expert system designed to classify user requests related to a fitness tracking and analysis application. Your goal is to accurately identify the user's primary goal from the provided list of intents, considering the immediate conversational context if provided."
        
        # --- Make the AI call --- 
        intent_key_response = await get_ai_response(prompt, system_prompt)
        print(f"--- Raw AI classification response: '{intent_key_response}' ---") # Log raw response

        # --- Clean and validate the response --- 
        # Attempt to extract a valid intent key even if the response is noisy
        cleaned_intent_key = "UNKNOWN" # Default to UNKNOWN
        for valid_key in self.intents.keys():
            # Use regex to find the key as a whole word, potentially surrounded by quotes/spaces
            # pattern = rf'(?:\"|\'|\s|^){re.escape(valid_key)}(?:\"|\'|\s|$)'
            # Simpler check: find the key as a substring, possibly quoted
            if f'"{valid_key}"' in intent_key_response or f"'{valid_key}'" in intent_key_response or valid_key == intent_key_response.strip():
                 cleaned_intent_key = valid_key
                 print(f"--- Extracted valid key '{valid_key}' from AI response. ---")
                 break # Found a valid key
            # Fallback: Check if the key exists as a word (less precise)
            elif re.search(rf'\b{re.escape(valid_key)}\b', intent_key_response):
                cleaned_intent_key = valid_key
                print(f"--- Extracted valid key '{valid_key}' (substring match) from AI response. ---")
                # Don't break here, prefer exact/quoted match if found later

        # Now check the extracted/default key
        if cleaned_intent_key != "UNKNOWN":
            print(f"--- Classified Intent: {cleaned_intent_key} ---")
            return cleaned_intent_key
        # Handle specific error code from get_ai_response if extraction failed
        elif intent_key_response == "ERROR_AI_CALL": 
             print(f"--- Intent Classification Failed (AI Error) ---")
             return "UNKNOWN" 
        else:
            # Log the original unexpected response if no valid key was extracted
            print(f"--- Warning: Could not extract valid intent key from AI response '{intent_key_response}'. Falling back to UNKNOWN. ---")
            return "UNKNOWN"

    async def get_relevant_context(self, intent: str, message: str) -> Dict[str, Any]:
        """
        Fetches relevant context data based on the classified intent by calling HevyAPI.
        """
        print(f"--- Getting Context for Intent: {intent} ---")
        context = {}
        hevy_api = self.hevy_api # Use the injected instance

        # --- ADDED: Handle context specifically for SUGGESTION_IMPLEMENT --- 
        if intent == "SUGGESTION_IMPLEMENT":
            print("--- Context for SUGGESTION_IMPLEMENT: Extracting chosen item... ---")
            # We need to extract the chosen exercise name from the *current* message.
            # This is tricky. Let's try a simple approach: look for capitalized words 
            # or words matching known exercise templates AFTER keywords like 'use', 'with', 'go with'.
            # THIS IS A PLACEHOLDER - Needs more robust logic or reliance on frontend passing context.
            chosen_match = re.search(r"(?:use|with|go with|choose|select)\s+([\w\s\(\)-]+)", message, re.IGNORECASE)
            if chosen_match:
                context['chosen_alternative_title'] = chosen_match.group(1).strip()
                print(f"--- Extracted potential chosen alternative: '{context['chosen_alternative_title']}' ---")
            else:
                 print("--- WARNING: Could not extract chosen alternative from message for SUGGESTION_IMPLEMENT. Handler will need fallback/clarification. ---")
            # NOTE: routine_id and exercise_to_swap_title MUST be passed via external context/state management.
            # We *cannot* reliably get them just from the message here.
            # The AIWorkoutOptimizer will check context for these.
            return context # Return immediately after extracting choice

        # --- Existing Context Logic --- 
        try:
            # --- Information Retrieval Context ---
            if intent == "WORKOUT_INFO":
                # Fetch last workout for specific keywords, otherwise maybe recent few?
                if "last workout" in message.lower() or "most recent" in message.lower() or "yesterday" in message.lower(): # Simple keyword check
                    print("--- Fetching last workout (limit 1) for WORKOUT_INFO ---")
                    workouts_response = await hevy_api.get_workouts(limit=1, page=1)
                    if workouts_response and workouts_response.get("data"):
                        context['last_workout'] = workouts_response["data"][0]
                        print(f"--- Found last workout: {context['last_workout'].get('title', 'Unknown')} ---")
                else:
                    # Fetch a few recent workouts for general workout info questions
                    print("--- Fetching recent workouts (limit 5) for WORKOUT_INFO ---")
                    workouts_response = await hevy_api.get_workouts(limit=5, page=1)
                    if workouts_response and workouts_response.get("data"):
                        context['recent_workouts'] = workouts_response["data"]
                        print(f"--- Found {len(context['recent_workouts'])} recent workouts ---")
                # TODO: Add logic to parse specific dates/IDs/titles from message

            elif intent == "ROUTINE_INFO":
                 # --- Reverted to simple fallback due to persistent syntax errors in name extraction ---
                 print(f"--- Fetching all routine titles (fallback) for ROUTINE_INFO from message: '{message}' ---")
                 # Fallback: Fetching all routine titles as placeholder
                 all_routines = await hevy_api.get_all_routines()
                 context['all_routines'] = all_routines
                 # --- UPDATED: Try to fetch SPECIFIC routine first ---
                 print(f"--- Attempting to fetch specific routine for ROUTINE_INFO from message: '{message}' ---")
                 # --- COMMENTED OUT name extraction due to syntax issues ---
                 # extracted_name = self._extract_routine_name(message)
                 extracted_name = None # Default to None for now
                 specific_routine = None
                 # if extracted_name:
                 #     print(f"--- Extracted potential routine name: '{extracted_name}' ---")
                 #     specific_routine = await hevy_api.find_routine_by_title(extracted_name)

                 if specific_routine: # This block will currently not be entered
                     context['specific_routine_details'] = specific_routine
                     print(f"--- Found specific routine details for: '{extracted_name}' ---")
                 else:
                     # Fallback: Fetching all routine titles as placeholder
                     print(f"--- Could not find specific routine '{extracted_name}' (or no name extracted). Fetching all routine titles as fallback. ---")
                     all_routines = await hevy_api.get_all_routines()
                     context['all_routines'] = all_routines
                     print(f"--- Found {len(context['all_routines'])} total routines (fallback context) ---")

            elif intent == "EXERCISE_INFO":
                 print("--- Fetching all exercise templates for EXERCISE_INFO ---")
                 # Fetching templates might be better than user's logged exercises for general info
                 all_templates = await hevy_api.get_all_exercise_templates()
                 context['all_exercise_templates'] = all_templates
                 print(f"--- Found {len(context['all_exercise_templates'])} exercise templates ---")
                 # TODO: Parse specific exercise name from message, fetch its details, maybe fetch user's history for *that* exercise.

            # --- Analysis Context ---
            elif intent == "PROGRAM_ANALYSIS":
                print("--- Fetching current program details & exercise templates for PROGRAM_ANALYSIS ---")
                # Fetch program details
                current_program = await hevy_api.get_current_program_details()
                if current_program:
                    context['current_program_folder'] = current_program.get('folder')
                    context['current_program_routines'] = current_program.get('routines')
                    print(f"--- Found current program: {context['current_program_folder'].get('title', 'Unknown')} with {len(context.get('current_program_routines', []))} routines for analysis ---")
                else:
                    print("--- Could not determine current program for PROGRAM_ANALYSIS ---")
                
                # --- REMOVED: Templates should be loaded on startup and accessed by AIWorkoutOptimizer --- 
                # Fetch exercise templates
                # all_templates = await hevy_api.get_all_exercise_templates()
                # context['all_exercise_templates'] = all_templates
                # print(f"--- Found {len(context['all_exercise_templates'])} exercise templates for analysis context ---")

            elif intent == "WORKOUT_ANALYSIS" or intent == "EXERCISE_ANALYSIS" or intent == "COMPARATIVE_ANALYSIS":
                print(f"--- Fetching recent workouts (limit 30) for Analysis Intent: {intent} ---")
                # Need a decent number of workouts for trend analysis
                workouts_response = await hevy_api.get_workouts(limit=30, page=1) # Fetch more for analysis
                if workouts_response and workouts_response.get("data"):
                    context['recent_workouts'] = workouts_response["data"]
                    print(f"--- Found {len(context['recent_workouts'])} recent workouts for analysis ---")
                # TODO: Parse specific exercise name for EXERCISE_ANALYSIS/COMPARATIVE_ANALYSIS

            # --- Modification Context ---
            elif intent == "EXERCISE_SWAP" or intent == "ROUTINE_UPDATE":
                print(f"--- Fetching routines/folders/exercises for Modification Intent: {intent} ---")
                
                # Extract common entities needed for modifications
                extracted_exercise = self._extract_exercise_name(message)
                if extracted_exercise:
                    context['exercise_name'] = extracted_exercise
                
                extracted_routine_name = self._extract_routine_name(message)
                if extracted_routine_name:
                    # Try to find the specific routine by its extracted name
                    print(f"--- Searching for routine title: '{extracted_routine_name}' ---")
                    target_routine = await hevy_api.find_routine_by_title(extracted_routine_name)
                    if target_routine:
                        context['target_routine_details'] = target_routine
                        print(f"--- Found specific routine details for '{extracted_routine_name}' (ID: {target_routine.get('id')}) ---")
                    else:
                        print(f"--- Could not find specific routine named '{extracted_routine_name}' by title. ---")
                
                # Fetch all routines (useful for context or updates)
                all_routines = await hevy_api.get_all_routines()
                context['all_routines'] = all_routines
                
                # --- Fetch folders, respecting API limit --- 
                try:
                    folders_response = await hevy_api.get_routine_folders(limit=10) # CORRECTED: Use 'limit' parameter
                    context['routine_folders'] = folders_response.get("data", [])
                except Exception as folder_err:
                    print(f"!!! Error fetching routine folders: {folder_err} !!!")

                # Fetch exercise templates only if needed (e.g., for swapping)
                if intent == "EXERCISE_SWAP":
                    # Templates should be loaded on startup & cached in AIWorkoutOptimizer
                    # Accessing cache directly here might be complex, rely on AIWorkoutOptimizer having it
                    # For now, let's ensure we log if templates are missing later if needed
                    # If we NEED the list here for context, uncomment:
                    # all_templates = await hevy_api.get_all_exercise_templates()
                    # context['all_exercise_templates'] = all_templates
                    pass # Assume AI Opt has access to cached templates
                
                print(f"--- Found {len(context.get('all_routines',[]))} routines, {len(context.get('routine_folders',[]))} folders for modification context ---")
                # TODO: Identify specific routine/exercise to modify from message/history

            elif intent == "PROGRAM_CREATE":
                print(f"--- Fetching exercises for Program Creation ---")
                # Need exercise list to build a program
                all_templates = await hevy_api.get_all_exercise_templates()
                context['all_exercise_templates'] = all_templates
                print(f"--- Found {len(context['all_exercise_templates'])} exercise templates for creation ---")

            elif intent == "SUGGESTION_IMPLEMENT":
                print("--- Context for SUGGESTION_IMPLEMENT relies on conversation history (Not fetched here) ---")
                # The AI handler will need to look back in the conversation history
                pass

            # --- ADDED: Handling for PROGRAM_INFO intent ---
            elif intent == "PROGRAM_INFO":
                if "current" in message.lower() or "active" in message.lower() or "what is my program" in message.lower():
                    print("--- Fetching current program details for PROGRAM_INFO ---")
                    current_program = await hevy_api.get_current_program_details()
                    if current_program:
                        context['current_program_folder'] = current_program.get('folder')
                        context['current_program_routines'] = current_program.get('routines')
                        print(f"--- Found current program: {context['current_program_folder'].get('title', 'Unknown')} with {len(context.get('current_program_routines', []))} routines ---")
                    else:
                        print("--- Could not determine current program for PROGRAM_INFO ---")
                else:
                    # General request for all programs/folders
                    print("--- Fetching all routine folders for PROGRAM_INFO ---")
                    folders_response = await hevy_api.get_routine_folders(limit=10) # Use API max limit
                    context['routine_folders'] = folders_response.get("data", [])
                    print(f"--- Found {len(context['routine_folders'])} routine folders ---")

            # GENERAL_INFO, GREETING, UNKNOWN usually don't need Hevy context

        except Exception as e:
            print(f"!!! Error getting context for intent {intent}: {e} !!!")
            # import traceback # Uncomment for detailed debugging if needed
            # traceback.print_exc()

        print(f"--- Returning Context Keys: {list(context.keys())} ---")
        return context

    # --- REMOVED _extract_routine_name method due to persistent syntax/reference errors ---
    # def _extract_routine_name(self, message: str) -> Optional[str]:
    #     """Simple helper to extract a potential routine name from a message."""
    #     # ... (method content removed) ...
    #     return None