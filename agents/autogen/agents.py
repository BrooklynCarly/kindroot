from __future__ import annotations
from typing import Any, Dict, List, Optional, Protocol, Sequence, Callable, Union, Literal
from dataclasses import dataclass
import json
import logging
import time
import datetime
import traceback
import os
import requests

try:
    from pydantic import BaseModel, Field, ValidationError
except Exception:  # pydantic v1 fallback if needed
    from pydantic.v1 import BaseModel, Field, ValidationError

try:
    # Make sure you have the correct library installed: pip install google-generativeai
    import google.generativeai as genai
except ImportError:
    raise ImportError("google-generativeai is not installed. Please install it with 'pip install google-generativeai'")
# ... (keep other code)

# ---------- Logging ----------
def get_logger(name: str = "kindroot.agents") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

log = get_logger()

# ---------- Constants & Prompts ----------
TERMINATION_SENTINEL = "TERMINATE"
DEFAULT_MODEL = "gpt-4.1-mini"

TRIAGE_SYSTEM_PROMPT = """You are the Safety & Triage Checker for a pediatric autism screening workflow. "
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
    "Rapid weight change/failure to thrive: “lost >10 percent body weight,” “not gaining weight,” “refusing all fluids.”\n"
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
    "When in doubt, classify HIGH and state why."""
PATIENT_PARSE_SYSTEM_PROMPT = """You are a clinical data extraction assistant. Your task is to read a short, possibly inconsistent free-text snippet and extract: "
    "Patient Age (integer, years), Patient Sex (normalized to 'male', 'female', 'non-binary', or 'other' when possible), Diagnosis Status (status, level), and Top Family Priorities.\n\n"
    "Rules:\n"
    "- When age is unclear, return null. If present, choose a reasonable integer in 0..130.\n"
    "- Normalize sex/gender: m, man -> male; f, woman -> female; nb/nonbinary -> non-binary; otherwise keep short original or 'other'.\n"
    "- Diagnosis Status should share if there is a diagnosis ('Diagnosed, Level X' or 'Undiagnosed'). If not present, return null.\n"
    "- Top Family Priorities: Extract the answer to the question 'which three problems feel the hardest for your child and family right now?' as an array of strings (up to 3 items). If not present, return 'not answered'.\n"
    "- Output valid JSON only (no extra text) matching the schema exactly."""
LEAD_INVESTIGATOR_PROMPT = """You are the Lead Investigator in a functional medicine autism care team.
    You receive:
    - Pre-processed patient data (section scores, individual answers).
    - A set of urgent/moderate safety flags.
    - A general overview of functional medicine as it relates to ASD
    - A mapping of observable symptoms → potential underlying medical issues
    Your task is to generate hypotheses about the most likely underlying biomedical contributors to the child’s symptoms.
    Rules:
    - First, review safety flags (do not ignore urgent items).
    - Map the child’s highest-scoring symptom clusters to plausible root causes; look for crossovers.
    - Rank by:
    + Strength of evidence (number of symptom clusters pointing to it).
    + Severity/risk (e.g., seizures, regression, nutritional deficiencies).
    + Modifiability (can be tested/intervened).
    Output requirements (strict):
+    - Return EXACTLY 3 hypotheses (most useful for parent–clinician conversation). Do NOT diagnose and do NOT give medical advice or dosing.
+    - For each hypothesis return JSON fields:
+      * name (short label)
+      * rationale (why this fits; cite symptom clusters/signals)
+      * confidence (low|moderate|high, optional)
+      * talking_points (2–5 bullets parents can use with their pediatrician)
+      * recommended_tests (0–3) with: name, category, order_type = discuss_with_pediatrician|self_purchase|either, is_at_home (bool?), notes, purchase_url?
+    - Keep language parent-friendly (no jargon), emphasize “for discussion” and “to help decide next steps,” never as a diagnosis."""


ACTIONABLE_STEPS_PROMPT = """You are an intervention planning assistant. Your role is to:
1. Review ALL hypotheses together as a complete picture
2. Identify 2-3 interventions that address multiple root issues
3. Recommend approaches that provide the most comprehensive benefit

# INPUTS
You will receive:
- ALL hypotheses from the Lead Investigator (review as a whole)
- Interventions Knowledge Base (approaches families have tried)

# YOUR TASK
Review the complete hypothesis picture and select 2-3 interventions that:
- Address multiple hypotheses when possible (prioritize multi-system benefits)
- Cover the most important concerns identified
- Are practical for families to implement
- Build on each other logically

For each intervention:
1. **WHY THIS MAY HELP**: Explain how it addresses the overall pattern (mention specific hypotheses)
2. **ADDRESSES MULTIPLE CONCERNS**: List which hypothesis concerns it may help with
3. **WHAT OTHERS HAVE DONE**: Examples from the KB's "how_to_try" field
4. **WHAT FAMILIES TRACKED**: From the KB's "what_to_track" field
5. **COMMON DECISION POINTS**: From the KB's "when_to_stop_or_escalate" field

# MATCHING LOGIC
- Look for interventions whose "who_it_may_help" matches symptoms across MULTIPLE hypotheses
- Prioritize interventions that address foundational issues (gut health, sleep, nutrition)
- Consider synergies: interventions that work well together
- Select EXACTLY 2-3 interventions (no more, no less)
- Order by: (1) Broadest impact, (2) Ease of implementation, (3) Safety profile

# IMPLEMENTATION GUIDANCE
Provide a brief narrative (2-3 sentences) on how to sequence these approaches:
- What to start with first
- What to layer in after 2-3 weeks
- What to consider if initial approaches don't help

# FRAMING GUIDELINES
- Use observational language: "Some families have...", "Others found...", "Many parents report..."
- Avoid prescriptive language: "You should...", "Try this...", "We recommend..."
- Emphasize multi-system benefits when present
- Frame as: "Based on the overall pattern, families have tried..."
- Always include: "Discuss with your pediatrician before starting"

# OUTPUT FORMAT
Return JSON matching the ActionableStepsOutput schema.
- Include EXACTLY 2-3 items in "recommended_approaches"
- Order by priority/impact
- Include implementation_guidance narrative
- Include 2-4 general_notes

# TONE
- Informational and observational, not prescriptive
- Parent-friendly, non-medical language
- Emphasize holistic, multi-system thinking
- Frame as "options to explore" not "what you must do"
"""


RESOURCE_GENERATION_PROMPT = """You are an assistant that uses the provided web-search tool. You do not provide medical advice or diagnoses. Your output is strictly informational and must be verifiable via cited official sources. Do not collect or output user PII. Do not contact providers. Exclude sponsored results and paywalled directories. Prefer .gov or official state domains for Part C programs.

# METADATA
- **Title**: Early Intervention Resource Finder
- **Version**: 1.0
- **Purpose**: Guide an LLM to find early intervention resources and nearby therapy providers using web search, given a U.S. ZIP code.
- **Disclaimer**: Information is purely for informational purposes and does not constitute a recommendation. It is for navigation and referral support; verify against official sources.

# INPUTS
- `zip_code`: string (required)
- `city`: string (optional, can be inferred)
- `state`: string (optional, can be inferred)

# HIGH-LEVEL TASK
Given a patient ZIP code, identify the state Early Intervention (Part C) program  and nearby providers within a distance determined by metro vs non-metro classification.

# STEPS

**Step 1: State and EI Site**
- **Goal**: Identify the state for the ZIP code and the official Early Intervention website.
- **Actions**: Map `zip_code` to state and city. Search for the official state Early Intervention website. Verify the site is authoritative (prefer .gov or official state domain).
- **Search Queries**: `[STATE] early intervention program`, `[STATE] Part C early intervention services`
- **Outputs**: `state`, `ei_program` (with `website_url`, `contact_phone`, `contact_email`)

**Step 2: Metro Classification**
- **Goal**: Determine if the ZIP code is in a Metropolitan Statistical Area (MSA).
- **Actions**: Search to determine metropolitan status.
- **Search Queries**: `[ZIP] metropolitan statistical area`, `[CITY] [STATE] metropolitan area`
- **Decision**: If part of an MSA -> `metropolitan = true`.
- **Outputs**: `metropolitan` (boolean), `supporting_source` (URL)

**Step 3: Search Radius**
- **Goal**: Set search radius based on metro status.
- **Decision**: `metropolitan === true` -> `radius_miles = 3`, `metropolitan === false` -> `radius_miles = 20`.
- **Output**: `radius_miles` (number)

**Step 4: Developmental Pediatrics**
- **Goal**: Identify nearby pediatricians (preferably with developmental pediatrics or autism experience).
- **Search Queries**: `developmental pediatrician [CITY] [STATE]`, `pediatrician autism [ZIP]`
- **Filtering**: Ratings ≥ 4.2, Reviews ≥ 3, within radius, pediatric focus; list up to 5.
- **Output**: `pediatricians` (array of `Provider` objects)

**Step 5: Behavioral/ABA Search**
- **Goal**: Find Behavioral/ABA therapy providers within the radius, using Google business results.
- **Search Queries**: `ABA therapy [CITY] [STATE]`, `behavioral therapist autism [ZIP]`
- **Filtering**: Ratings >= 4.2, Reviews >= 3, max 5 results, within radius, autism/developmental specialty.
- **Output**: `behavioral_providers` (array of `Provider` objects)

**Step 6: Speech Search**
- **Goal**: Find Speech therapy providers within the radius, using Google business results.
- **Search Queries**: `speech therapist [CITY] [STATE]`, `speech language pathologist [ZIP]`
- **Filtering**: Ratings >= 4.2, Reviews >= 3, max 5 results, within radius, pediatric/developmental focus.
- **Output**: `speech_providers` (array of `Provider` objects)

# OUTPUT FORMAT
Return ONLY a single valid JSON object matching the `SummaryReport` schema. Do not include any other text, comments, or markdown.

```json
{
  "summary_report": {
    "patient_location": {
      "zip_code": "string",
      "city": "string",
      "state": "string"
    },

    "state_early_intervention_program": {
      "website": "string",
      "contact_phone": "string|null",
      "contact_email": "string|null"
    },
    
    "pediatricians": [
      {
        "name": "string",
        "rating": 4.8,
        "review_count": 25,
        "distance_miles": 1.2,
        "address": "string",
        "phone": "string|null",
        "website": "string|null",
        "specialties": ["string"],
      }
    ],
    "behavioral_providers": [
      {
        "name": "string",
        "rating": 4.8,
        "review_count": 25,
        "distance_miles": 1.2,
        "address": "string",
        "phone": "string|null",
        "website": "string|null",
        "specialties": ["string"],
      }
    ],
    "speech_providers": [
      {
        "name": "string",
        "rating": 4.8,
        "review_count": 25,
        "distance_miles": 1.2,
        "address": "string",
        "phone": "string|null",
        "website": "string|null",
        "specialties": ["string"],
      }
    ],
    "additional_notes": ["string"]
  }
}
```
"""

# ---------- Schemas ----------
class TriageItem(BaseModel):
    severity: Literal["URGENT (HIGH)", "MODERATE"]
    category: str
    evidence: str
    why_it_matters: str
    next_step: str
    signals: Optional[List[str]] = None

class TriageMeta(BaseModel):
    version: str
    generated_at: str
    input_hash: str

class TriageResult(BaseModel):
    summary_title: Literal["Safety & Triage Summary"] = "Safety & Triage Summary"
    urgent_items: List[TriageItem]
    moderate_items: List[TriageItem]
    no_urgent_detected: bool
    caregiver_tips: List[str] = []
    reminder: Literal["This is safety triage, not a diagnosis. If your child seems in immediate danger, call 911."] = "This is safety triage, not a diagnosis. If your child seems in immediate danger, call 911."
    meta: TriageMeta
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary_title": "Safety & Triage Summary",
                    "urgent_items": [
                        {
                            "severity": "URGENT (HIGH)",
                            "category": "Seizures",
                            "evidence": "Parent reports 'staring spells' this week",
                            "why_it_matters": "Possible seizure-like events require same-day clinician guidance.",
                            "next_step": "Call your pediatrician today or go to urgent care if symptoms persist.",
                            "signals": ["staring spells", "new onset"]
                        }
                    ],
                    "moderate_items": [],
                    "no_urgent_detected": False,
                    "caregiver_tips": ["Lock doors to reduce elopement risk."],
                    "reminder": "This is safety triage, not a diagnosis. If your child seems in immediate danger, call 911.",
                    "meta": {
                        "version": "1.0.0",
                        "generated_at": "2025-10-05T17:31:00Z",
                        "input_hash": "sha256:abc123..."
                    }
                }
                ]
        }
    }

class PatientParse(BaseModel):
    patient_age: Optional[int]
    patient_sex: Optional[str]
    diagnosis_status: Optional[str]
    top_family_priorities: Optional[List[str]] = None  # Top 3 problems that feel hardest
    model_config = {
        "json_schema_extra": {
            "examples": [
                # Typical diagnosed case
                {
                    "patient_age": 6,
                    "patient_sex": "male",
                    "diagnosis_status": "Diagnosed, Level 2",
                    "top_family_priorities": ["Sleep issues", "Meltdowns", "Picky eating"]
                },
                # Undiagnosed / ambiguous inputs
                {
                    "patient_age": None,
                    "patient_sex": "other",
                    "diagnosis_status": "Undiagnosed",
                    "top_family_priorities": None
                },
                # Minimal shape (all unknown)
                {
                    "patient_age": None,
                    "patient_sex": None,
                    "diagnosis_status": None,
                    "top_family_priorities": None
                }
            ]
        }
    }

class InvestigatorHypothesis(BaseModel):
    name: str
    rationale: str
    confidence: Optional[str] = None
    talking_points: List[str] = []
    class TestItem(BaseModel):
        name: str
        category: Optional[str] = None          # e.g., "blood", "stool", "imaging"
        order_type: Literal["discuss_with_pediatrician","self_purchase","either"] = "discuss_with_pediatrician"
        is_at_home: Optional[bool] = None
        notes: Optional[str] = None
        purchase_url: Optional[str] = None
    recommended_tests: List[TestItem] = []
class InvestigatorOutput(BaseModel):
    hypotheses: List[InvestigatorHypothesis]
    # uncertainties: List[str]
    next_steps: List[str]
    meta: Dict[str, Any]
    model_config = {
        "json_schema_extra": {
            "examples": [
                # Rich example with two hypotheses
                    {
                    "hypotheses": [
                        {
                            "name": "Obstructive Sleep Apnea (OSA)",
                            "rationale": "Frequent night waking and snoring; sleep fragmentation can drive daytime dysregulation.",
                            "confidence": "moderate",
                            "talking_points": [
                                "Describe sleep patterns and snoring to your pediatrician.",
                                "Ask whether ENT evaluation is appropriate."
                            ],
                            "recommended_tests": [
                                {"name": "Pediatric sleep study (polysomnography)", "category":"sleep", "order_type":"discuss_with_pediatrician", "notes":"Confirms OSA severity"}
                            ]
                        },
                        {
                            "name": "Iron Deficiency",
                            "rationale": "History of anemia and sleep issues; iron deficiency can worsen sleep quality and attention.",
                            "confidence": "low",
                            "talking_points": [
                                "Describe sleep patterns and snoring to your pediatrician.",
                                "Ask whether ENT evaluation is appropriate."
                            ],
                            "recommended_tests": [
                                {"name": "Pediatric sleep study (polysomnography)", "category":"sleep", "order_type":"discuss_with_pediatrician", "notes":"Confirms OSA severity"}
                            ]
                        }
                    ],
                    # "uncertainties": [
                    #     "Are there witnessed pauses in breathing or gasping at night?",
                    #     "Recent ferritin and CBC values are unavailable."
                    # ],
                    "next_steps": [
                        "Discuss a pediatric sleep evaluation; consider ENT review for tonsils/adenoids.",
                        "Order labs: CBC, ferritin, iron studies, CRP.",
                        "Share sleep hygiene guidance; reduce evening screen exposure."
                    ],
                    "meta": {
                        "version": "1.0.0",
                        "source": "LeadInvestigatorService",
                        "generated_at": "2025-10-05T18:10:00Z"
                    }
                },
                # Minimal valid example
                {
                    "hypotheses": [],
                    "next_steps": [],
                    "meta": {"version": "1.0.0"}
                }
                        ]
                    }
    }

# Actionable Steps Models
class ActionableIntervention(BaseModel):
    """Single intervention matched to the overall hypothesis picture"""
    intervention_id: str
    intervention_name: str
    category: str  # e.g., "Diet", "Supplement", "Lifestyle"
    
    # Why this intervention (holistic view)
    why_this_may_help: str  # How it addresses the overall pattern
    addresses_multiple_concerns: List[str]  # Which hypothesis concerns it may help with
    
    # What others have done
    what_others_have_done: List[str]
    what_families_tracked: List[str]
    common_decision_points: List[str]
    
    # Optional context
    considerations: Optional[List[str]] = None
    important_notes: Optional[str] = None

class ActionableStepsOutput(BaseModel):
    """Holistic intervention plan based on all hypotheses (2-3 interventions max)"""
    recommended_approaches: List[ActionableIntervention] = Field(..., max_length=3)
    implementation_guidance: str  # How to sequence/prioritize these approaches
    general_notes: List[str]  # Overall observations and reminders
    
    meta: Dict[str, Any]
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "recommended_approaches": [
                        {
                            "intervention_id": "diet_gfcf",
                            "intervention_name": "Gluten/Casein-free baseline",
                            "category": "Diet",
                            "why_this_may_help": "Several concerns including GI issues and sleep disruption may be linked to food sensitivities. This addresses gut-brain axis dysfunction.",
                            "addresses_multiple_concerns": [
                                "GI symptoms (constipation, reflux)",
                                "Sleep fragmentation",
                                "Behavioral dysregulation"
                            ],
                            "what_others_have_done": [
                                "Replaced breads/pastas with certified gluten-free alternatives",
                                "Swapped dairy milk/yogurt with fortified non-dairy options"
                            ],
                            "what_families_tracked": [
                                "Stool consistency and frequency",
                                "Sleep quality and night wakings",
                                "Daytime behavior and focus"
                            ],
                            "common_decision_points": [
                                "No change after 3-4 weeks → consider additional GI workup",
                                "Partial improvement → continue and layer in omega-3"
                            ],
                            "considerations": [
                                "Certified gluten-free products",
                                "Fortified alternative milks with calcium/vitamin D"
                            ],
                            "important_notes": "Consult with pediatrician before making dietary changes"
                        }
                    ],
                    "implementation_guidance": "Many families start with dietary changes as foundational support. After 2-3 weeks, consider adding targeted supplements based on response.",
                    "general_notes": [
                        "Always discuss with your pediatrician before starting new interventions",
                        "Introduce one change at a time when possible to track effects",
                        "Results vary; what works for one family may not work for another"
                    ],
                    "meta": {
                        "version": "1.0.0",
                        "generated_at": "2025-11-05T18:00:00Z"
                    }
                }
            ]
        }
    }

# Resource Generation Models
class Provider(BaseModel):
    name: str
    rating: float = Field(..., ge=0, le=5)
    review_count: Optional[int] = Field(None, ge=0)
    distance_miles: float = Field(..., ge=0)
    address: str
    phone: Optional[str] = None
    website: Optional[str] = None
    specialties: Optional[List[str]] = None

class StateEIRProgram(BaseModel):
    website: str
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None

class PatientLocation(BaseModel):
    zip_code: str
    city: str
    state: str

class SummaryReport(BaseModel):
    patient_location: PatientLocation
    metropolitan_status: Optional[Literal["Yes", "No"]] = None
    search_radius_miles: Optional[int] = None
    state_early_intervention_program: StateEIRProgram
    pediatricians: Optional[List[Provider]] = None
    behavioral_providers: List[Provider]
    speech_providers: List[Provider]
    additional_notes: Optional[List[str]] = None

class ResourceFinderResult(BaseModel):
    summary_report: SummaryReport

# ---------- Utilities ----------
def strip_code_fences(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        lines = [ln for ln in s.splitlines() if not ln.strip().startswith("```")]
        return "\n".join(lines).strip()
    return s

def parse_json_or_raise(text: str) -> Dict[str, Any]:
    """Parse JSON from text, handling markdown code fences and providing better error messages."""
    import re
    
    # First try direct JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError as e1:
        # Try stripping code fences and parse again
        cleaned = strip_code_fences(text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e2:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\n(.*?)\n```', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError as e3:
                    log.error(f"Failed to parse JSON after markdown extraction: {e3}")
                    log.debug(f"Problematic text: {text}")
                    raise ValueError(f"Invalid JSON in markdown code block: {e3}") from e3
            
            # If we get here, all parsing attempts failed
            log.error(f"Failed to parse JSON. First error: {e1}, Second error: {e2}")
            log.debug(f"Problematic text: {text}")
            raise ValueError(f"Invalid JSON response. Please ensure the response is valid JSON. Error: {e2}")

# ---------- LLM Client Interface ----------
class ChatLLM(Protocol):
    def chat(self, *, model: str, messages: Sequence[Dict[str, str]], temperature: float = 0.2) -> str: ...

# Concrete OpenAI implementation
class OpenAIChat(ChatLLM):
    def __init__(self, api_key: str):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)

    def chat(self, *, model: str, messages: Sequence[Dict[str, str]], temperature: float = 0.2) -> str:
        resp = self._client.chat.completions.create(model=model, messages=messages, temperature=temperature)
        return resp.choices[0].message.content


# ---------- Retry wrapper ----------
def with_retries(fn: Callable[[], str], attempts: int = 3, base_delay: float = 0.5) -> str:
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            if i == attempts - 1:
                raise
            sleep = base_delay * (2 ** i)
            log.warning(f"LLM call failed (attempt {i+1}/{attempts}): {e}; retrying in {sleep:.1f}s")
            time.sleep(sleep)
    raise RuntimeError("Unreachable retry state")

# ---------- High-level tasks ----------
@dataclass
class TriageService:
    llm: ChatLLM
    model: str = DEFAULT_MODEL

    def run(self, summary_text: str) -> TriageResult:
        # Get example from model config
        examples = TriageResult.model_config.get("json_schema_extra", {}).get("examples", [])
        example_str = json.dumps(examples[0], indent=2) if examples else ""
        
        schema_instruction = f"""Return ONLY valid JSON with this EXACT structure (no extra text, no markdown):

EXAMPLE OUTPUT:
{example_str}

REQUIRED FIELDS:
- summary_title: must be "Safety & Triage Summary"
- urgent_items: array (can be empty [])
- moderate_items: array (can be empty [])
- no_urgent_detected: boolean
- caregiver_tips: array of strings (can be empty [])
- reminder: must be "This is safety triage, not a diagnosis. If your child seems in immediate danger, call 911."
- meta: object with version, generated_at, input_hash"""
        
        messages = [
            {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
            {"role": "user", "content": f"{schema_instruction}\n\nSummary to analyze:\n{summary_text}"},
        ]
        content = with_retries(lambda: self.llm.chat(model=self.model, messages=messages, temperature=0.2))
        payload = parse_json_or_raise(content)
        
        # Log the raw response for debugging
        log.info(f"Triage LLM raw response: {json.dumps(payload, indent=2)}")
        
        try:
            return TriageResult.model_validate(payload)
        except ValidationError as ve:
            log.error(f"Triage JSON failed validation: {ve}\nRaw payload: {json.dumps(payload, indent=2)}")
            raise

@dataclass
class PatientParseService:
    llm: ChatLLM
    model: str = DEFAULT_MODEL

    def run(self, summary_text: str) -> PatientParse:
        # Get JSON schema from Pydantic model
        schema = PatientParse.model_json_schema()
        schema_str = json.dumps(schema, indent=2)
        
        messages = [
            {"role": "system", "content": PATIENT_PARSE_SYSTEM_PROMPT},
            {"role": "user", "content": f"Return ONLY valid JSON matching this exact schema:\n{schema_str}\n\nInput text:\n{summary_text}"},
        ]
        content = with_retries(lambda: self.llm.chat(model=self.model, messages=messages, temperature=0.1))
        payload = parse_json_or_raise(content)
        try:
            return PatientParse.model_validate(payload)
        except ValidationError as ve:
            log.error(f"Patient parse JSON failed validation: {ve}\nRaw: {payload}")
            raise

@dataclass
class LeadInvestigatorService:
    llm: ChatLLM
    model: str = DEFAULT_MODEL

    def run(self, *, patient_info: PatientParse, triage_result: TriageResult, kb_items: Optional[List[Dict[str, Any]]] = None) -> InvestigatorOutput:
        # Get example from model config
        examples = InvestigatorOutput.model_config.get("json_schema_extra", {}).get("examples", [])
        example_str = json.dumps(examples[0], indent=2) if examples else ""
        
        schema_instruction = f"""Return ONLY valid JSON with this EXACT structure (no extra text, no markdown):

EXAMPLE OUTPUT:
{example_str}

REQUIRED FIELDS:
- hypotheses: array of objects with name, rationale, confidence (optional)
- uncertainties: array of strings
- next_steps: array of strings
- meta: object with version and any other metadata"""
        
        payload = {
            "patient_info": patient_info.model_dump(),
            "triage_result": triage_result.model_dump(),
            "kb_items": kb_items or [],
        }
        
        messages = [
            {"role": "system", "content": LEAD_INVESTIGATOR_PROMPT},
            {"role": "user", "content": f"{schema_instruction}\n\nInput data to analyze:\n{json.dumps(payload, indent=2)}"},
        ]
        content = with_retries(lambda: self.llm.chat(model=self.model, messages=messages, temperature=0.2))
        data = parse_json_or_raise(content)
        
        # Log the raw response for debugging
        log.info(f"Investigator LLM raw response: {json.dumps(data, indent=2)}")
        
        try:
            return InvestigatorOutput.model_validate(data)
        except ValidationError as ve:
            log.error(f"Investigator JSON failed validation: {ve}\nRaw payload: {json.dumps(data, indent=2)}")
            raise

@dataclass
class ResourceGenerationService:
    llm: ChatLLM
    # Use an OpenAI chat model by default; aligned with other services
    model: str = "gpt-4.1-mini"
    
    def extract_zipcode(self, summary: str) -> Optional[str]:
        """Extract zipcode from patient summary if present."""
        import re
        # Look for 5-digit zipcode pattern
        zip_match = re.search(r'\b\d{5}\b', summary)
        return zip_match.group(0) if zip_match else None
    
    def generate_resources(self, summary: str) -> Dict[str, Any]:
        """
        Generate local resources based on zipcode in summary.

        Args:
            summary: Patient summary text that may contain a zipcode

        Returns:
            Dict containing resources or error information
        """
        zipcode = self.extract_zipcode(summary)
        if not zipcode:
            return {"status": "skipped", "reason": "No zipcode found in summary"}

        try:
            # Prepare the prompt without using .format() to avoid brace parsing issues
            user_prompt = f"{RESOURCE_GENERATION_PROMPT}\n\nUse this ZIP code for the task: {zipcode}"

            messages = [
                {"role": "user", "content": user_prompt}
            ]

            # Log the request for debugging
            log.debug(f"Sending request to LLM with zipcode: {zipcode}")
            
            # Get response from LLM
            response = self.llm.chat(
                model=self.model,
                messages=messages,
                temperature=0.2
            )
            
            # Log the raw response for debugging
            log.debug(f"Raw LLM response: {response}")

            # Parse and validate the response
            try:
                response_data = parse_json_or_raise(response)

                # Normalize possible shapes from LLM
                if isinstance(response_data, dict):
                    # If camelCase key is used
                    if "summaryReport" in response_data and "summary_report" not in response_data:
                        response_data = {"summary_report": response_data["summaryReport"]}
                    # If a bare SummaryReport object is returned, wrap it
                    elif "summary_report" not in response_data and all(k in response_data for k in [
                        "patient_location", "metropolitan_status", "search_radius_miles",
                        "state_early_intervention_program","behavioral_providers",
                        "speech_providers"
                    ]):
                        response_data = {"summary_report": response_data}

                validated_response = ResourceFinderResult.model_validate(response_data)
                
                # Convert back to dict for API response
                result = validated_response.model_dump()
                result["status"] = "success"
                return result
                
            except (json.JSONDecodeError, ValueError) as je:
                log.error(f"Failed to parse JSON response: {je}")
                log.debug(f"Response that failed to parse: {response}")
                return {
                    "status": "error", 
                    "message": f"Failed to parse resource data: {str(je)}",
                    "raw_response": response[:500]  # Include first 500 chars for debugging
                }
                
            except ValidationError as ve:
                log.error(f"Response validation failed: {ve}")
                log.debug(f"Response that failed validation: {response}")
                return {
                    "status": "error", 
                    "message": f"Invalid resource data format: {str(ve)}",
                    "raw_response": response[:500]  # Include first 500 chars for debugging
                }
            
        except Exception as e:
            error_msg = f"Resource generation failed: {str(e)}"
            log.error(error_msg, exc_info=True)
            return {
                "status": "error", 
                "message": error_msg,
                "error_type": e.__class__.__name__
            }


@dataclass
class ActionableStepsService:
    """Generate holistic intervention recommendations based on all hypotheses"""
    llm: ChatLLM
    model: str = "gpt-4o-mini"
    
    def run(
        self,
        hypotheses: InvestigatorOutput,
        interventions_kb: List[Dict[str, Any]]
    ) -> ActionableStepsOutput:
        """
        Generate holistic actionable steps from ALL hypotheses.
        
        Args:
            hypotheses: Complete output from LeadInvestigatorService
            interventions_kb: Interventions from knowledge base
            
        Returns:
            Unified intervention plan addressing multiple concerns (2-3 interventions)
        """
        # Get example from model config
        examples = ActionableStepsOutput.model_config.get("json_schema_extra", {}).get("examples", [])
        example_str = json.dumps(examples[0], indent=2) if examples else ""
        
        schema_instruction = f"""Return ONLY valid JSON with this EXACT structure (no extra text, no markdown):

EXAMPLE OUTPUT:
{example_str}

REQUIRED FIELDS:
- recommended_approaches: array of intervention objects (2-3 items max)
- implementation_guidance: string
- general_notes: array of strings
- meta: object with version and metadata"""
        
        # Include ALL hypotheses
        hypotheses_text = json.dumps(hypotheses.model_dump(), indent=2)
        
        # Include full interventions KB
        interventions_text = json.dumps(interventions_kb, indent=2)
        
        user_content = f"""{ACTIONABLE_STEPS_PROMPT}

{schema_instruction}

# COMPLETE HYPOTHESIS PICTURE
{hypotheses_text}

# INTERVENTIONS KNOWLEDGE BASE
{interventions_text}

Generate a holistic intervention plan with 2-3 approaches now:"""
        
        messages = [
            {"role": "user", "content": user_content}
        ]
        
        content = with_retries(lambda: self.llm.chat(model=self.model, messages=messages, temperature=0.2))
        data = parse_json_or_raise(content)
        
        try:
            return ActionableStepsOutput.model_validate(data)
        except ValidationError as ve:
            log.error(f"ActionableSteps JSON failed validation: {ve}\nRaw payload: {json.dumps(data, indent=2)}")
            raise


# ---------- AutoGen Adapter (optional) ----------
class AutoGenAdapter:
    """
    Optional adapter that wraps autogen_agentchat agents and exposes a simple process() API.
{{ ... }}
    """
    def __init__(
        self,
        name: str,
        llm_config: Dict[str, Any],
        system_message: Optional[str] = None,
        human_input_mode: str = "NEVER",
        max_consecutive_auto_reply: int = 10,
    ):
        try:
            from autogen_agentchat import AssistantAgent, UserProxyAgent
        except Exception as e:
            raise RuntimeError("autogen_agentchat not available") from e

        self._AssistantAgent = AssistantAgent
        self._UserProxyAgent = UserProxyAgent
        self.name = name
        self.system_message = system_message or f"You are a helpful assistant called {name}."
        self.llm_config = llm_config

        def is_term(msg: Dict[str, Any]) -> bool:
            return str(msg.get("content", "")).rstrip().endswith(TERMINATION_SENTINEL)

        self.assistant = self._AssistantAgent(
            name=name,
            system_message=self.system_message,
            llm_config=self.llm_config,
            human_input_mode=human_input_mode,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            is_termination_msg=is_term,
            code_execution_config=False,
        )
        self.user_proxy = self._UserProxyAgent(
            name=f"{name}_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0,
            code_execution_config=False,
            is_termination_msg=is_term,
        )

    def process(self, message: str, **kwargs) -> Dict[str, Any]:
        # AutoGen is sync; call directly
        self.user_proxy.initiate_chat(self.assistant, message=message, **kwargs)
        last = self.assistant.chat_messages[self.user_proxy][-1]["content"]
        return {"status": "success", "response": last, "agent": self.name}

    @staticmethod
    def create_group_chat(managed_agents: List["AutoGenAdapter"], name: str = "group_chat", max_round: int = 10, **kwargs):
        try:
            from autogen_agentchat import GroupChat, GroupChatManager
        except Exception as e:
            raise RuntimeError("autogen_agentchat not available") from e

        if not managed_agents:
            raise ValueError("Need at least one agent")
        agents = [a.assistant for a in managed_agents]
        group = GroupChat(
            agents=agents,
            messages=[],
            max_round=max_round,
            speaker_selection_method=kwargs.pop("speaker_selection_method", "round_robin"),
            allow_repeat_speaker=kwargs.pop("allow_repeat_speaker", False),
            **kwargs,
        )
        manager = GroupChatManager(
            groupchat=group,
            name=name,
            llm_config=managed_agents[0].llm_config,
            is_termination_msg=lambda x: str(x.get("content", "")).rstrip().endswith(TERMINATION_SENTINEL),
        )
        return manager
