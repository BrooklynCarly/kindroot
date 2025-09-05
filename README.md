# KindRoot

A flexible agent system for processing data from Google Sheets with a Node.js frontend and Python backend, featuring AutoGen-powered agents for advanced AI capabilities.

## Project Structure

```
kindroot/
├── backend/              # Python FastAPI backend
│   ├── app/             
│   │   ├── __init__.py
│   │   ├── main.py      # FastAPI application
│   │   └── config.py    # Configuration settings
│   ├── requirements.txt
│   └── .env.example
├── frontend/            # Node.js frontend (to be implemented)
│   └── src/
│       ├── components/
│       └── pages/
├── agents/              # Agent implementations
│   ├── __init__.py
│   ├── base_agent.py    # Base agent class
│   ├── example_usage.py # Demo of agent usage
│   ├── autogen/         # AutoGen integration
│   │   ├── __init__.py
│   │   └── autogen_agent.py
│   └── tasks/           # Task modules
│       ├── __init__.py
│       └── sample_tasks.py
├── knowledge/           # Knowledge base files
├── tests/               # Test files
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 16+ (for frontend, coming soon)
- Google Cloud Platform account with Google Sheets API enabled (for future integration)

### Backend Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

2. Install backend dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Run the backend server:
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

The API will be available at http://localhost:8000

### Running the Agent Example

To see the agent system in action with sample tasks:

```bash
python agents/example_usage.py
```

## Agent System

The agent system is designed to be extensible and modular. Key components:

- **BaseAgent**: The foundation for all agents, providing common functionality
- **Tasks**: Individual units of work that can be registered with an agent
- **Knowledge Base**: Storage for agent knowledge and context

### Example Usage

See `agents/example_usage.py` for a demonstration of how to create an agent and register/execute tasks.

## AutoGen Integration

The project includes integration with [AutoGen AgentChat](https://microsoft.github.io/autogen/), a framework for developing LLM applications with multiple agents that can work together to solve tasks. We use the `autogen-agentchat` package which is the current recommended way to use AutoGen.

### Features

- **AutoGenAgent**: A wrapper around AutoGen's agents that integrates with our base agent system
- **Group Chat**: Support for multi-agent conversations
- **Task Management**: Seamlessly integrate AutoGen agents with existing task system

### Example Usage

```python
from agents.autogen import AutoGenAgent

# Create an AutoGen agent
agent = AutoGenAgent(
    name="ResearchAgent",
    llm_config={
        "config_list": [{"model": "gpt-4", "api_key": "your-api-key"}],
        "temperature": 0.7,
    },
    system_message="You are a helpful research assistant."
)

# Use the agent
response = await agent.process_message("What are the latest advancements in AI?")
print(response["response"])
```

Run the example:
```bash
# First install the dependencies
pip install -r backend/requirements.txt

# Then run the example
OPENAI_API_KEY=your-api-key python agents/autogen_example.py
```

## Next Steps

1. Implement Google Sheets integration
2. Set up the Node.js frontend
3. Create specific agent implementations for your use case
4. Implement the review workflow
5. Add tests
6. Extend AutoGen integration with custom tools and capabilities

## License

[Your License Here]
