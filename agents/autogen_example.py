"""
Example usage of the AutoGen integration with the KindRoot agent system.
This demonstrates how to create and use AutoGen-powered agents.
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import after setting up environment
from agents.autogen.autogen_agent import AutoGenAgent
import autogen_agentchat

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Main function to demonstrate AutoGen agent usage."""
    print("=== KindRoot AutoGen Integration Example ===\n")
    
    # Configuration for the language model
    llm_config = {
        "config_list": [
            {
                "model": "gpt-4",  # or any other model you have access to
                "api_key": os.getenv("OPENAI_API_KEY"),
            }
        ],
        "temperature": 0.7,
        "timeout": 120,
        "cache_seed": 42,  # For reproducibility
        "request_timeout": 600,  # Timeout in seconds
        "max_tokens": 4096,
    }
    
    # Create an AutoGen agent with v0.4.0 parameters
    research_agent = AutoGenAgent(
        name="ResearchAgent",
        llm_config=llm_config,
        system_message="""You are a research assistant. Your role is to help with researching topics 
        and providing detailed, well-structured information. Be thorough in your responses.
        When you have completed your task, end your response with 'TERMINATE'.""",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5,
    )
    
    # Example 1: Process a simple message
    print("\n--- Example 1: Simple Message Processing ---")
    response = await research_agent.process_message(
        "What are the latest advancements in renewable energy?"
    )
    print(f"Response from {response['agent']}: {response['response']}")
    
    # Example 2: Create a group chat with multiple agents
    print("\n--- Example 2: Group Chat with Multiple Agents ---")
    
    # Create a second agent with a different role
    coding_agent = AutoGenAgent(
        name="CodingAgent",
        llm_config=llm_config,
        system_message="""You are a coding assistant. Your role is to help with programming 
        tasks, write code, and explain technical concepts clearly.
        When you have completed your task, end your response with 'TERMINATE'.""",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5,
    )
    
    # Create a group chat with both agents
    group_chat = AutoGenAgent.create_group_chat(
        agents=[research_agent, coding_agent],
        name="ResearchAndCodingGroup",
        max_round=6,  # Increased for better conversation flow
        allow_repeat_speaker=True
    )
    
    # Create a user proxy to interact with the group
    user_proxy = research_agent.user_proxy
    
    # Initiate a group chat
    print("\nInitiating group chat with ResearchAgent and CodingAgent...")
    user_proxy.initiate_chat(
        group_chat,
        message="""Let's work together to create a Python script that analyzes 
        renewable energy trends and visualizes the data."""
    )
    
    print("\n=== Example Complete ===")

if __name__ == "__main__":
    # Check if OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set.")
        print("Please set it with your OpenAI API key to run this example.")
    else:
        asyncio.run(main())
