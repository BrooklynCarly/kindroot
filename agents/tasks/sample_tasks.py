"""
Sample tasks for the KindRoot agent system.
These demonstrate the structure for creating and registering tasks.
"""
import asyncio
from typing import Dict, Any, List
import random

# Example task: Simple greeting
def create_greeting_task():
    """Create a task that generates a greeting."""
    async def greet(name: str = "there") -> Dict[str, str]:
        """Generate a greeting.
        
        Args:
            name: Name of the person to greet
            
        Returns:
            Dictionary containing the greeting
        """
        greetings = [
            f"Hello, {name}! How can I help you today?",
            f"Hi {name}! What can I do for you?",
            f"Greetings {name}! How may I assist you?",
            f"Hey {name}! What brings you here today?"
        ]
        return {"message": random.choice(greetings)}
    
    return greet

# Example task: Simple math calculation
def create_calculation_task():
    """Create a task that performs basic arithmetic."""
    async def calculate(operation: str, numbers: List[float]) -> Dict[str, Any]:
        """Perform a calculation.
        
        Args:
            operation: The operation to perform (add, subtract, multiply, divide)
            numbers: List of numbers to operate on
            
        Returns:
            Dictionary containing the result or an error message
        """
        if not numbers:
            return {"error": "No numbers provided"}
            
        operation = operation.lower()
        
        try:
            if operation == "add":
                result = sum(numbers)
            elif operation == "subtract":
                result = numbers[0] - sum(numbers[1:])
            elif operation == "multiply":
                result = 1
                for num in numbers:
                    result *= num
            elif operation == "divide":
                if 0 in numbers[1:]:
                    return {"error": "Cannot divide by zero"}
                result = numbers[0]
                for num in numbers[1:]:
                    result /= num
            else:
                return {"error": f"Unknown operation: {operation}"}
                
            return {
                "operation": operation,
                "numbers": numbers,
                "result": result
            }
            
        except Exception as e:
            return {"error": f"Calculation error: {str(e)}"}
    
    return calculate

# Example task: Mock data retrieval
def create_data_retrieval_task():
    """Create a task that simulates retrieving data."""
    async def retrieve_data(query: str, limit: int = 5) -> Dict[str, Any]:
        """Simulate retrieving data based on a query.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            
        Returns:
            Dictionary containing the search results
        """
        # Simulate network/database delay
        await asyncio.sleep(0.5)
        
        # Mock data - in a real app, this would query a database or API
        mock_data = [
            {"id": i, "title": f"Result {i} for '{query}'", "content": f"This is sample content for result {i}"}
            for i in range(1, limit + 1)
        ]
        
        return {
            "query": query,
            "count": len(mock_data),
            "results": mock_data
        }
    
    return retrieve_data

# Example task registration function
def register_sample_tasks(agent):
    """Register all sample tasks with the agent.
    
    Args:
        agent: The agent instance to register tasks with
    """
    agent.register_task("greet", create_greeting_task())
    agent.register_task("calculate", create_calculation_task())
    agent.register_task("retrieve_data", create_data_retrieval_task())
    
    return agent
