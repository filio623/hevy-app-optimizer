## Future Work / Enhancements

### Intent Handling & Context
- **Implement Specific Routine Parsing:** In `IntentService.get_relevant_context`, enhance the `ROUTINE_INFO` intent handler:
    - Implement robust logic (e.g., using NLP or better regex) to extract the specific routine name from the user's message.
    - If a name is found, use `hevy_api.find_routine_by_title()` to fetch only that routine's details.
    - Add the specific routine details to the context.
- **Improve `EXERCISE_INFO` Context:** Similar to routines, parse specific exercise names and fetch/format their details rather than just listing all templates.
- **Implement Context Gathering:** Add *actual* data fetching logic (e.g., using `HevyAPI`) to `IntentService.get_relevant_context` based on classified intents (beyond just placeholder fetches).
- **Contextual History:** Implement logic to use conversation history more effectively, especially for follow-up questions or implementing suggestions.

### Response Generation & Actions
- **Enhance `get_info_response` for Routines/Exercises:** In `AIWorkoutOptimizer.get_info_response`, update the `ROUTINE_INFO` and `EXERCISE_INFO` blocks:
    - Check for specific details in the context (once context fetching is improved).
    - Format the specific routine/exercise details clearly for the prompt.
- **Implement Intent Handlers:** Flesh out the logic within `get_analysis_response`, and `get_modification_response` methods in `AIWorkoutOptimizer` to use context and generate meaningful AI prompts/actions.
- **Implement Modification Actions:** Add logic to `get_modification_response` to actually perform requested changes (e.g., exercise swaps, routine updates) via `HevyAPI` calls after AI planning/user confirmation.
- **Implement Sophisticated Parsing:** Improve `_parse_ai_response` and `_parse_program_analysis` methods to extract structured data from AI responses instead of just using raw text.
- **Refine Prompts:** Enhance AI prompts in handler methods for better, more accurate, and research-based responses.

### Architecture & Cleanup
- **Consolidate AI Calls:** Refactor `get_ai_response` (in `intent_service.py`) and `get_chat_response` (in `ai_workout_optimizer.py`) into a single, shared utility/service for making OpenAI calls.
- **Refine Dependencies:** Improve how services (`HevyAPI`, `IntentService`, `AIWorkoutOptimizer`) are initialized and injected using FastAPI's dependency system for better testability and management.
- **Data Storage:** Consider adding database (e.g., PostgreSQL, SQLite) storage for chat history and potentially analysis results.
- **Clarify Analysis Flows:** Review analysis triggered via dedicated endpoints vs. chat intents. Decide if both are needed, merge if possible, or remove redundant paths.

### Quality & Maintenance
- **Error Handling for API Calls:** Add more specific error handling around API calls in `HevyAPI` and `IntentService` to provide clearer feedback to the user if data fetching fails (e.g., routine not found).
- **Improve Logging:** Replace debug `print` statements throughout the backend with a proper logging library (e.g., Python's `logging`).
- **Add Unit/Integration Tests:** Create tests for services (`IntentService`, `AIWorkoutOptimizer`) and routers.

### Analysis & Recommendations
- **Enhance Specificity:** Improve workout/program analysis and recommendations:
    - Analyze progression trends for individual exercises over time.
    - Incorporate user's stated goals (e.g., from chat history) into analysis.
    - Provide concrete, actionable recommendations (specific exercise changes, set/rep adjustments).
    - Utilize workout history data alongside program structure.
- **Fine-tune Analysis Content/Prompt:** Refine the prompt in `_get_program_analysis` and potentially the AI model's responses for clarity, accuracy, structure, and adherence to formatting instructions.
- **Implement Sophisticated Parsing:** Improve `_parse_ai_response` and `_parse_program_analysis` methods to extract structured data from AI responses instead of just using raw text.
- **Clarify Analysis Flows:** Review analysis triggered via dedicated endpoints vs. chat intents. Decide if both are needed, merge if possible, or remove redundant paths. 