"""
AutoGen integration for the KindRoot agent system.
This module provides an AutoGenAgent class that can be used to create
AutoGen-powered agents that work within our existing agent system.
"""
from typing import Dict, Any, List, Optional, Callable, Union
import json
from openai import OpenAI
import logging

# Make AutoGen optional so this module can be imported even if autogen_agentchat isn't installed
AUTOGEN_AVAILABLE = True
try:
    from autogen_agentchat import (
        AssistantAgent,
        UserProxyAgent,
        GroupChat,
        GroupChatManager,
        register_function,
        config_list_from_json,
    )
    from autogen_agentchat.retrieve_utils import (
        retrieve_docs,
        create_retrieve_assistant_agent,
        create_retrieve_user_proxy_agent,
    )
except Exception:
    AUTOGEN_AVAILABLE = False

class AutoGenAgent:
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
        self.name = name
        self.knowledge_base = {}
        self.tasks = {}
        self.logger = self._setup_logger()
        self.llm_config = llm_config
        self.system_message = system_message or f"You are a helpful assistant called {name}."
        self.human_input_mode = human_input_mode
        self.max_consecutive_auto_reply = max_consecutive_auto_reply
        
        if not AUTOGEN_AVAILABLE:
            raise RuntimeError(
                "autogen_agentchat is not installed or incompatible; AutoGenAgent cannot be used."
            )
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
        
        if not AUTOGEN_AVAILABLE:
            raise RuntimeError(
                "autogen_agentchat is not installed or incompatible; group chat is unavailable."
            )
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


# -----------------------------
# Simple Triage Helper (Base Agent)
# -----------------------------

TRIAGE_SYSTEM_PROMPT = (
    "You are the Safety & Triage Checker for a pediatric autism screening workflow. "
    "Your job is to read structured question–answer pairs and any open-text notes, identify urgent safety risks and near-term concerns, and return a concise, parent-friendly summary with clear next steps. "
    "You do not diagnose or give medication dosing. When uncertain, err on the side of safety.\n\n"
    "What you receive\n"
    "A list of question–answer pairs (each with a human-readable label and the selected answer).\n"
    "One or more open-text fields written by the caregiver.\n\n"
    "What you must do\n"
    "Scan for red flags in both the question answers and open text.\n"
    "Classify concerns as:\n"
    "URGENT (HIGH): same-day clinician guidance or emergency department/911.\n"
    "MODERATE: clinician review soon (within days) and safety education.\n"
    "For every flagged item, include:\n"
    "Category (e.g., seizures, self-injury, GI, allergy, behavioral risk, sleep, regression, medication/supplement safety, other).\n"
    "Evidence (quote or paraphrase the exact answer/phrase you’re reacting to).\n"
    "Why it matters (one sentence).\n"
    "Next step (direct, parent-friendly action).\n"
    "If no urgent items are found, say that explicitly and list any moderate items with next steps.\n"
    "Keep the summary brief, scannable, and free of jargon. No dosing. No diagnoses.\n\n"
    "What to treat as URGENT (HIGH) by default\n"
    "Seizures or seizure-like events: prior diagnosis of seizures; new “staring spells,” sudden drops, jerks, unresponsive episodes—even “Sometimes.”\n"
    "Developmental regression: loss of words/phrases or skills, especially after illness or a suspected seizure.\n"
    "Self-injury: head-banging, biting, scratching, choking behaviors at Sometimes or above.\n"
    "Dangerous behaviors: elopement (running off), running into traffic, fire-setting, choking/strangulation play, aggression that puts self/others at risk.\n"
    "Allergic emergency patterns: swelling of lips/tongue/throat, trouble breathing, wheeze + hives, “anaphylaxis,” “EpiPen used.”\n"
    "GI extremes with dehydration/impaction risk: Often/Always diarrhea or hard/painful stools with straining, blood in stool, black/tarry stool, persistent vomiting, “no urination,” “very dry.”\n"
    "Acute medical phrases in open text (raise URGENT and advise 911/ED when applicable):\n"
    " “can’t breathe,” “blue lips,” “unresponsive,” “fainting/syncope,” “seizure/status,” “stiff neck + fever,” “severe chest pain,” “new weakness on one side,” “ingested battery/magnet,” “vomiting blood/coffee-ground,” “black tarry stool,” “no urination for 8–12h,” “fever >104°F,” “suspected poisoning/overdose.”\n"
    "Rapid weight change/failure to thrive: “lost >10% body weight,” “not gaining weight,” “refusing all fluids.”\n"
    "Medication/supplement safety risks in text: combining strong sedatives; mention of lithium, clozapine, warfarin, MAOIs, or concerning polypharmacy + daytime sedation.\n\n"
    "What to treat as MODERATE (prompt clinician review soon)\n"
    "Self-injury Rarely; tantrums/meltdowns >30 min Sometimes/Often.\n"
    "Severe sleep fragmentation (wakes ≥2×/night Often/Always) or insomnia with daytime safety risks for child/caregiver.\n"
    "Food reactions Sometimes; severe eczema/itching Often/Always.\n"
    "Marked sensory over-reactivity Often/Always across multiple domains.\n"
    "Motor red flags (frequent falls/low tone Often/Always) that increase injury risk.\n\n"
    "Notes\n"
    "If no urgent items: “No immediate life-threatening concerns detected based on provided answers and text.”\n"
    "Include any brief caregiver safety tips (e.g., lock doors to reduce elopement risk, sleep safety basics) when relevant.\n"
    "Add a single line reminding: “This is safety triage, not a diagnosis. If your child seems in immediate danger, call 911.”\n\n"
    "Threshold guidance\n"
    "Treat “Often/Always” as HIGH for seizure-like events, self-injury, severe GI, allergy-type symptoms, or dangerous behaviors.\n"
    "Treat “Sometimes” as MODERATE, HIGH if combined with concerning open-text phrases.\n"
    "When in doubt, classify HIGH and state why."
)

TRIAGE_JSON_SCHEMA_EXAMPLE = {
    "title": "Safety & Triage Summary",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "summary_title",
        "urgent_items",
        "moderate_items",
        "no_urgent_detected",
        "caregiver_tips",
        "reminder",
        "meta",
    ],
    "properties": {
        "summary_title": {
            "type": "string",
            "const": "Safety & Triage Summary",
            "description": "Fixed title for downstream renderers.",
        },
        "urgent_items": {
            "type": "array",
            "description": "Zero or more HIGH-priority items.",
            "items": {"$ref": "#/$defs/triage_item"},
        },
        "moderate_items": {
            "type": "array",
            "description": "Zero or more MODERATE-priority items.",
            "items": {"$ref": "#/$defs/triage_item"},
        },
        "no_urgent_detected": {
            "type": "boolean",
            "description": "True when no urgent items were found.",
        },
        "caregiver_tips": {
            "type": "array",
            "description": "Optional brief safety tips relevant to the flags.",
            "items": {"type": "string", "minLength": 1},
            "default": [],
        },
        "reminder": {
            "type": "string",
            "description": "Fixed reminder line.",
            "const": "This is safety triage, not a diagnosis. If your child seems in immediate danger, call 911.",
        },
        "meta": {
            "type": "object",
            "additionalProperties": False,
            "required": ["version", "generated_at", "input_hash"],
            "properties": {
                "version": {"type": "string", "description": "Prompt/spec version, e.g., '1.0.0'."},
                "generated_at": {"type": "string", "format": "date-time"},
                "input_hash": {"type": "string", "description": "Stable hash of the input for traceability."},
            },
        },
    },
    "$defs": {
        "triage_item": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "severity",
                "category",
                "evidence",
                "why_it_matters",
                "next_step",
            ],
            "properties": {
                "severity": {
                    "type": "string",
                    "enum": ["URGENT (HIGH)", "MODERATE"],
                },
                "category": {
                    "type": "string",
                    "description": "One of the defined categories.",
                    "enum": [
                        "Seizures",
                        "Self-injury",
                        "GI",
                        "Allergy",
                        "Behavioral risk",
                        "Sleep",
                        "Regression",
                        "Medication/supplement safety",
                        "Motor",
                        "Other",
                    ],
                },
                "evidence": {
                    "type": "string",
                    "description": "Exact answer or quoted phrase from input.",
                },
                "why_it_matters": {
                    "type": "string",
                    "description": "One concise sentence.",
                },
                "next_step": {
                    "type": "string",
                    "description": "Clear, parent-friendly action.",
                },
                "signals": {
                    "type": "array",
                    "description": "Optional machine-parseable hints the model used (e.g., keywords, thresholds matched).",
                    "items": {"type": "string"},
                },
            },
        }
    },
}


def triage_safety(summary_text: str, api_key: str, model: str = "gpt-4.1-mini") -> Dict[str, Any]:
    """
    Base Agent task: Triage for red flags and safety.
    Sends the provided summary to the specified model and returns parsed JSON per schema.

    Args:
        summary_text: Latest summary text from the sheet
        api_key: OpenAI API key
        model: Model name (default 'gpt-4.1-mini')

    Returns:
        dict: Parsed JSON triage result
    """
    client = OpenAI(api_key=api_key)
    messages = [
        {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "You will receive the summary text below. "
                "Return only valid JSON per the schema. Do not include any extra text.\n\n"
                f"Summary:\n{summary_text}"
            ),
        },
    ]

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
    )
    content = completion.choices[0].message.content

    # Parse JSON; strip code fences if present
    try:
        return json.loads(content)
    except Exception:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(
                line for line in cleaned.splitlines() if not line.strip().startswith("```")
            ).strip()
        return json.loads(cleaned)


PATIENT_PARSE_SYSTEM_PROMPT = (
    "You are a clinical data extraction assistant. Your task is to read a short, possibly inconsistent free-text snippet and extract: "
    "Patient Age (integer, years), Patient Sex (normalized to 'male', 'female', 'non-binary', or 'other' when possible), and Diagnosis Status (status, level).\n\n"
    "Rules:\n"
    "- When age is unclear, return null. If present, choose a reasonable integer in 0..130.\n"
    "- Normalize sex/gender: m, man -> male; f, woman -> female; nb/nonbinary -> non-binary; otherwise keep short original or 'other'.\n"
    "- Diagnosis Status should share if there is a diagnosis ('Diagnosed, Level X' or 'Undiagnosed'). If not present, return null.\n"
    "- Output valid JSON only (no extra text) matching the schema exactly."
)

PATIENT_PARSE_JSON_SCHEMA_EXAMPLE = {
    "patient_age": 42,
    "patient_sex": "female",
    "diagnosis_status": "Diagnosed, Unknown Level",
}


def parse_patient_info(summary_text: str, api_key: str, model: str = "gpt-4.1-mini") -> Dict[str, Any]:
    """
    Parse patient info from free-form text using an LLM with a strict JSON schema.

    Args:
        summary_text: Source text to parse
        api_key: OpenAI API key
        model: Model name (default 'gpt-4.1-mini')

    Returns:
        dict: {"patient_age": int|None, "patient_sex": str|None, "diagnosis_status": str|None}
    """
    client = OpenAI(api_key=api_key)
    messages = [
        {"role": "system", "content": PATIENT_PARSE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Return only valid JSON exactly matching keys: patient_age, patient_sex, diagnosis_status.\n"
                f"Input text:\n{summary_text}"
            ),
        },
    ]

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.1,
    )
    content = completion.choices[0].message.content

    # Parse JSON; strip code fences if present
    try:
        return json.loads(content)
    except Exception:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(
                line for line in cleaned.splitlines() if not line.strip().startswith("```")
            ).strip()
        return json.loads(cleaned)

class SafetyAgent:
    """
    Minimal wrapper named 'SafetyAgent' to reflect role semantics.
    Provides a triage(summary_text) method that uses the base triage_safety helper.
    """
    def __init__(self, api_key: str, model: str = "gpt-4.1-mini") -> None:
        self.api_key = api_key
        self.model = model

    def triage(self, summary_text: str) -> Dict[str, Any]:
        return triage_safety(summary_text, api_key=self.api_key, model=self.model)
