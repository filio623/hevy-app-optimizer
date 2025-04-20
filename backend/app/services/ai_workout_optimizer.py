from typing import Dict, List, Any, Optional, ClassVar
from datetime import datetime, timedelta
from .workout_optimizer import WorkoutOptimizer
from .hevy_api import HevyAPI
import openai
import os
import json
import re # Ensure re is imported if needed for goal extraction
from serpapi import GoogleSearch # Import SerpApi client
import traceback
import asyncio # Import asyncio

class AIWorkoutOptimizer:
    """
    Enhanced workout optimizer that combines data analysis with AI capabilities
    to provide personalized workout recommendations and insights.
    """
    
    # --- ADDED: Class variable for caching ---
    _cached_templates: ClassVar[Optional[List[Dict]]] = None

    def __init__(self, hevy_api: HevyAPI):
        """
        Initialize the AI Workout Optimizer.
        
        Args:
            hevy_api: Instance of HevyAPI for workout data
        """
        self.workout_optimizer = WorkoutOptimizer(hevy_api)
        self.hevy_api = hevy_api
        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conversation_history = []
        # --- ADDED: State for pending exercise swap --- 
        self.pending_swap_context: Optional[Dict[str, Any]] = None 
        
    # --- ADDED: Static method to load cache ---
    @staticmethod
    async def load_templates_cache(hevy_api: HevyAPI):
        """Fetches all exercise templates and stores them in the class cache."""
        if AIWorkoutOptimizer._cached_templates is None:
            print("--- AIWorkoutOptimizer: Loading exercise templates into cache... ---")
            try:
                # Use the get_all_exercise_templates method which already extracts necessary fields
                AIWorkoutOptimizer._cached_templates = await hevy_api.get_all_exercise_templates()
                print(f"--- AIWorkoutOptimizer: Successfully loaded {len(AIWorkoutOptimizer._cached_templates)} templates into cache. ---")
            except Exception as e:
                print(f"--- AIWorkoutOptimizer: ERROR loading exercise template cache: {e} ---")
                traceback.print_exc() # Print traceback for cache loading errors
                AIWorkoutOptimizer._cached_templates = [] # Set empty list on error
        else:
            print("--- AIWorkoutOptimizer: Exercise template cache already loaded. ---")
        
    async def get_chat_response(self, message: str, system_prompt: Optional[str] = None) -> str:
        """
        Get a response from the AI chat model.
        
        Args:
            message: The user's message
            system_prompt: Optional system prompt to guide the AI's response
            
        Returns:
            The AI's response
        """
        messages = []
        
        # Define the NEW comprehensive Markdown formatting instructions
        markdown_instructions = """
        **General Formatting Guidelines:**
        Your primary goal is to present information clearly, readably, and logically using standard Markdown.

        **Structure & Hierarchy:**
        *   Use headings (#, ##, ###) appropriately to structure long responses and show hierarchy. Choose heading levels that make sense for the content.
        *   Use **bold** (`**text**`) for emphasis on key terms, titles within paragraphs, or labels (e.g., `**Workout:** Upper A`).
        *   Use paragraphs for descriptive text. Ensure adequate spacing between paragraphs (one blank line in Markdown).

        **Lists:**
        *   Use bullet points (`* ` or `- `) for unordered lists (e.g., listing exercises, sets, recommendations).
        *   Use numbered lists (`1. `) for sequential steps or ordered items.
        *   Indent nested lists appropriately.

        **Workout Data Specifics:**
        *   When displaying details of one or more workouts:
            *   Clearly indicate the workout title and date (e.g., using a heading or bold text).
            *   List exercises clearly (e.g., using bold or a sub-heading).
            *   List sets under each exercise, typically using bullet points (`* Set: [Weight] x [Reps]`).
        *   When displaying program/routine structure:
            *   Clearly indicate program/folder names and the routines within them, possibly using nested lists or headings.

        **Readability:**
        *   **Spacing is crucial!** Add blank lines (press Enter twice in Markdown) between distinct sections, headings, paragraphs, lists, and exercises to improve readability. Avoid large blocks of text packed together.
        *   Use code blocks (```) for code examples or structured data snippets if appropriate.
        *   Use blockquotes (>) for important notes or warnings.

        **Overall:** Apply these rules thoughtfully to make the information easy to scan and understand, regardless of whether you are presenting workout data, analysis, general information, or step-by-step instructions. Adapt the specific elements (headings, lists, bolding) to best suit the content being presented in each response.
        """
        
        # Add system prompt if provided, and always append Markdown instructions
        if system_prompt:
            system_content = f"{system_prompt}\n\n{markdown_instructions}"
            messages.append({
                "role": "system", 
                "content": system_content
            })
        else:
            # Default system prompt with Markdown formatting
            system_content = f"""
            You are a fitness expert AI assistant. {markdown_instructions}
            """
            messages.append({
                "role": "system", 
                "content": system_content
            })
        
        # Add conversation history
        messages.extend(self.conversation_history)
        
        # Add current message
        messages.append({"role": "user", "content": message})

        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            # Extract the response text
            response_text = response.choices[0].message.content
 
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": response_text})
            
            return response_text
            
        except Exception as e:
            print(f"Error getting OpenAI response: {str(e)}")
            raise
            
    def clear_conversation_history(self):
        """Clear the conversation history"""
        self.conversation_history = []
        
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the current conversation history"""
        return self.conversation_history.copy()
    
    async def get_ai_optimization_insights(self, days: int = 30) -> Dict[str, Any]:
        """
        Get AI-enhanced workout optimization insights.
        
        Args:
            days: Number of days of workout history to analyze
            
        Returns:
            Dict containing AI-enhanced insights and recommendations
        """
        # Get basic workout analysis
        workout_analysis = await self.workout_optimizer.analyze_workout_history(days)
        
        # Prepare context for AI analysis
        context = self._prepare_ai_context(workout_analysis)
        
        # Get AI-enhanced insights
        ai_insights = await self._get_ai_insights(context)
        
        return {
            "workout_analysis": workout_analysis,
            "ai_insights": ai_insights,
            "recommendations": ai_insights.get("recommendations", []),
            "exercise_insights": ai_insights.get("exercise_insights", {}),
            "summary": ai_insights.get("summary", "")
        }
    
    def _prepare_ai_context(self, workout_analysis: Dict[str, Any]) -> str:
        """
        Prepare workout analysis data as context for AI.
        
        Args:
            workout_analysis: Basic workout analysis data
            
        Returns:
            Formatted context string for AI analysis
        """
        context = f"""
        Workout Analysis Summary:
        - Total workouts analyzed: {workout_analysis['total_workouts']}
        - Time period: Last {workout_analysis.get('days', 30)} days
        
        Exercise Analysis:
        """
        
        for exercise_id, data in workout_analysis.get("exercise_analysis", {}).items():
            context += f"""
            Exercise: {data['name']}
            - Frequency: {data['frequency']} times
            - Average weight: {data.get('average_weight', 'N/A')} kg
            - Average reps: {data.get('average_reps', 'N/A')}
            - Progression trend: {data['progression']}
            """
        
        return context
    
    async def _get_ai_insights(self, context: str) -> Dict[str, Any]:
        """
        Get AI-enhanced insights based on workout analysis.
        
        Args:
            context: Formatted workout analysis context
            
        Returns:
            Dict containing AI-generated insights
        """
        # Prepare the prompt for the AI
        prompt = f"""
        Based on the following workout analysis, provide detailed insights and recommendations:
        
        {context}
        
        Please provide:
        1. A summary of the workout patterns and trends
        2. Specific exercise recommendations for improvement
        3. Overall workout optimization suggestions
        4. Areas of concern or potential injury risks
        5. Suggestions for workout variety and progression
        
        Format the response as a structured analysis with clear sections.
        """
        
        # Get AI response - no need to pass system prompt as Markdown formatting is handled in get_chat_response
        response = await self.get_chat_response(prompt)
        
        # Parse and structure the AI response
        return self._parse_ai_response(response)
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the AI response into structured data.
        
        Args:
            response: Raw AI response text
            
        Returns:
            Structured dictionary of insights
        """
        # TODO: Implement more sophisticated parsing of AI response
        # For now, return a basic structure
        return {
            "summary": response[:200] + "...",  # First 200 chars as summary
            "recommendations": [line.strip() for line in response.split('\n') if line.strip()],
            "exercise_insights": {},  # TODO: Parse exercise-specific insights
            "raw_response": response
        }
    
    async def get_info_response(self, message: str, intent: str, context: Dict[str, Any]) -> str:
        """
        Handles intents related to information retrieval using provided context.
        Pre-formats workout details for better presentation.
        """
        print(f"--- AI Optimizer: Handling Info Intent '{intent}' ---")
        prompt_context = "No specific context was readily available." # Default

        # --- Format Context String with Spacing and Indentation ---
        if intent == "WORKOUT_INFO":
            workout_list_to_format = []
            if 'last_workout' in context:
                workout_list_to_format = [context['last_workout']]
                print("--- Formatting single last workout for prompt context ---")
            elif 'recent_workouts' in context:
                # Take up to 3 recent workouts
                workout_list_to_format = context['recent_workouts'][:3]
                print(f"--- Formatting {len(workout_list_to_format)} recent workouts for prompt context ---")

            if workout_list_to_format:
                formatted_workouts = []
                for workout in workout_list_to_format:
                    workout_str = f"**Workout:** {workout.get('title', 'Unknown')}\n"
                    # Extract just the date part
                    date_str = workout.get('start_time', 'Unknown Date')
                    if date_str and 'T' in date_str:
                         date_str = date_str.split('T')[0]
                    workout_str += f"**Date:** {date_str}\n\n" # Added double newline after date

                    exercise_strs = []
                    for exercise in workout.get('exercises', []):
                        exercise_str = f"  **{exercise.get('title', 'Unknown Exercise')}**\n" # Indent + Bold
                        set_strs = []
                        for i, set_data in enumerate(exercise.get('sets', [])):
                            weight_lbs = set_data.get('weight_lbs')
                            reps = set_data.get('reps')
                            reps_str = f"{reps} reps" if reps is not None else "N/A reps"
                            weight_str = "Bodyweight"
                            if weight_lbs is not None and weight_lbs > 0: # Only show lbs if weight exists
                                weight_str = f"{weight_lbs:.1f} lbs"
                            # Further indent sets with a bullet point
                            set_strs.append(f"    * Set {i+1}: {weight_str} x {reps_str}")
                        exercise_str += "\n".join(set_strs)
                        exercise_strs.append(exercise_str)
                    # Join exercises with double newline for spacing
                    workout_str += "\n\n".join(exercise_strs)
                    formatted_workouts.append(workout_str)
                # Join multiple workouts with triple newline for clear separation
                prompt_context = "\n\n\n".join(formatted_workouts)
                print("--- Added pre-formatted workout details to prompt context ---") # Updated log

        # --- UPDATED: Handle ROUTINE_INFO context (Limited Formatting) ---
        elif intent == "ROUTINE_INFO":
             if 'all_routines' in context:
                 routines = context['all_routines']
                 if routines:
                    # Just list titles to avoid excessive tokens for now
                    routine_list = "\n".join([f"- {routine.get('title', 'Unnamed Routine')}" for routine in routines])
                    prompt_context = f"Context contains the following routines (details require specific parsing not yet implemented):\n{routine_list}"
                 else:
                    prompt_context = "No routines found in the context."
                 print("--- Added routine title list (placeholder) to prompt context ---")
             else:
                 prompt_context = "Workout routine data was not found in context."

        # --- ADDED: Handle PROGRAM_INFO intent --- 
        elif intent == "PROGRAM_INFO":
            if 'routine_folders' in context:
                folders = context['routine_folders']
                if folders:
                    folder_list = "\n".join([f"- {folder.get('title', 'Unnamed Folder')} (ID: {folder.get('id')})" for folder in folders])
                    prompt_context = f"Here are your workout programs (folders):\n{folder_list}"
                else:
                    prompt_context = "You don't seem to have any workout programs (folders) set up yet."
                print("--- Added routine folder list to prompt context ---")
            elif 'current_program_folder' in context and 'current_program_routines' in context:
                folder = context['current_program_folder']
                routines = context['current_program_routines']
                folder_title = folder.get('title', 'Unnamed Program')
                routine_list = "\n".join([f"  - {routine.get('title', 'Unnamed Routine')}" for routine in routines])
                prompt_context = f"Your current program seems to be **{folder_title}**. It includes the following routines:\n{routine_list}"
                print("--- Added current program details to prompt context ---")
            else:
                prompt_context = "Could not find specific program information."

        elif intent == "EXERCISE_INFO":
             if 'all_exercise_templates' in context:
                  try:
                      prompt_context = f"Available Exercise Templates (JSON sample):\n```json\n{json.dumps(context['all_exercise_templates'][:10], indent=2)}\n```"
                  except Exception:
                      prompt_context = "Could not format exercise template data."
                  print(f"--- Added exercise templates JSON to prompt context ---")
             else:
                  prompt_context = "Exercise template information was not found."

        elif intent == "GENERAL_INFO":
             print("--- No specific Hevy context needed for GENERAL_INFO ---")
             prompt_context = "The user is asking a general fitness question."

        # --- Updated Prompt Instructions ---
        prompt = f"""Here is relevant context information:
--- CONTEXT START ---
{prompt_context}
--- CONTEXT END ---

User's Question (Intent: {intent}):
'{message}'

Instructions:
Answer the user's question based primarily on the provided context.
- If the context contains pre-formatted workout details (usually for WORKOUT_INFO intent), present that information clearly to the user. You can add a brief introductory sentence (like "Here are the details for your last workout:"), but **strictly preserve the structure, spacing, indentation, and bolding** as provided in the context. Do not reformat it using standard Markdown lists if it's already formatted.
- If the context contains JSON data (e.g., exercise templates), extract the relevant information to answer the question and format your answer using general Markdown guidelines (headings, lists, bolding, spacing).
- If the context contains a list of program folders or details about the current program (usually for PROGRAM_INFO intent), present that information clearly using Markdown lists and bolding.
- If the context contains a list of routine titles (usually for ROUTINE_INFO placeholder), use that list to answer the question about routines.
- If the question is general (like 'What is hypertrophy?'), answer it based on your general knowledge using standard Markdown formatting.
- If the necessary information isn't in the context, state that clearly.
"""

        # Send prompt to AI
        response = await self.get_chat_response(prompt)
        return response

    async def get_analysis_response(self, message: str, intent: str, context: Dict[str, Any]) -> str:
        """
        Handles intents related to analysis.
        """
        print(f"--- AI Optimizer: Handling Analysis Intent '{intent}' ---")
        prompt = ""
        response_content = "" # Initialize response

        if intent == "PROGRAM_ANALYSIS":
            print("--- AI Optimizer: Handling PROGRAM_ANALYSIS ---")
            program_analysis_results = context.get("program_analysis_results", {})
            if program_analysis_results:
                 # If analysis was already in context (future improvement)
                 program_name = program_analysis_results.get('program_name', 'Unknown Program')
                 analysis_summary = program_analysis_results.get('analysis', 'No analysis available')
                 prompt = f"""Context about the user's complete workout program:
Program Name: {program_name}
Program Analysis Summary:
{analysis_summary}
User's question regarding the program: {message}
Please provide a detailed, personalized response that addresses the user's question using the provided program analysis."""
                 response_content = await self.get_chat_response(prompt) # Ask AI to use existing analysis

            else:
                 # If no pre-computed analysis, try to generate it now
                 print("--- No pre-computed program analysis found, attempting to analyze now ---")
                 try:
                     analysis_data = await self.analyze_program(message) # Calls the existing method
                     if analysis_data and "error" not in analysis_data:
                          # --- CHANGE APPLIED HERE: Return analysis directly ---
                          analysis_summary = analysis_data.get('analysis', 'No analysis available')
                          print("--- Successfully generated analysis, returning directly. ---")
                          # We can potentially prepend the program name for clarity
                          program_name = analysis_data.get('program_name', 'Unknown Program')
                          response_content = f"# Analysis for: {program_name}\\n\\n{analysis_summary}"
                          # --- No second AI call needed here ---
                     else:
                          error_msg = analysis_data.get("error", "Unknown error during analysis")
                          print(f"--- Error generating program analysis on the fly: {error_msg} ---")
                          # Inform user about the error
                          response_content = f"I tried to analyze the program but encountered an error: {error_msg}."
                 except Exception as e:
                     print(f"--- Exception during on-the-fly program analysis: {e} ---")
                     # Inform user about the internal error
                     response_content = "I encountered an internal error while trying to analyze the program. Please try again later."

        else:
            # Handle other analysis intents (WORKOUT_ANALYSIS, EXERCISE_ANALYSIS, etc.)
            # These will likely still need an AI call based on context
            prompt = f"User asked for analysis (Intent: {intent}): '{message}'. Context: {str(context)}. Perform the requested analysis."
            response_content = await self.get_chat_response(prompt)

        # Return the determined response content
        return response_content

    async def get_modification_response(self, message: str, intent: str, context: Dict[str, Any]) -> str:
        """
        Handles intents related to modifications and actions.
        """
        print(f"--- AI Optimizer: Handling Modification Intent '{intent}' ---")
        # TODO: Implement logic for different modification intents
        # For EXERCISE_SWAP, PROGRAM_CREATE, ROUTINE_UPDATE:
        #   - Prepare prompt for AI to confirm or plan the change
        #   - Potentially call HevyAPI methods to *perform* the change after AI confirmation
        # For SUGGESTION_IMPLEMENT:
        #   - Retrieve previous suggestion from conversation history or context
        #   - Call HevyAPI to implement the change
        
        if intent == "EXERCISE_SWAP":
            print("--- Handling EXERCISE_SWAP intent ---")
            # --- Retrieve context --- 
            exercise_to_swap_name = context.get("exercise_name")
            target_routine = context.get("target_routine_details") # Contains ID, title, exercises list etc.
            routine_name = target_routine.get("title", "the routine") if target_routine else "the routine"

            if not exercise_to_swap_name:
                 # Handle case where exercise name wasn't extracted
                 print("--- ERROR: Exercise name not found in context for EXERCISE_SWAP ---")
                 prompt = "I understood you want to swap an exercise, but I couldn't identify which one from your message. Could you please specify the exercise name again?"
                 return await self.get_chat_response(prompt)

            print(f"--- User wants to swap: '{exercise_to_swap_name}' in routine '{routine_name}' ---")

            # --- Find Alternatives using Cached Templates --- 
            potential_swaps = []
            exercise_to_swap_muscle = None
            cached_templates = AIWorkoutOptimizer._cached_templates

            if not cached_templates:
                 print("--- WARNING: Exercise template cache is empty. Cannot find alternatives. ---")
                 # Fallback prompt if cache is empty
                 prompt = f"I understand you want to swap '{exercise_to_swap_name}', but I'm having trouble accessing the list of available exercises right now. Please try again later."
                 return await self.get_chat_response(prompt)

            # 1. Find the muscle group of the exercise to swap
            for template in cached_templates:
                if template.get('title') == exercise_to_swap_name:
                    exercise_to_swap_muscle = template.get('primary_muscle_group')
                    print(f"--- Found muscle group for '{exercise_to_swap_name}': {exercise_to_swap_muscle} ---")
                    break

            # 2. Find other exercises with the same primary muscle group
            if exercise_to_swap_muscle:
                for template in cached_templates:
                    if template.get('primary_muscle_group') == exercise_to_swap_muscle and \
                       template.get('title') != exercise_to_swap_name: # Exclude the original exercise
                        potential_swaps.append({
                            'name': template.get('title'),
                            'id': template.get('id'),
                            'muscles': template.get('primary_muscle_group') # Keep for consistency
                        })
                print(f"--- Found {len(potential_swaps)} potential swaps targeting {exercise_to_swap_muscle} (excluding original) ---")
            else:
                print(f"--- WARNING: Could not find primary muscle group for '{exercise_to_swap_name}'. Cannot suggest muscle-group based alternatives. ---")
                # Could add fallback logic here, e.g., suggest generic popular exercises?

            # --- Construct Prompt with REAL Alternatives --- 
            if potential_swaps:
                # Limit suggestions to avoid overwhelming user
                max_suggestions = 5
                suggestions_to_show = potential_swaps[:max_suggestions]
                
                # Format each swap
                formatted_list_items = [
                    f"*   **{swap['name']}** (Targets: {swap['muscles']})" 
                    for swap in suggestions_to_show
                ]
                formatted_swaps_string = "\n\n".join(formatted_list_items)
                
                prompt = f"""Okay, you want to swap the exercise '{exercise_to_swap_name}' in your '{routine_name}' routine. 

Based on exercises targeting the same primary muscle group ({exercise_to_swap_muscle}), here are some potential alternatives:

{formatted_swaps_string}

Please let me know which one you'd like to use. If none of these seem right, tell me more about what you're looking for.
"""
            elif exercise_to_swap_muscle: # Found muscle group, but no alternatives
                 prompt = f"I understand you want to swap '{exercise_to_swap_name}' (which targets {exercise_to_swap_muscle}) in your '{routine_name}' routine. However, I couldn't find any other exercises in the database that primarily target the same muscle group. You might need to search for exercises manually or consider alternatives targeting secondary muscles."
            else: # Could not find original exercise/muscle group
                prompt = f"I understand you want to swap '{exercise_to_swap_name}' in your '{routine_name}' routine, but I couldn't find that specific exercise in my database to determine its muscle group. Could you confirm the spelling or perhaps suggest a type of exercise you're looking for as an alternative?"

            print("--- Prompt for EXERCISE_SWAP (using real alternatives) ---")
            print(prompt)
            print("-------------------------------------------------------------")
            response = await self.get_chat_response(prompt)

            # --- ADDED: Store context for potential SUGGESTION_IMPLEMENT next turn --- 
            if target_routine and exercise_to_swap_name and potential_swaps:
                self.pending_swap_context = {
                    "type": "EXERCISE_SWAP", # Indicate the type of pending action
                    "routine_id": target_routine.get('id'),
                    "routine_name": routine_name, # Store for user messages
                    "exercise_to_swap_title": exercise_to_swap_name,
                    "suggestions": suggestions_to_show, # Store the actual suggestions shown
                    # --- ADDED: Store current exercises from the fetched routine --- 
                    "current_exercises": target_routine.get('exercises', [])
                }
                print(f"--- Stored pending swap context: {self.pending_swap_context} ---")
            else:
                 # Clear any stale context if we couldn't provide suggestions
                 self.pending_swap_context = None
                 print("--- Cleared pending swap context due to missing info/suggestions. ---")

            # --- ADDED: Log final state before returning --- 
            print(f"--- EXERCISE_SWAP block finishing. Final pending context: {self.pending_swap_context} ---")
            return response
            
        elif intent == "SUGGESTION_IMPLEMENT":
             # --- Phase 3: Implement the suggested exercise swap --- 
             print("--- Handling SUGGESTION_IMPLEMENT intent (Exercise Swap) ---")
             
             # --- UPDATED: Use stored pending context and extract choice from message --- 
             pending_context = self.pending_swap_context
             if not pending_context or pending_context.get("type") != "EXERCISE_SWAP":
                 print("--- ERROR: No valid pending exercise swap context found for SUGGESTION_IMPLEMENT. ---")
                 prompt = "I'm sorry, I don't have a pending exercise swap suggestion active. Could you please restate your initial swap request?"
                 self.pending_swap_context = None # Clear any invalid state
                 return await self.get_chat_response(prompt)

             # Extract necessary info from stored context
             routine_id = pending_context.get('routine_id')
             exercise_to_swap_title = pending_context.get('exercise_to_swap_title')
             routine_name = pending_context.get('routine_name', 'the routine')
             suggestions = pending_context.get('suggestions', []) # Get the list of suggestions

             # Extract chosen alternative title from the *current* user message
             # Use a helper function or IntentService method if needed
             # For now, basic extraction (needs improvement)
             chosen_alternative_title = None
             message_lower = message.lower()
             # Check if any suggestion title is mentioned
             for sugg in suggestions:
                 sugg_title = sugg.get('name')
                 if sugg_title and sugg_title.lower() in message_lower:
                     chosen_alternative_title = sugg_title
                     print(f"--- Matched chosen alternative '{chosen_alternative_title}' from message. ---")
                     break
             # Simple fallback checks if no direct match
             if not chosen_alternative_title:
                 # Placeholder: Use context extraction from IntentService or similar
                 temp_context = {} # Create temp dict for context extraction call
                 chosen_match = re.search(r"(?:use|with|go with|choose|select)\s+([\w\s\(\)-]+)", message, re.IGNORECASE)
                 if chosen_match:
                     chosen_alternative_title = chosen_match.group(1).strip()
                     print(f"--- Extracted potential chosen alternative: '{chosen_alternative_title}' (regex fallback) ---")
                 else:
                     print("--- WARNING: Could not reliably extract chosen alternative from message for SUGGESTION_IMPLEMENT. ---")
                     prompt = f"Sorry, I couldn't figure out which exercise you wanted to use from your message ('{message}'). Please clearly state the name of the exercise from the list I provided."
                     # DO NOT clear pending_swap_context here, let user try again
                     return await self.get_chat_response(prompt)

             # --- Input Validation ---
             if not all([routine_id, exercise_to_swap_title, chosen_alternative_title]):
                 print(f"--- ERROR: Missing context for SUGGESTION_IMPLEMENT after extraction. Need routine_id, exercise_to_swap_title, chosen_alternative_title. Context: {pending_context}, Chosen: {chosen_alternative_title} ---")
                 prompt = "I'm sorry, I seem to have lost some details for the swap. Could you please state the swap again? (e.g., 'swap X for Y in routine Z')"
                 self.pending_swap_context = None # Clear invalid state
                 return await self.get_chat_response(prompt)

             print(f"--- Attempting to swap '{exercise_to_swap_title}' with '{chosen_alternative_title}' in routine ID {routine_id} ('{routine_name}') ---")

             try:
                 # 2. Find the chosen alternative template in the cache
                 chosen_template = None
                 cached_templates = AIWorkoutOptimizer._cached_templates
                 if not cached_templates:
                     print("--- ERROR: Exercise template cache is empty for SUGGESTION_IMPLEMENT. ---")
                     prompt = f"I found your request to use '{chosen_alternative_title}', but I'm having trouble accessing the exercise database right now to make the change. Please try again later."
                     return await self.get_chat_response(prompt)

                 for template in cached_templates:
                     if template.get('title') == chosen_alternative_title:
                         chosen_template = template
                         break
                 
                 if not chosen_template:
                      print(f"--- ERROR: Could not find template for chosen alternative '{chosen_alternative_title}' in cache. ---")
                      prompt = f"I'm sorry, I couldn't find the details for '{chosen_alternative_title}' in the exercise database. Perhaps the name is slightly different?"
                      return await self.get_chat_response(prompt)
                 
                 print(f"--- Found template for chosen alternative: {chosen_template} ---")
                 chosen_template_id = chosen_template.get('id')
                 if not chosen_template_id:
                      print(f"--- ERROR: Found template for '{chosen_alternative_title}' but it has no ID! Template: {chosen_template} ---")
                      prompt = f"I found '{chosen_alternative_title}' but there seems to be an issue with its data (missing ID). I can't add it to the routine right now."
                      self.pending_swap_context = None # Clear state on error
                      return await self.get_chat_response(prompt)

                 # 3. Fetch the *current* state of the routine
                 # print(f"--- Fetching current state of routine {routine_id} before update... ---")
                 # current_routine_data = await self.hevy_api.get_routine(routine_id)
                 # if not current_routine_data or 'exercises' not in current_routine_data:
                 #      print(f"--- ERROR: Could not fetch current routine data for ID {routine_id}. ---")
                 #      raise ValueError("Failed to fetch current routine data.")
                 
                 # Use the exercises list stored during the suggestion phase
                 current_exercises = pending_context.get('current_exercises')
                 if current_exercises is None: # Check if it was missing/null
                     print(f"--- ERROR: current_exercises list not found in pending context {pending_context}. Cannot perform swap. ---")
                     raise ValueError("Missing exercise list from stored context.")
                 
                 print(f"--- Using stored exercise list. Current routine has {len(current_exercises)} exercises. ---")

                 # 4. Create the updated exercise list
                 updated_exercises = []
                 swap_performed = False

                 for i, exercise in enumerate(current_exercises):
                     if exercise.get('title') == exercise_to_swap_title:
                         print(f"--- Found exercise '{exercise_to_swap_title}' at index {i} to replace. ---")
                         swap_performed = True
                         # Create the new exercise object based on the chosen template
                         new_exercise = {
                             "title": chosen_alternative_title,
                             "notes": None, # Default notes
                             "exercise_template_id": chosen_template_id,
                             "superset_id": None, # Assume not part of superset for now
                             "sets": [
                                 {"type": "normal", "weight_kg": None, "reps": None}, 
                                 {"type": "normal", "weight_kg": None, "reps": None},
                                 {"type": "normal", "weight_kg": None, "reps": None}
                             ]
                         }
                         updated_exercises.append(new_exercise)
                     else:
                         # Keep the existing exercise, removing the index field if present
                         exercise.pop('index', None) # Remove index if it exists
                         updated_exercises.append(exercise)
                 
                 # Re-check if swap actually happened
                 if not swap_performed:
                     print(f"--- ERROR: Did not find exercise '{exercise_to_swap_title}' in the current routine state for {routine_id}. Cannot perform swap. ---")
                     prompt = f"I looked for '{exercise_to_swap_title}' in your '{routine_name}' routine to swap it, but I couldn't find it there anymore. Has it been changed or removed recently?"
                     self.pending_swap_context = None # Clear state
                     return await self.get_chat_response(prompt)
                     
                 # 5. Construct the update payload
                 update_payload = {
                     "routine": {
                         "title": routine_name, # Use stored routine_name
                         "exercises": updated_exercises
                     }
                 }

                 # 6. Call Hevy API to update the routine
                 print(f"--- Calling update_routine for ID {routine_id} with {len(updated_exercises)} exercises... ---")
                 update_response = await self.hevy_api.update_routine(routine_id, update_payload)
                 print(f"--- Update routine API response: {update_response} ---") # Log response

                 # 7. Generate confirmation response
                 # TODO: Check update_response for actual success indicator if API provides one
                 prompt = f"Okay, I've updated your '{routine_name}' routine. I've replaced '{exercise_to_swap_title}' with '{chosen_alternative_title}'."

             except Exception as e:
                 print(f"--- ERROR during SUGGESTION_IMPLEMENT swap execution: {e} ---")
                 traceback.print_exc() # Log detailed error traceback
                 prompt = f"I encountered an error while trying to update the '{routine_name}' routine. I couldn't swap '{exercise_to_swap_title}' for '{chosen_alternative_title}'. Please try again later or check the routine in the app."
                 # --- ADDED: Clear state on error --- 
                 self.pending_swap_context = None 

             # --- ADDED: Clear state on success --- 
             # (Assuming the API call section ends before this)
             # We should clear the state regardless of API success/failure, as the action was attempted.
             finally:
                  self.pending_swap_context = None
                  print("--- Cleared pending swap context after handling SUGGESTION_IMPLEMENT. ---")

             # Send final response to user
             response = await self.get_chat_response(prompt)
             return response

        else:
            # Fallback for other/unimplemented modification intents
            print(f"--- Handling modification intent '{intent}' with fallback logic ---")
            prompt = f"User requested a modification (Intent: {intent}): '{message}'. Context: {str(context)}. This specific modification isn't fully implemented yet. Please explain the general steps you *would* take to help the user with this type of request (e.g., asking for details, confirming changes), but state clearly that you cannot perform the action automatically right now."
            response = await self.get_chat_response(prompt) 
            return response

    async def chat_about_workout_optimization(self, user_message: str, context: Dict[str, Any] = None) -> str:
        """
        Engage in a conversation about workout optimization.
        [REFACTORED - This is now primarily a fallback if specific intent handlers are not matched,
         or could be used for very general, non-specific chat if needed.]
        """
        try:
            print("\n===== START: chat_about_workout_optimization [Refactored Fallback] =====")
            print(f"User message: {user_message}")
            print(f"Context provided: {context}") # Context here is likely from IntentService now

            # Simplified fallback logic - provide minimal context
            context_summary = "No specific context provided for this general chat."
            if context:
                context_summary = f"Relevant context: {list(context.keys())}" # Just show keys for brevity

            prompt = f"""Context Summary: {context_summary}

User's message (seems general or fallback): {user_message}

Please provide a helpful, general response related to workout optimization or ask clarifying questions if the request is unclear."""

            print("\nSending simplified fallback prompt to AI...")
            response = await self.get_chat_response(prompt)
            print(f"Received response: {response[:100]}...")
            print("\n===== END: chat_about_workout_optimization [Refactored Fallback] =====\n")
            return response

        except Exception as e:
            print(f"\n❌ Error in refactored chat_about_workout_optimization: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"I encountered an error processing this request. Error: {str(e)}"

    async def analyze_program(self, user_message: str) -> Dict[str, Any]:
        """
        Analyze the current workout program.
        
        Args:
            user_message: The original user message requesting analysis (for goal extraction).

        Returns:
            Dict containing program analysis
        """
        print("--- AI Optimizer: analyze_program() called ---")
        try:
            # Fetch program details
            print("--- analyze_program: Fetching program details... ---")
            current_program_details = await self.hevy_api.get_current_program_details()
            
            # --- CORRECTED: Check cache and use it, remove redundant fetch --- 
            # REMOVED: all_templates = await self.hevy_api.get_all_exercise_templates()

            if AIWorkoutOptimizer._cached_templates is None:
                print("--- analyze_program: WARNING - Template cache not loaded, attempting fallback load ---")
                await AIWorkoutOptimizer.load_templates_cache(self.hevy_api)
                # If fallback fails, _cached_templates will be []

            # Use the value FROM the cache
            all_templates = AIWorkoutOptimizer._cached_templates if AIWorkoutOptimizer._cached_templates is not None else []
            print(f"--- analyze_program: Using {len(all_templates)} cached exercise templates. ---")
            # --- END CORRECTION --- 

            if not current_program_details:
                return {"error": "Could not retrieve current program data."}

            folder = current_program_details.get("folder")
            routines = current_program_details.get("routines")

            if not folder or not routines:
                 return {"error": "Incomplete program data retrieved."}

            # Prepare context string for the program structure
            program_context_str = self._prepare_program_context(folder, routines)
            
            # --- Extract user goal --- 
            user_goal = self._extract_user_goal(user_message)
            print(f"--- analyze_program: Extracted User goal: {user_goal} ---")

            # Get the structured analysis from the AI
            ai_analysis_response = await self._get_program_analysis(program_context_str, all_templates, user_goal)

            # Combine program details with AI analysis
            final_analysis = {
                "program_name": folder.get("title", "Unknown Program"),
                "folder_id": folder.get("id"),
                "number_of_routines": len(routines),
                # The AI response is expected to be pre-formatted Markdown now
                "analysis": ai_analysis_response.get("analysis_text", "AI analysis not available"), 
                # "recommendations": ai_analysis_response.get("recommendations", []), # Might be part of analysis_text
            }
            print(f"--- Program Analysis Complete for: {final_analysis['program_name']} ---")
            return final_analysis

        except Exception as e:
            print(f"Error during program analysis: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to analyze program: {str(e)}"}

    def _prepare_program_context(self, folder: Dict[str, Any], routines: List[Dict[str, Any]]) -> str:
        """
        Prepare program data as context for AI analysis.
        
        Args:
            folder: Program folder details
            routines: List of routines in the program
            
        Returns:
            Formatted context string for AI analysis
        """
        context = f"""
        Program Analysis:
        Name: {folder.get('title', 'Unknown Program')}
        Total Routines: {len(routines)}
        
        Routine Structure:
        """
        
        for routine in routines:
            context += f"""
            Routine: {routine.get('title', 'Unknown')}
            Exercises:
            """
            
            for exercise in routine.get('exercises', []):
                sets_info = exercise.get('sets', [])
                context += f"""
                - {exercise.get('title', 'Unknown Exercise')}
                  Sets: {len(sets_info)}
                  Rep Range: {self._get_rep_range(sets_info)}
                  Weight Range: {self._get_weight_range(sets_info)}
                """
        
        return context

    def _get_rep_range(self, sets: List[Dict[str, Any]]) -> str:
        """Get the rep range from a list of sets."""
        reps = [s.get('reps') for s in sets if s.get('reps') is not None]
        if not reps:
            return "N/A"
        return f"{min(reps)}-{max(reps)}"

    def _get_weight_range(self, sets: List[Dict[str, Any]]) -> str:
        """Get the weight range from a list of sets."""
        weights = [s.get('weight_kg') for s in sets if s.get('weight_kg') is not None]
        if not weights:
            return "Bodyweight/N/A"
        return f"{min(weights):.1f}kg-{max(weights):.1f}kg"

    async def _get_program_analysis(self, program_context_str: str, available_exercises: List[Dict], user_goal: Optional[str] = None) -> Dict[str, Any]:
        """
        Get AI analysis of a workout program, potentially incorporating web search and user goals.
        
        Args:
            program_context_str: String containing the current program structure.
            available_exercises: List of available exercise templates from Hevy.
            user_goal: Optional string describing the user's specific goal (e.g., "develop my chest").
            
        Returns:
            Dict containing AI-generated program analysis and recommendations.
        """
        
        web_search_context = ""
        serpapi_key = os.getenv("SERPAPI_API_KEY")
        
        if user_goal and serpapi_key:
            # --- Perform Web Search using SerpApi --- 
            search_query = f"recommendations for {user_goal} with upper lower split program structure"
            print(f"--- Performing SerpApi search (async wrapper) for goal: '{user_goal}' with query: '{search_query}' ---")
            try:
                params = {
                    "q": search_query,
                    "api_key": serpapi_key,
                    "num": 3 # Request top 3 results
                }
                search = GoogleSearch(params)
                # --- UPDATED: Run synchronous blocking call in a thread --- 
                results = await asyncio.to_thread(search.get_dict)
                # --- END UPDATE --- 
                
                organic_results = results.get("organic_results", [])
                
                results_str = "\n".join([
                    f"- {result.get('title', '')}: {result.get('snippet', '')} (Source: {result.get('link', 'N/A')})" 
                    for result in organic_results[:3] # Ensure we only take up to 3
                ])
                
                if results_str:
                    web_search_context = f"\n\nWeb Search Results for \"{search_query}\":\n{results_str}"
                    print(f"--- SerpApi search successful. Added {len(organic_results[:3])} result snippets to context. ---")
                else:
                     web_search_context = "\n\nWeb search via SerpApi returned no relevant organic results."
                     print("--- SerpApi search returned no organic results. ---")
                     
            except Exception as e:
                print(f"--- SerpApi search failed: {e} ---")
                # Optionally log more details about the error e
                web_search_context = "\n\nWeb search could not be performed due to an error." 
        elif user_goal and not serpapi_key:
             print("--- Skipping web search: SERPAPI_API_KEY not found in environment. ---")
             web_search_context = "\n\nWeb search skipped: API key not configured."

        # --- Prepare list of available exercises for the prompt --- 
        exercise_list_str = "None Available"
        if available_exercises:
            # Extract titles from the list of dicts
            exercise_titles = [ex.get('title', 'Unknown') for ex in available_exercises]
            # Limit the list slightly just in case, though should be less of an issue now
            limit = 500 
            if len(exercise_titles) > limit:
                 exercise_list_str = "\n".join([f"- {title}" for title in exercise_titles[:limit]]) + "\n... (list truncated)"
            else:
                 exercise_list_str = "\n".join([f"- {title}" for title in exercise_titles])
        
        # --- Construct the Detailed Prompt --- 
        prompt = f"""You are an expert fitness coach analyzing a user's workout program. 

User's Goal: {user_goal if user_goal else 'General program analysis requested.'}

Current Program Structure:
{program_context_str}

Available Exercises in App (Suggest ONLY from this list if adding/swapping):
---
{exercise_list_str}
---
{web_search_context}

Instructions:
1.  Analyze the user's **Current Program Structure** in relation to their stated **User's Goal**. If no specific goal, provide a general analysis.
2.  If a **User's Goal** is provided, use the **Web Search Context** (if available) and your fitness knowledge to inform your recommendations.
3.  Provide **specific, actionable recommendations** for modification. Focus on exercise additions, removals, or swaps to better align the program with the goal.
4.  **Format your response clearly** using Markdown:
    *   Start with a brief summary of the analysis.
    *   Use a heading like `## Proposed Program Changes`. 
    *   List the **Current Routines** involved in the changes (showing relevant exercises).
    *   List the **Proposed Routines** showing the *exact* structure with suggested modifications (exercise swaps/additions).
    *   Use a heading like `## Summary of Changes` and list the key modifications made.
    *   If suggesting new exercises, **strictly ensure they are present in the 'Available Exercises in App' list provided above.** Do not invent exercises.
    *   If no changes are recommended, state that clearly and explain why the current program is suitable.
5.  Be concise but thorough in your explanation of the changes.
"""
        
        print("--- Sending detailed analysis prompt to AI... ---")
        # Get AI response - Markdown formatting is handled by get_chat_response
        response_text = await self.get_chat_response(prompt) 
        print("--- Received analysis response from AI. ---")
        
        # TODO: Parse the response into sections? For now, return raw text.
        # We are returning the raw response text which should be formatted by the AI according to instructions.
        return {
            # "overview": response[:200] + "...",
            # "structure_analysis": "Program structure analysis...",
            # "exercise_analysis": "Exercise selection analysis...",
            # "recommendations": [line.strip() for line in response.split('\n') if line.strip()],
            # "raw_response": response,
            "analysis_text": response_text # Returning the full, AI-formatted response
        }

    def _parse_program_analysis(self, response: str) -> Dict[str, Any]:
        # This method might become redundant if the AI formats the response directly
        # Kept for now, but the logic above returns the raw response.
        """Parse the AI program analysis response into structured data.""" 
        # TODO: Implement more sophisticated parsing if needed later
        print("--- (_parse_program_analysis called - currently returning raw response) ---")
        return {
            # "overview": response[:200] + "...",
            # "structure_analysis": "Program structure analysis...",
            # "exercise_analysis": "Exercise selection analysis...",
            # "recommendations": [line.strip() for line in response.split('\n') if line.strip()],
            # "raw_response": response,
            "analysis_text": response # Return raw response as per current logic
        } 

    # --- ADDED: Helper to extract goal from message --- 
    def _extract_user_goal(self, message: str) -> Optional[str]:
        """Attempts to extract a user's stated goal from their message (using simple find)."""
        message_lower = message.lower()
        keywords = [
            "goal is to ", 
            "want to ", 
            "focus on ", 
            "develop my ", 
            "improve my ", 
            "get better at ", 
            "increase my "
        ]
        
        for keyword in keywords:
            index = message_lower.find(keyword)
            if index != -1:
                # Extract text after the keyword
                start_index = index + len(keyword)
                # --- UPDATED: Strip quotes as well --- 
                goal = message[start_index:].strip(" .!?\'\"") # Extract from original message, strip punctuation/quotes
                # Basic length check
                if 0 < len(goal) < 100:
                    return goal
        
        return None

    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the AI response into structured data.
        
        Args:
            response: Raw AI response text
            
        Returns:
            Structured dictionary of insights
        """
        # TODO: Implement more sophisticated parsing of AI response
        # For now, return a basic structure
        return {
            "summary": response[:200] + "...",  # First 200 chars as summary
            "recommendations": [line.strip() for line in response.split('\n') if line.strip()],
            "exercise_insights": {},  # TODO: Parse exercise-specific insights
            "raw_response": response
        } 