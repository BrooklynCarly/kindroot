"""
AutoGen integration for the KindRoot agent system.
This module provides an AutoGenAgent class that can be used to create
AutoGen-powered agents that work within our existing agent system.
"""
from typing import Dict, Any, List, Optional, Callable, Union
import json
import logging
from autogen_agentchat import (
    AssistantAgent,
    UserProxyAgent,
    GroupChat,
    GroupChatManager,
    register_function,
    config_list_from_json
)
from autogen_agentchat.retrieve_utils import (
    retrieve_docs,
    create_retrieve_assistant_agent,
    create_retrieve_user_proxy_agent
)

from ..base_agent import BaseAgent

class AutoGenAgent(BaseAgent):
    """
    A wrapper around AutoGen's agents to integrate with our agent system.
    """
    
    def __init__(
        self,
        name: str,
        llm_config: Dict[str, Any],
        system_message: Optional[str] = None,
        human_input_mode: str = "NEVER",
        max_consecutive_auto_reply: int = 10,
        **kwargs
    ):
        """
        Initialize an AutoGen agent.
        
        Args:
            name: Name of the agent
            llm_config: Configuration for the language model
            system_message: System message for the agent
            human_input_mode: When to request human input (ALWAYS, TERMINATE, NEVER)
            max_consecutive_auto_reply: Maximum number of consecutive auto-replies
            **kwargs: Additional arguments for BaseAgent
        """
        super().__init__(name=name, **kwargs)
        self.llm_config = llm_config
        self.system_message = system_message or f"You are a helpful assistant called {name}."
        self.human_input_mode = human_input_mode
        self.max_consecutive_auto_reply = max_consecutive_auto_reply
        
        # Initialize the AutoGen agent with v0.4.0 parameters
        self.agent = AssistantAgent(
            name=name,
            system_message=self.system_message,
            llm_config=self.llm_config,
            human_input_mode=self.human_input_mode,
            max_consecutive_auto_reply=self.max_consecutive_auto_reply,
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
            code_execution_config=False,
        )
        
        # Create a user proxy agent for tool use
        self.user_proxy = UserProxyAgent(
            name=f"{name}_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0,
            code_execution_config=False,
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
        )
        
        # Register the process_message function as a task
        self.register_task("process_message", self.process_message)
    
    async def process_message(self, message: str, **kwargs) -> Dict[str, Any]:
        """
        Process a message using the AutoGen agent.
        
        Args:
            message: The message to process
            **kwargs: Additional arguments to pass to the agent
            
        Returns:
            Dictionary containing the agent's response
        """
        try:
            # Initialize a chat between the user proxy and the assistant
            self.user_proxy.initiate_chat(
                self.agent,
                message=message,
                **kwargs
            )
            
            # Get the last message from the chat history
            last_message = self.agent.chat_messages[self.user_proxy][-1]["content"]
            
            return {
                "status": "success",
                "response": last_message,
                "agent": self.name
            }
            
        except Exception as e:
            self.logger.error(f"Error in AutoGen agent: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "agent": self.name
            }
    
    @classmethod
    def create_group_chat(
        cls,
        agents: List['AutoGenAgent'],
        name: str = "group_chat",
        max_round: int = 10,
        **kwargs
    ) -> 'GroupChatManager':
        """
        Create a group chat with multiple AutoGen agents.
        
        Args:
            agents: List of AutoGenAgent instances
            name: Name for the group chat
            max_round: Maximum number of rounds for the chat
            **kwargs: Additional arguments for GroupChat
            
        Returns:
            A GroupChatManager instance
        """
        # Extract the underlying AutoGen agents
        agent_list = [agent.agent for agent in agents]
        
        # Create a group chat with v0.4.0 parameters
        group_chat = GroupChat(
            agents=agent_list,
            messages=[],
            max_round=max_round,
            speaker_selection_method="round_robin",
            allow_repeat_speaker=False,
            **kwargs
        )
        
        # Create a manager for the group chat
        manager = GroupChatManager(
            groupchat=group_chat,
            name=name,
            llm_config=agents[0].llm_config if agents else {},
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
        )
        
        return manager
