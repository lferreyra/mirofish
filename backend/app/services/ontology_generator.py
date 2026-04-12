"""
Gerar
1AnáliseConteúdoGerarSimulaçãoEntidadeRelacionamento
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
from ..utils.llm_client import LLMClient
from ..utils.locale import get_language_instruction
from .ontology_prompts_v2 import detect_sector_and_decision, get_ontology_system_prompt_v3

logger = logging.getLogger(__name__)


def _to_pascal_case(name: str) -> str:
    """ PascalCase 'works_for' -> 'WorksFor', 'person' -> 'Person'"""
    parts = re.split(r'[^a-zA-Z0-9]+', name)
    # camelCase  'camelCase' -> ['camel', 'Case']
    words = []
    for part in parts:
        words.extend(re.sub(r'([a-z])([A-Z])', r'\1_\2', part).split('_'))
    result = ''.join(word.capitalize() for word in words if word)
    return result if result else 'Unknown'


# Gerar
ONTOLOGY_SYSTEM_PROMPT = """\
Você é um especialista em design de ontologias para grafos de conhecimento. Sua tarefa é analisar o conteúdo textual e os requisitos de simulação fornecidos, e projetar tipos de entidades e relacionamentos adequados para **simulação de opinião pública em redes sociais no mercado brasileiro**.

**IMPORTANTE: Retorne APENAS dados em formato JSON válido. Não retorne nada além do JSON.**

## Contexto da Tarefa

Estamos construindo um **sistema de simulação de opinião pública em redes sociais**. Neste sistema:
- Cada entidade é uma "conta" ou "agente" que pode publicar, interagir e propagar informações em redes sociais
- Entidades influenciam umas às outras, repostam, comentam e respondem
- Precisamos simular as reações e caminhos de propagação de informação de todas as partes em eventos de opinião pública

Portanto, **entidades devem ser agentes do mundo real que podem publicar e interagir em redes sociais**:

**Permitido**:
- Indivíduos específicos (figuras públicas, formadores de opinião, especialistas, pessoas comuns)
- Empresas e negócios (incluindo suas contas oficiais)
- Organizações (universidades, associações, ONGs, sindicatos, etc.)
- Órgãos governamentais e agências reguladoras
- Organizações de mídia (jornais, TVs, influenciadores, sites, etc.)
- Plataformas de redes sociais
- Representantes de grupos específicos (associações, fã-clubes, grupos de advocacy, etc.)

**NÃO Permitido**:
- Conceitos abstratos (como "opinião pública", "emoção", "tendência")
- Tópicos/temas (como "integridade acadêmica", "reforma educacional")
- Pontos de vista/atitudes (como "apoiadores", "oponentes")

## Formato de Saída

Retorne JSON com a seguinte estrutura:

```json
{
    "entity_types": [
        {
            "name": "NomeTipoEntidade (Português do Brasil, PascalCase. Ex: ConsumidorJovem, LojaLocal, InfluenciadorDigital)",
            "description": "Descrição breve em PORTUGUÊS DO BRASIL (máx 100 caracteres)",
            "attributes": [
                {
                    "name": "nome_atributo (português, snake_case. Ex: faixa_etaria, poder_aquisitivo)",
                    "type": "text",
                    "description": "Descrição do atributo em português"
                }
            ],
            "examples": ["Exemplo 1 em português", "Exemplo 2 em português"]
        }
    ],
    "edge_types": [
        {
            "name": "NOME_RELACIONAMENTO (Português, UPPER_SNAKE_CASE. Ex: COMPETE_COM, INFLUENCIA, REGULA)",
            "description": "Descrição breve em PORTUGUÊS DO BRASIL (máx 100 caracteres)",
            "source_targets": [
                {"source": "TipoOrigem", "target": "TipoDestino"}
            ],
            "attributes": []
        }
    ],
    "analysis_summary": "Análise breve do conteúdo em PORTUGUÊS DO BRASIL"
}
```

## Diretrizes de Design

### 1. Tipos de Entidades — Seguir Rigorosamente

**Quantidade: exatamente 10 tipos de entidades**

**Hierarquia (obrigatória)**:

A. **Tipos de fallback (obrigatórios, últimos 2 da lista)**:
   - `Person`: Qualquer pessoa física sem tipo específico
   - `Organization`: Qualquer organização sem tipo específico

B. **Tipos específicos (8, baseados no conteúdo)**:
   - Projete tipos para os papéis principais do texto
   - Cada tipo deve ter limites claros sem sobreposição

### 2. Tipos de Relacionamento
- Quantidade: 6-10
- Devem refletir conexões reais em redes sociais

### 3. Atributos
- 1-3 atributos-chave por tipo
- Nomes proibidos: `name`, `uuid`, `group_id`, `created_at`, `summary`
- Recomendado: `full_name`, `title`, `role`, `position`, `location`, `description`

## Referência de Tipos

**Pessoa**: Student, Professor, Journalist, Celebrity, Executive, Official, Lawyer, Doctor, Person (fallback)
**Organização**: University, Company, GovernmentAgency, MediaOutlet, Hospital, School, NGO, Organization (fallback)
**Relacionamentos**: WORKS_FOR, STUDIES_AT, AFFILIATED_WITH, REPRESENTS, REGULATES, REPORTS_ON, COMMENTS_ON, RESPONDS_TO, SUPPORTS, OPPOSES, COLLABORATES_WITH, COMPETES_WITH

⚠️ REGRA ABSOLUTA DE IDIOMA ⚠️
- Nomes de tipos: INGLÊS (PascalCase / UPPER_SNAKE_CASE / snake_case)
- Descrições, examples, analysis_summary: PORTUGUÊS DO BRASIL
- ZERO caracteres chineses permitidos em qualquer campo
- Texto fonte em chinês ou inglês → TRADUZA para português
"""


class OntologyGenerator:
    """
    Gerar
    AnáliseConteúdoGerarEntidadeRelacionamento
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
        Gerar
        
        Args:
            document_texts: 
            simulation_requirement: Descrição dos requisitos da simulação
            additional_context: 
            
        Returns:
            entity_types, edge_types
        """
        user_message = self._build_user_message(
            document_texts, 
            simulation_requirement,
            additional_context
        )
        
        lang_instruction = get_language_instruction()

        # AUGUR v2: detecção bidimensional setor + tipo de decisão
        sector, decision = detect_sector_and_decision(simulation_requirement)
        logger.info(f"AUGUR v2 ontology: setor={sector}, decisao={decision}")

        system_prompt = f"{get_ontology_system_prompt_v3(sector, decision)}\n\n{lang_instruction}"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        result = self.llm_client.chat_json(
            messages=messages,
            temperature=0.3,
            max_tokens=4096
        )
        
        result = self._validate_and_process(result)
        result["_augur_meta"] = {"setor": sector, "tipo_decisao": decision}
        
        return result
    
    # LLM 5
    MAX_TEXT_LENGTH_FOR_LLM = 50000
    
    def _build_user_message(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str]
    ) -> str:
        """"""
        
        combined_text = "\n\n---\n\n".join(document_texts)
        original_length = len(combined_text)
        
        # 5LLMConteúdoGrafo
        if len(combined_text) > self.MAX_TEXT_LENGTH_FOR_LLM:
            combined_text = combined_text[:self.MAX_TEXT_LENGTH_FOR_LLM]
            combined_text += f"\n\n...(original text: {original_length} chars, truncated to first {self.MAX_TEXT_LENGTH_FOR_LLM} chars for ontology analysis)..."
        
        message = f"""## Simulation Requirement

{simulation_requirement}

## Document Content

{combined_text}
"""
        
        if additional_context:
            message += f"""
## Additional Notes

{additional_context}
"""
        
        message += """
Based on the above content, design entity types and relationship types suitable for social media public opinion simulation.

**Mandatory rules**:
1. Must output exactly 10 entity types
2. The last 2 must be fallback types: Person (individual fallback) and Organization (organization fallback)
3. The first 8 are specific types designed based on text content
4. All entity types must be real-world agents that can post on social media, NOT abstract concepts
5. Attribute names cannot use name, uuid, group_id, etc. (reserved words) — use full_name, org_name, etc. instead
"""
        
        return message
    
    def _validate_and_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Resultado"""
        
        if "entity_types" not in result:
            result["entity_types"] = []
        if "edge_types" not in result:
            result["edge_types"] = []
        if "analysis_summary" not in result:
            result["analysis_summary"] = ""
        
        # Entidade
        # PascalCase  edge  source_targets
        entity_name_map = {}
        for entity in result["entity_types"]:
            # entity name  PascalCaseZep API
            if "name" in entity:
                original_name = entity["name"]
                entity["name"] = _to_pascal_case(original_name)
                if entity["name"] != original_name:
                    logger.warning(f"Entity type name '{original_name}' auto-converted to '{entity['name']}'")
                entity_name_map[original_name] = entity["name"]
            if "attributes" not in entity:
                entity["attributes"] = []
            if "examples" not in entity:
                entity["examples"] = []
            # description100
            if len(entity.get("description", "")) > 100:
                entity["description"] = entity["description"][:97] + "..."
        
        # Relacionamento
        for edge in result["edge_types"]:
            # edge name  SCREAMING_SNAKE_CASEZep API
            if "name" in edge:
                original_name = edge["name"]
                edge["name"] = original_name.upper()
                if edge["name"] != original_name:
                    logger.warning(f"Edge type name '{original_name}' auto-converted to '{edge['name']}'")
            # source_targets Entidade PascalCase
            for st in edge.get("source_targets", []):
                if st.get("source") in entity_name_map:
                    st["source"] = entity_name_map[st["source"]]
                if st.get("target") in entity_name_map:
                    st["target"] = entity_name_map[st["target"]]
            if "source_targets" not in edge:
                edge["source_targets"] = []
            if "attributes" not in edge:
                edge["attributes"] = []
            if len(edge.get("description", "")) > 100:
                edge["description"] = edge["description"][:97] + "..."
        
        # Zep API  10 Entidade 10
        MAX_ENTITY_TYPES = 10
        MAX_EDGE_TYPES = 10

        # name
        seen_names = set()
        deduped = []
        for entity in result["entity_types"]:
            name = entity.get("name", "")
            if name and name not in seen_names:
                seen_names.add(name)
                deduped.append(entity)
            elif name in seen_names:
                logger.warning(f"Duplicate entity type '{name}' removed during validation")
        result["entity_types"] = deduped

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
        
        entity_names = {e["name"] for e in result["entity_types"]}
        has_person = "Person" in entity_names
        has_organization = "Organization" in entity_names
        
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
            
            result["entity_types"].extend(fallbacks_to_add)
        
        if len(result["entity_types"]) > MAX_ENTITY_TYPES:
            result["entity_types"] = result["entity_types"][:MAX_ENTITY_TYPES]
        
        if len(result["edge_types"]) > MAX_EDGE_TYPES:
            result["edge_types"] = result["edge_types"][:MAX_EDGE_TYPES]
        
        return result
    
    def generate_python_code(self, ontology: Dict[str, Any]) -> str:
        """
        Pythonontology.py
        
        Args:
            ontology: 
            
        Returns:
            Python
        """
        code_lines = [
            '"""',
            'Entidade',
            'MiroFishGerarSimulação',
            '"""',
            '',
            'from pydantic import Field',
            'from zep_cloud.external_clients.ontology import EntityModel, EntityText, EdgeModel',
            '',
            '',
            '# ============== Entidade ==============',
            '',
        ]
        
        # GerarEntidade
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
        
        code_lines.append('# ============== Relacionamento ==============')
        code_lines.append('')
        
        # GerarRelacionamento
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            # PascalCase
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
        
        # Gerar
        code_lines.append('# ============== Configuração ==============')
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
        
        # Gerarsource_targets
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
