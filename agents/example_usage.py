"""
Example usage of the KindRoot agent system with sample tasks.
This demonstrates how to create an agent, register tasks, and execute them.
"""
import asyncio
import logging
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from agents.tasks.sample_tasks import register_sample_tasks

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

async def main():
    """Main function to demonstrate agent usage."""
    print("=== KindRoot Agent System Example ===\n")
    
    # Create a new agent
    agent = BaseAgent(name="demo_agent")
    
    # Register sample tasks with the agent
    agent = register_sample_tasks(agent)
    
    # Example 1: Using the greet task
    print("\n--- Example 1: Greeting Task ---")
    greeting_result = await agent.execute_task("greet", name="Alice")
    print(f"Greeting result: {greeting_result}")
    
    # Example 2: Using the calculation task
    print("\n--- Example 2: Calculation Task ---")
    calc_result = await agent.execute_task(
        "calculate",
        operation="multiply",
        numbers=[2, 3, 4]  # 2 * 3 * 4 = 24
    )
    print(f"Calculation result: {calc_result}")
    
    # Example 3: Using the data retrieval task
    print("\n--- Example 3: Data Retrieval Task ---")
    data_result = await agent.execute_task(
        "retrieve_data",
        query="example search",
        limit=3
    )
    print(f"Retrieved {data_result.get('count', 0)} items:")
    for item in data_result.get('results', []):
        print(f"- {item['title']}")
    
    print("\n=== Example Complete ===")

if __name__ == "__main__":
    asyncio.run(main())
