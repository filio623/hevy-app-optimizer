from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import re

from ..services.ai_workout_optimizer import AIWorkoutOptimizer
from ..dependencies import get_ai_optimizer
from ..services.intent_service import IntentService
from ..dependencies import get_intent_service

router = APIRouter()

class ChatMessage(BaseModel):
    """Schema for chat messages"""
    message: str

@router.post("/")
async def workout_chat(
    chat_input: ChatMessage,
    ai_optimizer: AIWorkoutOptimizer = Depends(get_ai_optimizer),
    intent_service: IntentService = Depends(get_intent_service)
) -> Dict[str, Any]:
    """
    Process chat messages based on classified intent and relevant context.
    """
    try:
        print(f"\n--- Processing Chat Request: '{chat_input.message}' ---")
        # --- ADDED: Log incoming pending state --- 
        print(f"--- State at request start: ai_optimizer.pending_swap_context = {ai_optimizer.pending_swap_context} ---") 

        # --- State Management Logic --- 
        intent = None
        context = {}
        response_content = "" # Initialize response content variable
        response_data = {}
        user_message = chat_input.message
        
        # Check for pending swap context
        if ai_optimizer.pending_swap_context and ai_optimizer.pending_swap_context.get("type") == "EXERCISE_SWAP":
            print("--- Pending exercise swap context found. Attempting to handle as SUGGESTION_IMPLEMENT. ---")
            # Assume intent is SUGGESTION_IMPLEMENT
            intent = "SUGGESTION_IMPLEMENT"
            # Extract chosen alternative from the current message (basic logic)
            chosen_alternative_title = None
            message_lower = user_message.lower()
            suggestions = ai_optimizer.pending_swap_context.get('suggestions', [])
            for sugg in suggestions:
                 sugg_title = sugg.get('name')
                 if sugg_title and sugg_title.lower() in message_lower:
                     chosen_alternative_title = sugg_title
                     break
            # Fallback regex (similar to the one in AIWorkoutOptimizer)
            if not chosen_alternative_title:
                 chosen_match = re.search(r"(?:use|with|go with|choose|select)\s+([\w\s\(\)-]+)", user_message, re.IGNORECASE)
                 if chosen_match:
                     chosen_alternative_title = chosen_match.group(1).strip()
            
            if chosen_alternative_title:
                 print(f"--- Router extracted chosen alternative: '{chosen_alternative_title}' ---")
                 # Populate context directly using stored + extracted info
                 context = {
                     "routine_id": ai_optimizer.pending_swap_context.get('routine_id'),
                     "exercise_to_swap_title": ai_optimizer.pending_swap_context.get('exercise_to_swap_title'),
                     "routine_name": ai_optimizer.pending_swap_context.get('routine_name'),
                     "chosen_alternative_title": chosen_alternative_title
                 }
                 # Skip normal intent classification and context gathering
            else:
                 print("--- Could not extract choice from user message while swap context was pending. Falling back to classification. ---")
                 # Clear the pending context as the user message seems unrelated
                 ai_optimizer.pending_swap_context = None
                 intent = None # Reset intent so normal classification runs
        
        # --- Normal Intent Classification Flow (if no pending action handled) --- 
        if intent is None: 
            print("--- No pending action found or handled, proceeding with intent classification. ---")
            # --- Pass conversation history to classify_intent --- 
            history = ai_optimizer.get_conversation_history()
            intent = await intent_service.classify_intent(user_message, conversation_history=history)
            context = await intent_service.get_relevant_context(intent, user_message)
            # --- If classification results in unrelated intent, clear pending state --- 
            if intent != "SUGGESTION_IMPLEMENT" and ai_optimizer.pending_swap_context:
                 print(f"--- User provided unrelated intent ('{intent}') while swap was pending. Clearing pending state. ---")
                 ai_optimizer.pending_swap_context = None

        # --- Routing based on intent --- 
        if intent == "SUGGESTION_IMPLEMENT":
             # Ensure context is populated (either from state check or potentially intent service - though state check is primary)
             if not context.get('chosen_alternative_title'):
                  # Attempt extraction again if missed by state check somehow (shouldn't happen often)
                  # Or rely on the AIWorkoutOptimizer handler to request clarification
                  print("--- WARNING: SUGGESTION_IMPLEMENT intent routed, but context missing chosen_alternative_title. Handler needs to cope. ---")
             print(f"--- Routing to Modification/Action (Intent: {intent}) ---")
             response_content = await ai_optimizer.get_modification_response(user_message, intent, context)
             response_data = {"response": response_content, "intent": intent}
        elif intent == "GREETING":
            response_content = "Hello! How can I help you with your workouts today?"
            # No need to call AI optimizer for a simple greeting
            response_data = {"response": response_content, "intent": intent}
        elif intent == "UNKNOWN":
            response_content = "Sorry, I'm not sure how to help with that. Can you please rephrase or ask about your workouts?"
            # No need to call AI optimizer for unknown intent
            response_data = {"response": response_content, "intent": intent}
        elif intent in ["WORKOUT_INFO", "EXERCISE_INFO", "ROUTINE_INFO", "PROGRAM_INFO", "GENERAL_INFO"]:
            print(f"--- Routing to Information Retrieval (Intent: {intent}) ---")
            # --- Replace Placeholder with Actual Call ---
            response_content = await ai_optimizer.get_info_response(user_message, intent, context)
            response_data = {"response": response_content, "intent": intent}

        elif intent in ["WORKOUT_ANALYSIS", "PROGRAM_ANALYSIS", "EXERCISE_ANALYSIS", "COMPARATIVE_ANALYSIS"]:
            print(f"--- Routing to Analysis (Intent: {intent}) ---")
            # --- Pass chat_input.message to the handler ---
            response_content = await ai_optimizer.get_analysis_response(user_message, intent, context)
            response_data = {"response": response_content, "intent": intent}

        elif intent in ["EXERCISE_SWAP", "PROGRAM_CREATE", "ROUTINE_UPDATE", "SUGGESTION_IMPLEMENT"]:
            print(f"--- Routing to Modification/Action (Intent: {intent}) ---")
            # --- Replace Placeholder with Actual Call ---
            response_content = await ai_optimizer.get_modification_response(user_message, intent, context)
            response_data = {"response": response_content, "intent": intent}

        else:
            # Fallback for any unexpected, non-UNKNOWN intent that wasn't caught by IntentService validation
            print(f"--- Warning: Unhandled intent '{intent}'. Falling back. ---")
            response_content = "Sorry, I encountered an unexpected situation handling your request."
            # Attempt fallback using the generic chat method
            # response_content = await ai_optimizer.chat_about_workout_optimization(chat_input.message, context)
            response_data = {"response": response_content, "intent": "UNKNOWN"} # Ensure intent is UNKNOWN

        # --- Update conversation history using the final response_content ---
        # Only add non-empty user messages and assistant responses
        if user_message:
            ai_optimizer.conversation_history.append({"role": "user", "content": user_message})
        if response_content: # Ensure we have a response before adding
            ai_optimizer.conversation_history.append({"role": "assistant", "content": response_content})

        print(f"--- Sending Response: {str(response_data)[:200]}... ---")
        return response_data

    except Exception as e:
        print(f"!!! Error in workout_chat endpoint: {e} !!!")
        # Consider logging the full traceback in production
        # import traceback
        # print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"An internal error occurred: {str(e)}"
        )

@router.get("/history")
async def get_chat_history(
    ai_optimizer: AIWorkoutOptimizer = Depends(get_ai_optimizer)
) -> List[Dict[str, str]]:
    """
    Get the conversation history.
    """
    return ai_optimizer.get_conversation_history()

@router.delete("/history")
async def clear_chat_history(
    ai_optimizer: AIWorkoutOptimizer = Depends(get_ai_optimizer)
) -> Dict[str, str]:
    """
    Clear the conversation history.
    """
    ai_optimizer.clear_conversation_history()
    return {"status": "success", "message": "Chat history cleared"}

@router.post("/save")
async def save_chat_history(
    filepath: str = Body(..., embed=True),
    ai_optimizer: AIWorkoutOptimizer = Depends(get_ai_optimizer)
) -> Dict[str, str]:
    """
    Save the conversation history to a file.
    """
    try:
        ai_optimizer.save_conversation_history(filepath)
        return {"status": "success", "message": f"Chat history saved to {filepath}"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save chat history: {str(e)}"
        )

@router.post("/load")
async def load_chat_history(
    filepath: str = Body(..., embed=True),
    ai_optimizer: AIWorkoutOptimizer = Depends(get_ai_optimizer)
) -> Dict[str, str]:
    """
    Load conversation history from a file.
    """
    try:
        ai_optimizer.load_conversation_history(filepath)
        return {"status": "success", "message": f"Chat history loaded from {filepath}"}
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Chat history file not found: {filepath}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load chat history: {str(e)}"
        ) 