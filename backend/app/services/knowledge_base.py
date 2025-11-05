"""
Knowledge Base service for loading and managing KB items.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

# KB directory path
KB_DIR = Path(__file__).parent.parent / "data" / "kb"


@lru_cache(maxsize=None)
def load_kb_file(filename: str) -> Dict[str, Any]:
    """
    Load a single KB JSON file with caching.
    
    Args:
        filename: Name of the KB file (e.g., 'observable_symptoms_and_links.json')
    
    Returns:
        Parsed JSON content as dict
        
    Raises:
        FileNotFoundError: If the KB file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    kb_path = KB_DIR / filename
    if not kb_path.exists():
        logger.error(f"KB file not found: {kb_path}")
        raise FileNotFoundError(f"KB file not found: {kb_path}")
    
    try:
        with open(kb_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Validate that we got a dict
        if not isinstance(data, dict):
            raise ValueError(f"KB file {filename} must contain a JSON object, got {type(data).__name__}")
            
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in KB file {filename}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading KB file {filename}: {e}")
        raise


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


def load_interventions() -> Dict[str, Any]:
    """
    Load the Interventions KB.
    
    Returns:
        Full KB structure with interventions
    """
    return load_kb_file("interventions_modular_v1.json")


def load_root_cause_taxonomy() -> Dict[str, Any]:
    """
    Load the Root Cause Taxonomy KB.
    
    Returns:
        Full KB structure with root cause taxonomy
    """
    return load_kb_file("root_cause_taxonomy.json")

def load_tests() -> Dict[str, Any]:
    """
    Load the Tests KB.
    
    Returns:
        Full KB structure with tests
    """
    return load_kb_file("tests.json")


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
    Load all KB items from all JSON files in the KB directory.
    Flattens into a list suitable for passing to the Lead Investigator.
    
    This function dynamically loads all .json files (excluding archived files)
    and structures them appropriately based on their content.
    
    Returns:
        List of KB item dicts
    """
    all_items = []
    
    try:
        # Load observable symptoms KB
        obs_kb = load_observable_symptoms_and_links()
        all_items.extend(_process_observable_symptoms_kb(obs_kb))
    except Exception as e:
        logger.warning(f"Failed to load observable symptoms KB: {e}")
    
    try:
        # Load functional medicine KB
        fm_kb = load_functional_medicine_asd()
        all_items.extend(_process_functional_medicine_kb(fm_kb))
    except Exception as e:
        logger.warning(f"Failed to load functional medicine KB: {e}")
    
    try:
        # Load interventions KB
        interventions_kb = load_interventions()
        all_items.extend(_process_interventions_kb(interventions_kb))
    except Exception as e:
        logger.warning(f"Failed to load interventions KB: {e}")
    
    try:
        # Load root cause taxonomy KB
        taxonomy_kb = load_root_cause_taxonomy()
        all_items.extend(_process_root_cause_taxonomy_kb(taxonomy_kb))
    except Exception as e:
        logger.warning(f"Failed to load root cause taxonomy KB: {e}")
    
    try:
        # Load tests KB
        tests_kb = load_tests()
        all_items.extend(_process_tests_kb(tests_kb))
    except Exception as e:
        logger.warning(f"Failed to load tests KB: {e}")
    
    logger.info(f"Loaded {len(all_items)} total KB items from all sources")
    return all_items


def _process_observable_symptoms_kb(obs_kb: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process observable symptoms KB into structured items."""
    items = []
    
    if not obs_kb:
        return items
    
    # Add metadata
    items.append({
        "type": "kb_metadata",
        "source": "observable_symptoms_and_links",
        "title": obs_kb.get("title", "Observable Symptoms and Links"),
        "description": obs_kb.get("description", ""),
        "version": obs_kb.get("version", "1.0.0"),
    })
    
    # Add symptom mappings
    for mapping in obs_kb.get("symptom_mappings", []):
        items.append({
            "type": "symptom_mapping",
            "cluster": mapping.get("symptom_cluster"),
            "observable_symptoms": mapping.get("observable_symptoms", []),
            "possible_causes": mapping.get("possible_underlying_causes", []),
        })
    
    # Add cross-cutting patterns
    for pattern in obs_kb.get("cross_cutting_patterns", []):
        items.append({
            "type": "cross_cutting_pattern",
            "pattern": pattern.get("pattern"),
            "hypothesis": pattern.get("hypothesis"),
            "rationale": pattern.get("rationale"),
        })
    
    return items


def _process_functional_medicine_kb(fm_kb: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process functional medicine KB into structured items."""
    items = []
    
    if not fm_kb:
        return items
    
    # Handle metadata at root or nested under 'metadata' key
    metadata = fm_kb.get("metadata", fm_kb)
    items.append({
        "type": "kb_metadata",
        "source": "functional_medicine_asd",
        "title": metadata.get("title", "Functional Medicine Approaches to ASD"),
        "description": metadata.get("description", metadata.get("purpose", "")),
        "version": metadata.get("version", metadata.get("version_date", "1.0.0")),
    })
    
    # Add domains (gut, immunity, genetics, toxicity, nutrition)
    domains = fm_kb.get("domains", {})
    for domain_name, domain_data in domains.items():
        items.append({
            "type": "functional_medicine_domain",
            "domain": domain_name,
            "data": domain_data,
        })
    
    # Add clinical stance and roadmap
    if "clinical_stance_and_roadmap" in fm_kb:
        items.append({
            "type": "clinical_roadmap",
            "data": fm_kb["clinical_stance_and_roadmap"],
        })
    
    # Add evaluation algorithm
    if "evaluation_and_care_algorithm" in fm_kb:
        items.append({
            "type": "care_algorithm",
            "data": fm_kb["evaluation_and_care_algorithm"],
        })
    
    return items


def _process_interventions_kb(interventions_kb: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process interventions KB into structured items."""
    items = []
    
    if not interventions_kb:
        return items
    
    # Add metadata
    metadata = interventions_kb.get("metadata", {})
    items.append({
        "type": "kb_metadata",
        "source": "interventions",
        "title": metadata.get("title", "Interventions"),
        "description": metadata.get("description", ""),
        "version": metadata.get("version", "1.0.0"),
    })
    
    # Add intervention categories
    categories = interventions_kb.get("categories", [])
    for category in categories:
        items.append({
            "type": "intervention_category",
            "data": category,
        })
    
    return items


def _process_root_cause_taxonomy_kb(taxonomy_kb: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process root cause taxonomy KB into structured items."""
    items = []
    
    if not taxonomy_kb:
        return items
    
    # Add metadata
    metadata = taxonomy_kb.get("metadata", {})
    items.append({
        "type": "kb_metadata",
        "source": "root_cause_taxonomy",
        "title": metadata.get("title", "Root Cause Taxonomy"),
        "description": metadata.get("description", ""),
        "version": metadata.get("version", "1.0.0"),
    })
    
    # Add taxonomy items
    taxonomy = taxonomy_kb.get("taxonomy", [])
    for item in taxonomy:
        items.append({
            "type": "root_cause_taxonomy_item",
            "data": item,
        })
    
    return items


def _process_tests_kb(tests_kb: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process tests KB into structured items."""
    items = []
    
    if not tests_kb:
        return items
    
    # Add metadata
    metadata = tests_kb.get("metadata", {})
    items.append({
        "type": "kb_metadata",
        "source": "tests",
        "title": metadata.get("title", "Tests"),
        "description": metadata.get("description", ""),
        "version": metadata.get("version", "1.0.0"),
    })
    
    # Add test items
    tests = tests_kb.get("tests", [])
    for test in tests:
        items.append({
            "type": "test",
            "data": test,
        })
    
    return items


def search_kb_by_flags(flags: List[str], limit: int = 6) -> List[Dict[str, Any]]:
    """
    Very simple tag/flag match. You can replace with embeddings later.
    Matches if any of the 'who_it_may_help' tokens intersect with provided flags.
    """
    kb = load_all_kb_items()
    items = kb.get("items", [])
    flags_norm = {f.strip().lower() for f in flags}
    scored: List[Tuple[int, Dict[str, Any]]] = []
    for item in items:
        ic = (item.get("implementation_card") or {})
        helps = {h.strip().lower() for h in ic.get("who_it_may_help", [])}
        score = len(flags_norm.intersection(helps))
        if score > 0:
            scored.append((score, item))
    # Priority: score desc, then priority_tier, then name
    tier_order = {"Foundation": 0, "Core": 1, "Targeted": 2, "Advanced": 3}
    scored.sort(key=lambda x: ( -x[0],
                                tier_order.get(x[1].get("priority_tier", "Core"), 9),
                                x[1].get("name", "")))
    return [x[1] for x in scored[:limit]]


def map_hypotheses_to_kb(hypotheses: Dict[str, Any], top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Given a hypotheses payload (from your Hypothesis agent),
    derive flags and pick KB modules.
    Expecting something like:
    {
      "Symptoms": ["sleep fragmentation","constipation","irritability"],
      "Goals": ["sleep through night","reduce tantrums"]
    }
    """
    flags = []
    for k in ("Symptoms", "Goals", "RedFlags"):
        flags.extend(hypotheses.get(k, []))
    # normalize basic synonyms:
    synonyms = {
        "sleep issues": "sleep fragmentation",
        "loose stools": "diarrhea",
        "eczema": "skin rashes/eczema/hives"
    }
    flags = [synonyms.get(x.lower(), x) for x in flags]
    return search_kb_by_flags(flags, limit=top_k)


def search_kb_by_symptom(symptom_query: str) -> List[Dict[str, Any]]:
    """
    Search KB for symptom clusters matching a query string.
    
    Args:
        symptom_query: Search term (case-insensitive)
    
    Returns:
        List of matching symptom mappings
    """
    query_lower = symptom_query.lower()
    
    try:
        mappings = get_symptom_mappings()
    except Exception as e:
        logger.error(f"Failed to load symptom mappings for search: {e}")
        return []
    
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


def clear_kb_cache() -> None:
    """
    Clear the KB file cache. Useful for testing or when KB files are updated.
    """
    load_kb_file.cache_clear()
    logger.info("KB cache cleared")


def get_available_kb_files() -> List[str]:
    """
    Get a list of all available KB JSON files in the KB directory.
    
    Returns:
        List of KB filenames (excluding archived files)
    """
    if not KB_DIR.exists():
        logger.warning(f"KB directory not found: {KB_DIR}")
        return []
    
    kb_files = []
    for file_path in KB_DIR.glob("*.json"):
        # Skip files in archive subdirectory
        if "archive" not in str(file_path):
            kb_files.append(file_path.name)
    
    return sorted(kb_files)


def get_interventions_for_matching() -> List[Dict[str, Any]]:
    """
    Get interventions KB items formatted for matching to hypotheses.
    Returns the full kb_items array with all intervention details.
    
    Returns:
        List of intervention items with implementation cards
    """
    try:
        kb = load_interventions()
        return kb.get("kb_items", [])
    except Exception as e:
        logger.error(f"Failed to load interventions for matching: {e}")
        return []
