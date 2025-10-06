# Knowledge Base (KB) Directory

This directory contains structured knowledge base items used by the Lead Investigator agent to generate hypotheses about underlying biomedical contributors to patient symptoms.

## Current KB Files

### `observable_symptoms_and_links.json`
Maps observable symptoms to potential underlying causes with supporting evidence and recommended workup.

**Structure:**
- `symptom_mappings`: Array of symptom clusters with possible underlying causes
- `cross_cutting_patterns`: Patterns that link multiple symptom clusters to common root causes
- `usage_notes`: Guidelines for interpreting and using the KB

**Used by:** Lead Investigator agent via `/api/investigator/latest` endpoint

## How to Add New KB Items

### Option 1: Edit Existing Files
Simply edit the JSON files in this directory. The KB is loaded fresh on each API call, so changes take effect immediately (no server restart needed).

### Option 2: Create New KB Files
1. Create a new JSON file in this directory (e.g., `interventions.json`)
2. Add a loader function in `backend/app/services/knowledge_base.py`:
   ```python
   def load_interventions_kb() -> Dict[str, Any]:
       return load_kb_file("interventions.json")
   ```
3. Update `load_all_kb_items()` to include your new KB file

### Option 3: Upload via API (Future)
We can add a POST endpoint to upload KB items programmatically if needed.

## KB Design Principles

1. **Structured and Parseable**: Use consistent JSON schemas so the LLM can reliably extract information
2. **Evidence-Based**: Include supporting evidence and recommended workup for each hypothesis
3. **Actionable**: Focus on modifiable causes that can be tested or treated
4. **Safety-First**: Prioritize urgent/high-risk conditions (seizures, regression, severe GI)
5. **Non-Diagnostic**: Frame as hypotheses for clinician review, not diagnoses

## Example KB Item Structure

```json
{
  "symptom_cluster": "Sleep Disturbances",
  "observable_symptoms": ["Frequent night waking", "Snoring"],
  "possible_underlying_causes": [
    {
      "cause": "Obstructive Sleep Apnea",
      "supporting_evidence": ["Snoring", "Gasping", "Enlarged tonsils"],
      "recommended_workup": ["Sleep study", "ENT evaluation"],
      "modifiability": "High"
    }
  ]
}
```

## API Endpoints

- **GET `/api/kb/list`** - List all KB items (flattened for LLM consumption)
- **GET `/api/kb/observable-symptoms`** - Get full Observable Symptoms KB structure
- **POST `/api/investigator/latest`** - Run Lead Investigator with KB (auto-loads all KB files)

## Version Control

KB files are version-controlled in git. When making changes:
1. Update the `version` field in the JSON file
2. Update the `last_updated` field
3. Commit with a descriptive message (e.g., "Add mitochondrial dysfunction to seizure causes")

## Future Enhancements

- **Interventions KB**: Map conditions to specific interventions (supplements, dietary changes, therapies)
- **Lab Interpretation KB**: Reference ranges and interpretation guidance for common labs
- **Medication Safety KB**: Drug interactions and contraindications for common autism medications
- **Research Citations KB**: Link hypotheses to published research for clinician reference
