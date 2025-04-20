from .chat import router as chat_router
from .workouts import router as workouts_router
from .analysis import router as analysis_router
from .optimizer import router as optimizer_router

__all__ = ['chat_router', 'workouts_router', 'analysis_router', 'optimizer_router'] 