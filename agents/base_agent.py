from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

class BaseAgent:
    """
    Base class for all agents in the system.
    Handles common functionality like task processing and knowledge base integration.
    """
    
    def __init__(self, name: str, knowledge_base: Optional[Dict[str, Any]] = None):
        """
        Initialize the base agent.
        
        Args:
            name: A unique name for the agent
            knowledge_base: Optional initial knowledge base
        """
        self.name = name
        self.knowledge_base = knowledge_base or {}
        self.tasks = {}
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """Set up a logger for the agent."""
        logger = logging.getLogger(f"agent.{self.name}")
        logger.setLevel(logging.INFO)
        
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        
        # Add handler to logger
        if not logger.handlers:
            logger.addHandler(ch)
            
        return logger
    
    def add_knowledge(self, key: str, value: Any) -> None:
        """Add or update knowledge in the agent's knowledge base."""
        self.knowledge_base[key] = value
        self.logger.info(f"Updated knowledge base with key: {key}")
    
    def get_knowledge(self, key: str, default: Any = None) -> Any:
        """Retrieve knowledge from the agent's knowledge base."""
        return self.knowledge_base.get(key, default)
    
    def register_task(self, name: str, task_func: callable) -> None:
        """Register a new task that this agent can perform."""
        self.tasks[name] = task_func
        self.logger.info(f"Registered task: {name}")
    
    async def execute_task(self, task_name: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a registered task with the given parameters.
        
        Args:
            task_name: Name of the task to execute
            **kwargs: Parameters to pass to the task function
            
        Returns:
            Dictionary containing task results or error information
        """
        if task_name not in self.tasks:
            error_msg = f"Task '{task_name}' not found in agent '{self.name}'"
            self.logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        
        try:
            self.logger.info(f"Executing task: {task_name}")
            start_time = datetime.utcnow()
            
            # Execute the task
            result = await self.tasks[task_name](**kwargs)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.logger.info(f"Task '{task_name}' completed in {execution_time:.2f}s")
            
            return {
                "status": "success",
                "task": task_name,
                "execution_time": execution_time,
                "result": result
            }
            
        except Exception as e:
            error_msg = f"Error executing task '{task_name}': {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "status": "error",
                "task": task_name,
                "message": str(e)
            }
    
    async def process_input(self, user_input: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process user input and determine the appropriate action.
        This method should be overridden by specific agent implementations.
        
        Args:
            user_input: The input text from the user
            context: Additional context for processing
            
        Returns:
            Dictionary containing the agent's response
        """
        raise NotImplementedError("Subclasses must implement process_input method")
