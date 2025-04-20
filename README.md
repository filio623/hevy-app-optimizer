# Hevy Workout Optimizer

An AI-powered workout optimization tool that interfaces with the Hevy Workout app API to analyze and modify workouts through natural language interactions.

## Features

- Natural language interface for workout modifications
- Integration with Hevy Workout app API
- Exercise substitution recommendations
- Workout program analysis
- Historical workout data tracking
- AI-powered workout optimization
- Personalized exercise suggestions
- Workout pattern analysis
- Training balance recommendations
- Interactive chat about workout optimization

## Project Status

The project is currently in active development with the following components implemented:

### Backend Services

- **HevyAPI Service**: A comprehensive client for interacting with the Hevy fitness app API
  - Authentication and session management
  - Methods for all major API endpoints (workouts, routines, exercise templates)
  - Error handling and rate limiting
  - Comprehensive test coverage

- **WorkoutOptimizer Service**: Analyzes workout data to provide optimization suggestions
  - Workout frequency and pattern analysis
  - Exercise progression tracking (weight and rep changes)
  - Personalized exercise suggestions
  - Overall workout recommendations
  - Training balance identification

- **AIWorkoutOptimizer Service**: Enhances the base optimizer with AI capabilities
  - Combines data analysis with AI-generated insights
  - Natural language understanding for user questions
  - Personalized recommendations based on workout history
  - Injury risk identification
  - Interactive chat about workout optimization

- **ChatService**: Manages AI interactions with multiple LLM providers
  - Support for OpenAI and Anthropic models
  - Conversation history and context management
  - Specialized methods for workout-specific responses
  - Retry logic for API reliability

### API Endpoints

- Workout endpoints for retrieving, creating, and updating workouts
- Routine endpoints for managing workout routines
- Exercise template endpoints for accessing exercise information
- Optimization endpoints for getting workout optimization suggestions
- Chat endpoints for interacting with the AI about workout optimization

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   # Backend
   cd backend
   pip install -r requirements.txt
   
   # Frontend (coming soon)
   cd frontend
   npm install
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your configuration:
   - HEVY_API_KEY
   - OPENAI_API_KEY
   - DATABASE_URL
   - REDIS_URL

4. Run the development servers:
   ```bash
   # Backend
   cd backend
   uvicorn app.main:app --reload
   
   # Frontend (coming soon)
   cd frontend
   npm run dev
   ```

## Project Structure

```
project/
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── core/         # Core functionality
│   │   ├── models/       # Database models
│   │   └── services/     # Business logic
│   │       ├── hevy_api.py           # Hevy API client
│   │       ├── workout_optimizer.py   # Workout analysis service
│   │       ├── ai_workout_optimizer.py # AI-enhanced optimizer
│   │       └── chat_service.py        # AI chat service
│   ├── tests/            # Test files
│   └── requirements.txt
├── frontend/             # Coming soon
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   └── services/     # API services
│   └── package.json
└── docker-compose.yml
```

## API Documentation

API documentation is available at `/docs` when running the backend server.

## Key Features

### Workout Analysis
- **Frequency Tracking**: Analyzes how often workouts are performed
- **Exercise Progression**: Tracks changes in weight and reps over time
- **Training Balance**: Identifies imbalances between muscle groups
- **Rest Period Analysis**: Evaluates rest periods between sets

### Optimization Suggestions
- **Exercise-Specific Recommendations**: Personalized advice for each exercise
- **Overall Workout Recommendations**: General suggestions for workout improvement
- **Progression Strategies**: Advice on how to progressively overload
- **Injury Prevention**: Identifying potential risks and suggesting safer alternatives

### AI-Enhanced Insights
- **Natural Language Understanding**: Responds to user questions about workouts
- **Personalized Advice**: Tailors recommendations to individual workout patterns
- **Interactive Experience**: Enables conversation about workout optimization
- **Advanced Pattern Recognition**: Identifies trends that might not be obvious from data alone

## Next Steps

- Creating a frontend interface to display optimization suggestions
- Implementing user authentication for personalized recommendations
- Adding more advanced analysis features (e.g., muscle group targeting, recovery tracking)
- Enhancing the AI capabilities with more specialized workout knowledge
- Implementing data visualization for workout trends and progress

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT 