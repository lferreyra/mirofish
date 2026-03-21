"""
Ontology generation service.
Analyzes text and produces entity and relationship type definitions for social simulation.
"""

import json
from typing import Dict, Any, List, Optional
from ..utils.llm_client import LLMClient


# System prompt for ontology generation
ONTOLOGY_SYSTEM_PROMPT = """You are a professional knowledge-graph ontology designer. Your task is to analyze the given text and simulation requirements and design entity types and relationship types suitable for **social-media opinion simulation**.

**Important: Output valid JSON only. Do not output anything else.**

## Core context

We are building a **social media opinion simulation system**. In this system:
- Each entity is an "account" or actor that can post, interact, and spread information on social media
- Entities influence one another through shares, comments, and replies
- We simulate reactions and information paths during opinion events

Therefore, **entities must be real-world actors that can plausibly post and interact on social media**:

**May be**:
- Specific individuals (public figures, parties involved, opinion leaders, experts, ordinary people)
- Companies and enterprises (including official accounts)
- Organizations (universities, associations, NGOs, unions, etc.)
- Government departments and regulators
- Media outlets (newspapers, TV, self-media, websites)
- Social platforms themselves
- Representative groups (e.g. alumni associations, fan groups, advocacy groups)

**May not be**:
- Abstract concepts (e.g. "public opinion", "emotion", "trend")
- Topics or subjects alone (e.g. "academic integrity", "education reform")
- Positions or attitudes alone (e.g. "pro side", "anti side")

## Output format

Return JSON with this structure:

```json
{
    "entity_types": [
        {
            "name": "entity type name (English, PascalCase)",
            "description": "short description (English, max ~100 characters)",
            "attributes": [
                {
                    "name": "attribute name (English, snake_case)",
                    "type": "text",
                    "description": "attribute description"
                }
            ],
            "examples": ["example entity 1", "example entity 2"]
        }
    ],
    "edge_types": [
        {
            "name": "RELATION_TYPE_NAME (English, UPPER_SNAKE_CASE)",
            "description": "short description (English, max ~100 characters)",
            "source_targets": [
                {"source": "source entity type", "target": "target entity type"}
            ],
            "attributes": []
        }
    ],
    "analysis_summary": "brief analysis of the text (English)"
}
```

## Design rules (critical)

### 1. Entity types — strict rules

**Count: exactly 10 entity types**

**Hierarchy (must include both specific and fallback types)**:

Your 10 types must include:

A. **Fallback types (required; place last in the list)**:
   - `Person`: catch-all for any natural person not covered by a more specific person type.
   - `Organization`: catch-all for any organization not covered by a more specific org type.

B. **Specific types (8; derive from the text)**:
   - Reflect main roles in the text
   - e.g. academic events: `Student`, `Professor`, `University`
   - e.g. business events: `Company`, `CEO`, `Employee`

**Why fallbacks**:
- Many people appear (teachers, passers-by, anonymous netizens) — if no specific type fits, use `Person`
- Small orgs and ad hoc groups → `Organization`

**Specific type rules**:
- Identify frequent or high-impact role types from the text
- Each type should have clear boundaries and minimal overlap
- `description` must distinguish the type from the fallbacks

### 2. Relationship types

- Count: 6–10
- Relationships should reflect realistic social-media ties
- Ensure `source_targets` cover your entity types

### 3. Attributes

- 1–3 key attributes per entity type
- **Do not** use reserved names: `name`, `uuid`, `group_id`, `created_at`, `summary`
- Prefer: `full_name`, `title`, `role`, `position`, `location`, `description`, etc.

## Entity type reference

**Individuals (specific)**:
- Student, Professor, Journalist, Celebrity, Executive, Official, Lawyer, Doctor

**Individuals (fallback)**:
- Person: any natural person when no more specific type applies

**Organizations (specific)**:
- University, Company, GovernmentAgency, MediaOutlet, Hospital, School, NGO

**Organizations (fallback)**:
- Organization: any organization when no more specific type applies

## Relationship type reference

- WORKS_FOR, STUDIES_AT, AFFILIATED_WITH, REPRESENTS, REGULATES, REPORTS_ON, COMMENTS_ON, RESPONDS_TO, SUPPORTS, OPPOSES, COLLABORATES_WITH, COMPETES_WITH
"""


class OntologyGenerator:
    """
    Generates ontology definitions from text:
    entity types and relationship types for simulation.
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()
    
    def generate(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate ontology definition.

        Args:
            document_texts: Document text segments
            simulation_requirement: Simulation requirement description
            additional_context: Optional extra context

        Returns:
            Ontology dict (entity_types, edge_types, etc.)
        """
        # Build user message
        user_message = self._build_user_message(
            document_texts, 
            simulation_requirement,
            additional_context
        )
        
        messages = [
            {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        result = self.llm_client.chat_json(
            messages=messages,
            temperature=0.3,
            max_tokens=4096
        )
        
        result = self._validate_and_process(result)
        
        return result
    
    # Max characters sent to the LLM (~50k Chinese chars / large UTF-8 window)
    MAX_TEXT_LENGTH_FOR_LLM = 50000
    
    def _build_user_message(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str]
    ) -> str:
        """Build the user message for the LLM."""
        
        combined_text = "\n\n---\n\n".join(document_texts)
        original_length = len(combined_text)
        
        if len(combined_text) > self.MAX_TEXT_LENGTH_FOR_LLM:
            combined_text = combined_text[:self.MAX_TEXT_LENGTH_FOR_LLM]
            combined_text += f"\n\n...(source text has {original_length} characters; first {self.MAX_TEXT_LENGTH_FOR_LLM} sent for ontology analysis)..."
        
        message = f"""## Simulation requirement

{simulation_requirement}

## Document content

{combined_text}
"""
        
        if additional_context:
            message += f"""
## Additional notes

{additional_context}
"""
        
        message += """
From the above, design entity types and relationship types suitable for social-opinion simulation.

**Rules**:
1. Output exactly 10 entity types
2. The last 2 must be fallbacks: Person (individual fallback) and Organization (organization fallback)
3. The first 8 are specific types grounded in the text
4. All entity types must be real actors who can post; not abstract concepts
5. Do not use reserved attribute names: name, uuid, group_id, etc.; use full_name, org_name, etc.
"""
        
        return message
    
    def _validate_and_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and post-process the LLM result."""
        
        # Ensure required keys
        if "entity_types" not in result:
            result["entity_types"] = []
        if "edge_types" not in result:
            result["edge_types"] = []
        if "analysis_summary" not in result:
            result["analysis_summary"] = ""
        
        # Entity types
        for entity in result["entity_types"]:
            if "attributes" not in entity:
                entity["attributes"] = []
            if "examples" not in entity:
                entity["examples"] = []
            # Cap description length
            if len(entity.get("description", "")) > 100:
                entity["description"] = entity["description"][:97] + "..."
        
        # Edge types
        for edge in result["edge_types"]:
            if "source_targets" not in edge:
                edge["source_targets"] = []
            if "attributes" not in edge:
                edge["attributes"] = []
            if len(edge.get("description", "")) > 100:
                edge["description"] = edge["description"][:97] + "..."
        
        # Zep API: max 10 custom entity types and 10 custom edge types
        MAX_ENTITY_TYPES = 10
        MAX_EDGE_TYPES = 10
        
        # Fallback type definitions
        person_fallback = {
            "name": "Person",
            "description": "Any individual person not fitting other specific person types.",
            "attributes": [
                {"name": "full_name", "type": "text", "description": "Full name of the person"},
                {"name": "role", "type": "text", "description": "Role or occupation"}
            ],
            "examples": ["ordinary citizen", "anonymous netizen"]
        }
        
        organization_fallback = {
            "name": "Organization",
            "description": "Any organization not fitting other specific organization types.",
            "attributes": [
                {"name": "org_name", "type": "text", "description": "Name of the organization"},
                {"name": "org_type", "type": "text", "description": "Type of organization"}
            ],
            "examples": ["small business", "community group"]
        }
        
        # Check for existing fallbacks
        entity_names = {e["name"] for e in result["entity_types"]}
        has_person = "Person" in entity_names
        has_organization = "Organization" in entity_names
        
        # Fallbacks to append
        fallbacks_to_add = []
        if not has_person:
            fallbacks_to_add.append(person_fallback)
        if not has_organization:
            fallbacks_to_add.append(organization_fallback)
        
        if fallbacks_to_add:
            current_count = len(result["entity_types"])
            needed_slots = len(fallbacks_to_add)
            
            if current_count + needed_slots > MAX_ENTITY_TYPES:
                to_remove = current_count + needed_slots - MAX_ENTITY_TYPES
                result["entity_types"] = result["entity_types"][:-to_remove]
            
            # Append fallbacks
            result["entity_types"].extend(fallbacks_to_add)
        
        # Hard cap (defensive)
        if len(result["entity_types"]) > MAX_ENTITY_TYPES:
            result["entity_types"] = result["entity_types"][:MAX_ENTITY_TYPES]
        
        if len(result["edge_types"]) > MAX_EDGE_TYPES:
            result["edge_types"] = result["edge_types"][:MAX_EDGE_TYPES]
        
        return result
    
    def generate_python_code(self, ontology: Dict[str, Any]) -> str:
        """
        Convert ontology definition to Python code (similar to ontology.py).

        Args:
            ontology: Ontology definition dict

        Returns:
            Python source string
        """
        code_lines = [
            '"""',
            'Custom entity type definitions',
            'Auto-generated by MiroFish for social-opinion simulation',
            '"""',
            '',
            'from pydantic import Field',
            'from zep_cloud.external_clients.ontology import EntityModel, EntityText, EdgeModel',
            '',
            '',
            '# ============== Entity type definitions ==============',
            '',
        ]
        
        # Emit entity type classes
        for entity in ontology.get("entity_types", []):
            name = entity["name"]
            desc = entity.get("description", f"A {name} entity.")
            
            code_lines.append(f'class {name}(EntityModel):')
            code_lines.append(f'    """{desc}"""')
            
            attrs = entity.get("attributes", [])
            if attrs:
                for attr in attrs:
                    attr_name = attr["name"]
                    attr_desc = attr.get("description", attr_name)
                    code_lines.append(f'    {attr_name}: EntityText = Field(')
                    code_lines.append(f'        description="{attr_desc}",')
                    code_lines.append(f'        default=None')
                    code_lines.append(f'    )')
            else:
                code_lines.append('    pass')
            
            code_lines.append('')
            code_lines.append('')
        
        code_lines.append('# ============== Edge type definitions ==============')
        code_lines.append('')
        
        # Emit edge type classes
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            # Edge name -> PascalCase class name
            class_name = ''.join(word.capitalize() for word in name.split('_'))
            desc = edge.get("description", f"A {name} relationship.")
            
            code_lines.append(f'class {class_name}(EdgeModel):')
            code_lines.append(f'    """{desc}"""')
            
            attrs = edge.get("attributes", [])
            if attrs:
                for attr in attrs:
                    attr_name = attr["name"]
                    attr_desc = attr.get("description", attr_name)
                    code_lines.append(f'    {attr_name}: EntityText = Field(')
                    code_lines.append(f'        description="{attr_desc}",')
                    code_lines.append(f'        default=None')
                    code_lines.append(f'    )')
            else:
                code_lines.append('    pass')
            
            code_lines.append('')
            code_lines.append('')
        
        code_lines.append('# ============== Type registries ==============')
        code_lines.append('')
        code_lines.append('ENTITY_TYPES = {')
        for entity in ontology.get("entity_types", []):
            name = entity["name"]
            code_lines.append(f'    "{name}": {name},')
        code_lines.append('}')
        code_lines.append('')
        code_lines.append('EDGE_TYPES = {')
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            class_name = ''.join(word.capitalize() for word in name.split('_'))
            code_lines.append(f'    "{name}": {class_name},')
        code_lines.append('}')
        code_lines.append('')
        
        # EDGE_SOURCE_TARGETS
        code_lines.append('EDGE_SOURCE_TARGETS = {')
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            source_targets = edge.get("source_targets", [])
            if source_targets:
                st_list = ', '.join([
                    f'{{"source": "{st.get("source", "Entity")}", "target": "{st.get("target", "Entity")}"}}'
                    for st in source_targets
                ])
                code_lines.append(f'    "{name}": [{st_list}],')
        code_lines.append('}')
        
        return '\n'.join(code_lines)

