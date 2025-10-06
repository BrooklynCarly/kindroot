"""
Knowledge Base service for loading and managing KB items.
"""
import json
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# KB directory path
KB_DIR = Path(__file__).parent.parent / "data" / "kb"


def load_kb_file(filename: str) -> Dict[str, Any]:
    """
    Load a single KB JSON file.
    
    Args:
        filename: Name of the KB file (e.g., 'observable_symptoms_and_links.json')
    
    Returns:
        Parsed JSON content as dict
    """
    kb_path = KB_DIR / filename
    if not kb_path.exists():
        logger.warning(f"KB file not found: {kb_path}")
        return {}
    
    try:
        with open(kb_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading KB file {filename}: {e}")
        return {}


def load_observable_symptoms_and_links() -> Dict[str, Any]:
    """
    Load the Observable Symptoms and Links KB.
    
    Returns:
        Full KB structure with symptom_mappings and cross_cutting_patterns
    """
    return load_kb_file("observable_symptoms_and_links.json")


def load_functional_medicine_asd() -> Dict[str, Any]:
    """
    Load the Functional Medicine Approaches to ASD KB.
    
    Returns:
        Full KB structure with functional medicine approaches and interventions
    """
    return load_kb_file("functional_medicine_asd.json")


def get_symptom_mappings() -> List[Dict[str, Any]]:
    """
    Get just the symptom mappings from the Observable Symptoms KB.
    
    Returns:
        List of symptom cluster mappings
    """
    kb = load_observable_symptoms_and_links()
    return kb.get("symptom_mappings", [])


def get_cross_cutting_patterns() -> List[Dict[str, Any]]:
    """
    Get cross-cutting patterns that link multiple symptom clusters.
    
    Returns:
        List of pattern objects
    """
    kb = load_observable_symptoms_and_links()
    return kb.get("cross_cutting_patterns", [])


def load_all_kb_items() -> List[Dict[str, Any]]:
    """
    Load all KB items from all files in the KB directory.
    Flattens into a list suitable for passing to the Lead Investigator.
    
    Returns:
        List of KB item dicts
    """
    all_items = []
    
    # Load observable symptoms KB
    obs_kb = load_observable_symptoms_and_links()
    if obs_kb:
        # Add metadata
        all_items.append({
            "type": "kb_metadata",
            "title": obs_kb.get("title", "Observable Symptoms and Links"),
            "description": obs_kb.get("description", ""),
            "version": obs_kb.get("version", "1.0.0"),
        })
        
        # Add symptom mappings
        for mapping in obs_kb.get("symptom_mappings", []):
            all_items.append({
                "type": "symptom_mapping",
                "cluster": mapping.get("symptom_cluster"),
                "observable_symptoms": mapping.get("observable_symptoms", []),
                "possible_causes": mapping.get("possible_underlying_causes", []),
            })
        
        # Add cross-cutting patterns
        for pattern in obs_kb.get("cross_cutting_patterns", []):
            all_items.append({
                "type": "cross_cutting_pattern",
                "pattern": pattern.get("pattern"),
                "hypothesis": pattern.get("hypothesis"),
                "rationale": pattern.get("rationale"),
            })
    
    # Load functional medicine KB
    fm_kb = load_functional_medicine_asd()
    if fm_kb:
        # Add metadata
        all_items.append({
            "type": "kb_metadata",
            "title": fm_kb.get("title", "Functional Medicine Approaches to ASD"),
            "description": fm_kb.get("description", ""),
            "version": fm_kb.get("version", "1.0.0"),
        })
        
        # Add functional medicine approaches
        for approach in fm_kb.get("approaches", []):
            all_items.append({
                "type": "functional_medicine_approach",
                "category": approach.get("category"),
                "description": approach.get("description", ""),
                "interventions": approach.get("interventions", []),
            })
    
    return all_items


def search_kb_by_symptom(symptom_query: str) -> List[Dict[str, Any]]:
    """
    Search KB for symptom clusters matching a query string.
    
    Args:
        symptom_query: Search term (case-insensitive)
    
    Returns:
        List of matching symptom mappings
    """
    query_lower = symptom_query.lower()
    mappings = get_symptom_mappings()
    
    matches = []
    for mapping in mappings:
        # Check cluster name
        if query_lower in mapping.get("symptom_cluster", "").lower():
            matches.append(mapping)
            continue
        
        # Check observable symptoms
        for symptom in mapping.get("observable_symptoms", []):
            if query_lower in symptom.lower():
                matches.append(mapping)
                break
    
    return matches
