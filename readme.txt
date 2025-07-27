# AI Debate Platform Backend

A Flask-based backend service that orchestrates debates between 6 unique AI personalities using Hugging Face transformers and MongoDB for data persistence.

## Features

- 🤖 *6 AI Personalities*: The Philosopher, The Scientist, The Advocate, The Pragmatist, The Contrarian, and The Historian
- 🎯 *Multi-round Debates*: Structured debates with multiple rounds of arguments
- 🏆 *Judging System*: AI-powered or human judging with winner selection
- 📊 *Voting & Analytics*: Community voting and detailed debate analytics
- 🔄 *Real-time Generation*: Dynamic argument generation using Hugging Face models
- 📈 *Leaderboards*: Track personality performance and statistics

## Tech Stack

- *Backend*: Flask 2.3.3
- *Database*: MongoDB with PyMongo
- *AI Models*: Hugging Face Transformers (DialoGPT-medium)
- *Dependencies*: See requirements.txt

## Project Structure


ai-debate-platform/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── models/
│   ├── debate.py         # Debate and argument models
│   └── personality.py    # AI personality models
├── services/
│   ├── ai_service.py     # AI text generation service
│   ├── debate_service.py # Debate management service
│   └── personality_service.py # Personality management
├── routes/
│   ├── __init__.py       # Routes initialization
│   ├── main.py          # Main routes
│   ├── debate.py        # Debate-specific routes
│   └── api.py           # Main API endpoints
└── utils/
    ├── database.py       # Database connection and utilities
    └── helpers.py        # Utility functions


## Installation

1. *Clone the repository*
bash
git clone <repository-url>
cd ai-debate-platform


2. *Create virtual environment*
bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


3. *Install dependencies*
bash
pip install -r requirements.txt


4. *Set up environment variables*
bash
# Create .env file
cp .env.example .env

# Edit .env with your settings:
SECRET_KEY=your-secret-key-here
MONGODB_URI=mongodb://localhost:27017/ai_debate_platform
HUGGINGFACE_API_TOKEN=your-huggingface-token  # Optional


5. *Start MongoDB*
bash
# Using Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Or install MongoDB locally


6. *Run the application*
bash
python app.py


The server will start on http://localhost:5000

## API Endpoints

### Main Endpoints

- GET /health - Health check
- GET /info - Platform information
- GET /status - Platform status

### Debate Management

- GET /api/debates - Get all debates (paginated)
- POST /api/debates - Create new debate
- GET /api/debates/<id> - Get specific debate
- POST /api/debates/<id>/start - Start debate
- POST /api/debates/<id>/next-round - Proceed to next round
- POST /api/debates/<id>/judge - Judge debate
- POST /api/debates/<id>/vote - Vote on debate

### Personalities

- GET /api/personalities - Get all personalities
- GET /api/personalities/leaderboard - Get leaderboard

### Analytics

- GET /api/stats - Platform statistics
- GET /debate/<id>/analytics - Debate analytics
- GET /debate/<id>/summary - Debate summary

## Usage Examples

### Create a Debate

bash
curl -X POST http://localhost:5000/api/debates \
  -H "Content-Type: application/json" \
  -d '{"topic": "Should artificial intelligence be regulated by governments?"}'


### Start a Debate

bash
curl -X POST http://localhost:5000/api/debates/DEBATE_ID/start


### Judge a Debate

bash
curl -X POST http://localhost:5000/api/debates/DEBATE_ID/judge \
  -H "Content-Type: application/json" \
  -d '{
    "winner": "The Philosopher",
    "reasoning": "Provided the most compelling ethical arguments"
  }'


## AI Personalities

### The Philosopher
- *Style*: Ethical reasoning and moral frameworks
- *Approach*: Socratic questioning, considers deeper implications

### The Scientist
- *Style*: Evidence-based analysis
- *Approach*: Data-driven arguments, scientific methodology

### The Advocate
- *Style*: Social justice focus
- *Approach*: Human rights perspective, protects vulnerable populations

### The Pragmatist
- *Style*: Practical solutions
- *Approach*: Real-world feasibility, cost-benefit analysis

### The Contrarian
- *Style*: Devil's advocate
- *Approach*: Challenges assumptions, alternative viewpoints

### The Historian
- *Style*: Historical context
- *Approach*: Lessons from the past, pattern recognition

## Configuration

Key configuration options in config.py:

python
# AI Model Settings
DEFAULT_MODEL = "microsoft/DialoGPT-medium"
BACKUP_MODEL = "gpt2"

# Debate Settings
MAX_DEBATE_ROUNDS = 3
MAX_ARGUMENT_LENGTH = 500
DEBATE_TIMEOUT = 300

# Database
MONGODB_URI = "mongodb://localhost:27017/ai_debate_platform"


## Development

### Adding New Personalities

1. Add personality data to DEFAULT_PERSONALITIES in models/personality.py
2. Include unique system prompt and traits
3. Restart application to initialize

### Extending API

1. Add new routes in appropriate blueprint (routes/api.py, etc.)
2. Implement service logic in services/
3. Add validation in utils/helpers.py

### Database Operations

The platform includes utilities for:
- Database health checks
- Index creation
- Backup/restore operations
- Collection statistics

## Monitoring

### Health Checks

bash
curl http://localhost:5000/health


### Platform Statistics

bash
curl http://localhost:5000/api/stats


## Deployment

### Using Docker

dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]


### Using Gunicorn

bash
gunicorn --bind 0.0.0.0:5000 --workers 4 app:app


## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| SECRET_KEY | Flask secret key | your-secret-key-change-in-production |
| MONGODB_URI | MongoDB connection string | mongodb://localhost:27017/ai_debate_platform |
| HUGGINGFACE_API_TOKEN | Hugging Face API token | None |

## Troubleshooting

### Common Issues

1. *MongoDB Connection Failed*
   - Ensure MongoDB is running
   - Check connection string in environment variables

2. *AI Model Loading Issues*
   - Verify internet connection for model downloads
   - Check available memory (models require significant RAM)

3. *Slow Response Times*
   - AI generation can be slow on CPU
   - Consider using GPU-enabled deployment
   - Implement caching for repeated requests

### Logs

Check application logs for detailed error information:
bash
tail -f app.log


## Contributing

1. Fork the repository
2. Create feature branch (git checkout -b feature/amazing-feature)
3. Commit changes (git commit -m 'Add amazing feature')
4. Push to branch (git push origin feature/amazing-feature)
5. Open Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the API documentation

---

Built with ❤ using Flask, MongoDB, and Hugging Face Transformers