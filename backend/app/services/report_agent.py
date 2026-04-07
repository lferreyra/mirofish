"""
Serviço do Report Agent
Geração de relatórios de simulação com padrão ReACT usando LangChain + Zep

1. Gera relatórios baseados nos requisitos da simulação e informações do grafo Zep
2. Primeiro planeja a estrutura, depois gera seção por seção
3. Cada seção usa o padrão ReACT de múltiplas rodadas de raciocínio
4. Suporta diálogo com usuário, chamando ferramentas de busca autonomamente
"""

import os
import json
import time
import re
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from ..utils.locale import get_language_instruction, t
from .zep_tools import (
    ZepToolsService, 
    SearchResult, 
    InsightForgeResult, 
    PanoramaResult,
    InterviewResult
)

logger = get_logger('mirofish.report_agent')


class ReportLogger:
    """
    Logger detalhado do Report Agent
    
    Gera arquivo agent_log.jsonl na pasta do relatório, registrando cada ação detalhada。
    Cada linha é um objeto JSON completo com timestamp, tipo de ação e detalhes。
    """
    
    def __init__(self, report_id: str):
        """
        
        Args:
            report_id: ID do relatório, para determinar o caminho do log
        """
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'agent_log.jsonl'
        )
        self.start_time = datetime.now()
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _get_elapsed_time(self) -> float:
        """"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def log(
        self, 
        action: str, 
        stage: str,
        details: Dict[str, Any],
        section_title: str = None,
        section_index: int = None
    ):
        """
        
        Args:
            action: Tipo de ação, como 'start', 'tool_call', 'llm_response', 'section_complete' 
            stage: Fase atual, como 'planning', 'generating', 'completed'
            details: Conteúdo
            section_title: Seção
            section_index: Seção
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(self._get_elapsed_time(), 2),
            "report_id": self.report_id,
            "action": action,
            "stage": stage,
            "section_title": section_title,
            "section_index": section_index,
            "details": details
        }
        
        # JSONL
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def log_start(self, simulation_id: str, graph_id: str, simulation_requirement: str):
        """RelatórioGerar"""
        self.log(
            action="report_start",
            stage="pending",
            details={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "simulation_requirement": simulation_requirement,
                "message": t('report.taskStarted')
            }
        )
    
    def log_planning_start(self):
        """Outline"""
        self.log(
            action="planning_start",
            stage="planning",
            details={"message": t('report.planningStart')}
        )
    
    def log_planning_context(self, context: Dict[str, Any]):
        """"""
        self.log(
            action="planning_context",
            stage="planning",
            details={
                "message": t('report.fetchSimContext'),
                "context": context
            }
        )
    
    def log_planning_complete(self, outline_dict: Dict[str, Any]):
        """Outline"""
        self.log(
            action="planning_complete",
            stage="planning",
            details={
                "message": t('report.planningComplete'),
                "outline": outline_dict
            }
        )
    
    def log_section_start(self, section_title: str, section_index: int):
        """SeçãoGerar"""
        self.log(
            action="section_start",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={"message": t('report.sectionStart', title=section_title)}
        )
    
    def log_react_thought(self, section_title: str, section_index: int, iteration: int, thought: str):
        """Registrar processo de raciocínio ReACT"""
        self.log(
            action="react_thought",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "thought": thought,
                "message": t('report.reactThought', iteration=iteration)
            }
        )
    
    def log_tool_call(
        self, 
        section_title: str, 
        section_index: int,
        tool_name: str, 
        parameters: Dict[str, Any],
        iteration: int
    ):
        """Registrar chamada de ferramenta"""
        self.log(
            action="tool_call",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "parameters": parameters,
                "message": t('report.toolCall', toolName=tool_name)
            }
        )
    
    def log_tool_result(
        self,
        section_title: str,
        section_index: int,
        tool_name: str,
        result: str,
        iteration: int
    ):
        """Registrar chamada de ferramentaResultado（Conteúdo completo, sem truncar）"""
        self.log(
            action="tool_result",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "result": result,  # Resultado
                "result_length": len(result),
                "message": t('report.toolResult', toolName=tool_name)
            }
        )
    
    def log_llm_response(
        self,
        section_title: str,
        section_index: int,
        response: str,
        iteration: int,
        has_tool_calls: bool,
        has_final_answer: bool
    ):
        """ LLM Conteúdo completo, sem truncar"""
        self.log(
            action="llm_response",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "response": response,  # 
                "response_length": len(response),
                "has_tool_calls": has_tool_calls,
                "has_final_answer": has_final_answer,
                "message": t('report.llmResponse', hasToolCalls=has_tool_calls, hasFinalAnswer=has_final_answer)
            }
        )
    
    def log_section_content(
        self,
        section_title: str,
        section_index: int,
        content: str,
        tool_calls_count: int
    ):
        """SeçãoConteúdoGerarConteúdoSeção"""
        self.log(
            action="section_content",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": content,  # Conteúdo completo, sem truncar
                "content_length": len(content),
                "tool_calls_count": tool_calls_count,
                "message": t('report.sectionContentDone', title=section_title)
            }
        )
    
    def log_section_full_complete(
        self,
        section_title: str,
        section_index: int,
        full_content: str
    ):
        """
        SeçãoGerar

        SeçãoConteúdo
        """
        self.log(
            action="section_complete",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": full_content,
                "content_length": len(full_content),
                "message": t('report.sectionComplete', title=section_title)
            }
        )
    
    def log_report_complete(self, total_sections: int, total_time_seconds: float):
        """RelatórioGerar"""
        self.log(
            action="report_complete",
            stage="completed",
            details={
                "total_sections": total_sections,
                "total_time_seconds": round(total_time_seconds, 2),
                "message": t('report.reportComplete')
            }
        )
    
    def log_error(self, error_message: str, stage: str, section_title: str = None):
        """"""
        self.log(
            action="error",
            stage=stage,
            section_title=section_title,
            section_index=None,
            details={
                "error": error_message,
                "message": t('report.errorOccurred', error=error_message)
            }
        )


class ReportConsoleLogger:
    """
    Report Agent 
    
    INFOWARNINGRelatórioPasta console_log.txt 
     agent_log.jsonl 
    """
    
    def __init__(self, report_id: str):
        """
        
        Args:
            report_id: ID do relatório, para determinar o caminho do log
        """
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'console_log.txt'
        )
        self._ensure_log_file()
        self._file_handler = None
        self._setup_file_handler()
    
    def _ensure_log_file(self):
        """"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _setup_file_handler(self):
        """"""
        import logging
        
        self._file_handler = logging.FileHandler(
            self.log_file_path,
            mode='a',
            encoding='utf-8'
        )
        self._file_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        self._file_handler.setFormatter(formatter)
        
        # report_agent  logger
        loggers_to_attach = [
            'mirofish.report_agent',
            'mirofish.zep_tools',
        ]
        
        for logger_name in loggers_to_attach:
            target_logger = logging.getLogger(logger_name)
            if self._file_handler not in target_logger.handlers:
                target_logger.addHandler(self._file_handler)
    
    def close(self):
        """ logger """
        import logging
        
        if self._file_handler:
            loggers_to_detach = [
                'mirofish.report_agent',
                'mirofish.zep_tools',
            ]
            
            for logger_name in loggers_to_detach:
                target_logger = logging.getLogger(logger_name)
                if self._file_handler in target_logger.handlers:
                    target_logger.removeHandler(self._file_handler)
            
            self._file_handler.close()
            self._file_handler = None
    
    def __del__(self):
        """"""
        self.close()


class ReportStatus(str, Enum):
    """Status do relatório"""
    PENDING = "pending"
    PLANNING = "planning"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReportSection:
    """RelatórioSeção"""
    title: str
    content: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content
        }

    def to_markdown(self, level: int = 2) -> str:
        """Markdown"""
        md = f"{'#' * level} {self.title}\n\n"
        if self.content:
            md += f"{self.content}\n\n"
        return md


@dataclass
class ReportOutline:
    """Outline do relatório"""
    title: str
    summary: str
    sections: List[ReportSection]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "sections": [s.to_dict() for s in self.sections]
        }
    
    def to_markdown(self) -> str:
        """Markdown"""
        md = f"# {self.title}\n\n"
        md += f"> {self.summary}\n\n"
        for section in self.sections:
            md += section.to_markdown()
        return md


@dataclass
class Report:
    """Relatório"""
    report_id: str
    simulation_id: str
    graph_id: str
    simulation_requirement: str
    status: ReportStatus
    outline: Optional[ReportOutline] = None
    markdown_content: str = ""
    created_at: str = ""
    completed_at: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "simulation_id": self.simulation_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "status": self.status.value,
            "outline": self.outline.to_dict() if self.outline else None,
            "markdown_content": self.markdown_content,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error
        }


# ═══════════════════════════════════════════════════════════════
# Prompt
# ═══════════════════════════════════════════════════════════════

# ── Ferramenta ──

TOOL_DESC_INSIGHT_FORGE = """\
【Busca de Insights Profundos - Ferramenta poderosa de busca】
Função de busca poderosa, projetada para análise profunda. Ela:
1. Decompõe automaticamente sua pergunta em sub-questões
2. Busca informações no grafo da simulação de múltiplas dimensões
3. Integra resultados de busca semântica, análise de entidades e rastreamento de relações
4. Retorna o conteúdo mais abrangente e profundo

【Quando usar】
- Análise profunda de um tema específico
- Entender múltiplos aspectos de um evento
- Obter material rico para sustentar seções do relatório

【Conteúdo retornado】
- Fatos originais relevantes (citáveis diretamente)
- Insights de entidades centrais
- Análise de cadeias de relações"""

TOOL_DESC_PANORAMA_SEARCH = """\
【Busca Panorâmica - Visão completa】
Ferramenta para obter a visão completa dos resultados da simulação, ideal para entender a evolução dos eventos. Ela:
1. Obtém todos os nós e relações relevantes
2. Distingue fatos atuais válidos de fatos históricos/expirados
3. Ajuda a entender como a dinâmica evoluiu

【Quando usar】
- Entender a linha completa de desenvolvimento dos eventos
- Comparar mudanças entre diferentes fases da simulação
- Obter informações completas de entidades e relações

【Conteúdo retornado】
- Fatos atuais válidos (resultado mais recente da simulação)
- Fatos históricos/expirados (registro de evolução)
- Todas as entidades envolvidas"""

TOOL_DESC_QUICK_SEARCH = """\
【Busca Rápida - Consulta simples】
Ferramenta leve de busca rápida, ideal para consultas simples e diretas.

【Quando usar】
- Buscar rapidamente uma informação específica
- Verificar um fato
- Consultas simples de informação

【Conteúdo retornado】
- Lista de fatos mais relevantes para a consulta"""

TOOL_DESC_INTERVIEW_AGENTS = """\
【Entrevista Profunda - Entrevista real com Agentes (dual plataforma)】
Chama a API de entrevista do ambiente de simulação OASIS para entrevistar Agentes reais!
Não é simulação por LLM — são chamadas reais à interface de entrevista para obter respostas originais dos Agentes.
Por padrão entrevista em Twitter e Reddit simultaneamente para perspectivas mais completas.

Fluxo:
1. Lê automaticamente os perfis para conhecer todos os Agentes simulados
2. Seleciona inteligentemente os Agentes mais relevantes para o tema da entrevista
3. Gera automaticamente as perguntas da entrevista
4. Chama /api/simulation/interview/batch para entrevista real em duas plataformas
5. Integra todos os resultados, fornecendo análise multi-perspectiva

【Quando usar】
- Entender visões de diferentes papéis sobre o evento (o que consumidores pensam? empresários? analistas?)
- Coletar opiniões e posições de múltiplas partes
- Obter respostas reais dos Agentes simulados (do ambiente OASIS)
- Tornar o relatório mais vivo, incluindo "registros de entrevista"

【Conteúdo retornado】
- Informações de identidade dos Agentes entrevistados
- Respostas de cada Agente nas plataformas Twitter e Reddit
- Citações-chave (citáveis diretamente)
- Resumo da entrevista e comparação de pontos de vista

【IMPORTANTE】O ambiente de simulação OASIS precisa estar rodando para usar esta funcionalidade!"""

# ── Prompt de planejamento do outline ──

PLAN_SYSTEM_PROMPT = """\
Você é especialista em elaborar RELATÓRIOS DE PREVISÃO baseados em simulações de opinião pública com IA.
Você tem visão de deus sobre todos os agentes, suas interações, seus comportamentos e os padrões emergentes.

【MISSÃO】
A simulação representa um "futuro previamente executado". Seu relatório responde:
"Se esse cenário ocorrer, o que vai acontecer? Como diferentes grupos vão reagir?"

【ESTRUTURA OBRIGATÓRIA DO RELATÓRIO】
Você DEVE gerar EXATAMENTE as seguintes seções, nessa ordem:

1. **Resumo Executivo** — síntese com as principais descobertas e índice de confiança (0-100%)

2. **Cenários Futuros** — TRÊS cenários obrigatórios:
   - Cenário Otimista (probabilidade em %, impacto, descrição detalhada)
   - Cenário Base/Realista (probabilidade em %, impacto, descrição detalhada)
   - Cenário Pessimista (probabilidade em %, impacto, descrição detalhada)
   As três probabilidades devem somar 100%.

3. **Fatores de Risco** — TRÊS a CINCO riscos identificados, cada um com:
   - Nome, descrição, probabilidade (%) e impacto (Alto/Médio/Baixo)

4. **Mapa de Forças** — agentes mais influentes, clusters de comportamento e tensões emergentes

5. **Cronologia por Rodada** — o que aconteceu em cada fase da simulação, pontos de inflexão

6. **Padrões Emergentes** — comportamentos que surgiram naturalmente da interação entre agentes

7. **Hipóteses Causais** — hipóteses sobre causa e efeito, com evidências, contra-evidências e nível de confiança (Alta/Média/Baixa)

8. **Recomendações Estratégicas** — TRÊS a CINCO recomendações com prazo e urgência (Urgente/Alta/Média/Baixa)

9. **Previsões** — TRÊS previsões com datas estimadas e probabilidade (%)

【REGRAS CRÍTICAS】
- Escreva TUDO em português do Brasil com linguagem profissional e acessível
- Cite comportamentos REAIS dos agentes simulados
- Cada seção deve ter conteúdo RICO e ESPECÍFICO
- NÃO invente dados — baseie-se exclusivamente no que a simulação revelou
- O relatório deve ter a profundidade de uma consultoria premium

Retorne JSON com o formato:
{
    "title": "Título do relatório em português",
    "summary": "Resumo em 2-3 frases em português",
    "sections": [
        {
            "title": "Nome da seção em português",
            "description": "Instruções para gerar o conteúdo desta seção"
        }
    ]
}

IMPORTANTE: O array sections deve ter EXATAMENTE 9 elementos, um para cada seção listada acima.

⚠️ REGRA ABSOLUTA DE IDIOMA ⚠️
Os dados da simulação abaixo podem estar em CHINÊS ou INGLÊS — isso NÃO importa.
Você DEVE escrever o título, summary e TODOS os nomes de seções em PORTUGUÊS DO BRASIL.
Se você retornar QUALQUER texto em chinês, o relatório será REJEITADO.
Exemplos de títulos corretos: "Relatório de Previsão: Mercado de Calçados", "Resumo Executivo", "Cenários Futuros"
Exemplos de títulos PROIBIDOS: "Análise", "PrevisãoRelatório", ""
"""

PLAN_USER_PROMPT_TEMPLATE = """\
【CENÁRIO DA SIMULAÇÃO】
Hipótese testada: {simulation_requirement}

【ESCALA DA SIMULAÇÃO】
- Entidades simuladas: {total_nodes}
- Relacionamentos gerados: {total_edges}
- Tipos de entidades: {entity_types}
- Agentes ativos: {total_entities}

【AMOSTRA DE FATOS SIMULADOS】
{related_facts_json}

Com base nesses dados, elabore o plano completo do relatório com as 9 seções obrigatórias.
Cada seção deve ter uma descrição clara do que deve ser analisado e escrito em português do Brasil.

⚠️ REGRA ABSOLUTA: Relatório INTEIRO em PORTUGUÊS DO BRASIL.
Dados em chinês → TRADUZA. NENHUM caractere chinês permitido. VIOLAÇÃO = INVÁLIDO.
Seja específico sobre quais aspectos da simulação cada seção deve explorar."""

# ── Prompt de geração de seções ──

SECTION_SYSTEM_PROMPT_TEMPLATE = """\
Você é um especialista em redação de RELATÓRIOS DE PREVISÃO, escrevendo uma seção do relatório.

Título do relatório: {report_title}
Resumo do relatório: {report_summary}
Cenário de previsão (requisito da simulação): {simulation_requirement}

Seção a ser redigida: {section_title}

═══════════════════════════════════════════════════════════════
【CONCEITO CENTRAL】
═══════════════════════════════════════════════════════════════

O mundo simulado é um ensaio do futuro. Injetamos condições específicas (requisito da simulação),
e o comportamento e interações dos Agentes representam previsões do comportamento futuro dos grupos.

Sua tarefa é:
- Revelar o que aconteceu no futuro sob as condições definidas
- Prever como cada tipo de grupo (Agente) reagiu e agiu
- Identificar tendências, riscos e oportunidades futuras relevantes

❌ NÃO escreva como uma análise da situação atual do mundo real
✅ Foque em "o que vai acontecer" — os resultados da simulação SÃO o futuro previsto

═══════════════════════════════════════════════════════════════
【REGRAS MAIS IMPORTANTES - OBRIGATÓRIAS】
═══════════════════════════════════════════════════════════════

1. 【OBRIGATÓRIO usar ferramentas para observar o mundo simulado】
   - Você está observando o ensaio do futuro com "visão de deus"
   - Todo o conteúdo DEVE vir de eventos e falas dos Agentes no mundo simulado
   - PROIBIDO usar seu próprio conhecimento para escrever o conteúdo do relatório
   - Cada seção deve chamar ferramentas pelo menos 3 vezes (máximo 5) para observar o mundo simulado

2. 【OBRIGATÓRIO citar falas e ações originais dos Agentes】
   - As falas e ações dos Agentes são previsões do comportamento futuro dos grupos
   - Use formato de citação no relatório para exibir essas previsões, por exemplo:
     > "Determinado grupo diria: conteúdo original..."
   - Essas citações são a evidência central das previsões da simulação

3. 【Consistência de idioma - citações DEVEM ser traduzidas para o idioma do relatório】
   - O conteúdo retornado pelas ferramentas pode estar em outro idioma
   - O relatório DEVE ser escrito INTEIRAMENTE em português do Brasil
   - Ao citar conteúdo em outro idioma retornado pelas ferramentas, traduza para português antes de incluir
   - Mantenha o significado original ao traduzir, garantindo naturalidade
   - Esta regra se aplica tanto ao texto corrido quanto aos blocos de citação (formato >)

4. 【Apresentar fielmente os resultados da previsão】
   - O conteúdo do relatório deve refletir os resultados simulados que representam o futuro
   - NÃO adicione informações que não existem na simulação
   - Se houver informação insuficiente em algum aspecto, declare isso honestamente

═══════════════════════════════════════════════════════════════
【⚠️⚠️⚠️ REGRA ABSOLUTA DE IDIOMA — NÃO VIOLAR】
═══════════════════════════════════════════════════════════════

ESCREVA 100% EM PORTUGUÊS DO BRASIL.
- Dados em chinês das ferramentas → TRADUZA para PT-BR
- Dados em inglês → TRADUZA para PT-BR  
- NENHUM caractere chinês (汉字) permitido no output
- Citações de agentes DEVEM ser traduzidas
- VIOLAÇÃO = RELATÓRIO INVÁLIDO

═══════════════════════════════════════════════════════════════
【⚠️ REGRAS DE FORMATAÇÃO - EXTREMAMENTE IMPORTANTE!】
═══════════════════════════════════════════════════════════════

【Uma seção = unidade mínima de conteúdo】
- Cada seção é a menor unidade do relatório
- ❌ PROIBIDO usar qualquer título Markdown (#, ##, ###, #### etc.) dentro da seção
- ❌ PROIBIDO adicionar o título da seção no início do conteúdo
- ✅ O título da seção é adicionado automaticamente pelo sistema — escreva apenas o texto corrido
- ✅ Use **negrito**, separação de parágrafos, citações e listas para organizar, mas NÃO use títulos

【Exemplo CORRETO】
```
Esta seção analisa a dinâmica de propagação na opinião pública. Através da análise profunda dos dados simulados, descobrimos...

**Fase de ignição inicial**

As redes sociais funcionaram como palco principal da disseminação inicial:

> "As redes contribuíram com 68% do volume inicial de menções..."

**Fase de amplificação emocional**

As plataformas de vídeo curto amplificaram o impacto do evento:

- Forte impacto visual
- Alto grau de ressonância emocional
```

【Exemplo ERRADO】
```
## Resumo Executivo          ← ERRADO! Não adicione títulos
### 1. Fase Inicial          ← ERRADO! Não use ### para subseções
#### 1.1 Análise Detalhada   ← ERRADO! Não use #### para detalhar

Esta seção analisa...
```

═══════════════════════════════════════════════════════════════
【FERRAMENTAS DE BUSCA DISPONÍVEIS】(chamar 3-5 vezes por seção)
═══════════════════════════════════════════════════════════════

{tools_description}

【Sugestões de uso — combine diferentes ferramentas, não use apenas uma】
- insight_forge: Análise de insights profundos, decompõe a questão e busca fatos e relações multidimensionais
- panorama_search: Busca panorâmica ampla, para entender o panorama geral, timeline e evolução dos eventos
- quick_search: Verificação rápida de um ponto de informação específico
- interview_agents: Entrevistar Agentes simulados, obter perspectivas em primeira pessoa e reações reais de diferentes papéis

═══════════════════════════════════════════════════════════════
【FLUXO DE TRABALHO】
═══════════════════════════════════════════════════════════════

Em cada resposta, você pode fazer APENAS uma das duas coisas (nunca as duas ao mesmo tempo):

Opção A - Chamar ferramenta:
Escreva seu raciocínio, depois chame uma ferramenta no seguinte formato:
<tool_call>
{{"name": "nome_da_ferramenta", "parameters": {{"nome_param": "valor_param"}}}}
</tool_call>
O sistema executará a ferramenta e retornará o resultado. Você NÃO precisa e NÃO pode escrever o resultado da ferramenta.

Opção B - Gerar conteúdo final:
Quando tiver informações suficientes das ferramentas, comece com "Final Answer:" e escreva o conteúdo da seção.

⚠️ ESTRITAMENTE PROIBIDO:
- Proibido incluir chamada de ferramenta E Final Answer na mesma resposta
- Proibido inventar resultados de ferramentas (Observation) — todos os resultados são injetados pelo sistema
- Máximo de uma chamada de ferramenta por resposta

═══════════════════════════════════════════════════════════════
【REQUISITOS DO CONTEÚDO DA SEÇÃO】
═══════════════════════════════════════════════════════════════

1. O conteúdo DEVE ser baseado nos dados da simulação obtidos pelas ferramentas
2. Cite abundantemente o texto original para demonstrar os efeitos da simulação
3. Use formato Markdown (mas PROIBIDO usar títulos):
   - Use **texto em negrito** para destacar pontos importantes (substitua subtítulos)
   - Use listas (- ou 1.2.3.) para organizar pontos
   - Use linhas em branco para separar parágrafos
   - ❌ PROIBIDO usar #, ##, ###, #### ou qualquer sintaxe de título
4. 【Formato de citação - DEVE ser parágrafo independente】
   Citações devem ser parágrafos independentes, com uma linha em branco antes e depois:

   ✅ Formato correto:
   ```
   A resposta da empresa foi considerada insuficiente.

   > "O padrão de resposta da empresa mostrou-se rígido e lento no ambiente dinâmico das redes sociais."

   Esta avaliação reflete a insatisfação geral do público.
   ```

   ❌ Formato errado:
   ```
   A resposta foi insuficiente.> "O padrão de resposta..." Esta avaliação reflete...
   ```
5. Mantenha coerência lógica com as demais seções
6. 【Evite repetição】Leia atentamente o conteúdo das seções já concluídas abaixo, NÃO repita as mesmas informações
7. 【REFORÇANDO】NÃO adicione nenhum título! Use **negrito** no lugar de subtítulos

⚠️ REGRA ABSOLUTA: As ferramentas podem retornar dados em CHINÊS ou INGLÊS.
Você DEVE traduzir TUDO para PORTUGUÊS DO BRASIL antes de incluir no relatório.
NÃO copie texto em chinês — traduza SEMPRE. Se uma citação está em chinês, traduza-a."""

SECTION_USER_PROMPT_TEMPLATE = """\
Conteúdo das seções já concluídas (leia atentamente para evitar repetição):
{previous_content}

═══════════════════════════════════════════════════════════════
【TAREFA ATUAL】Redigir a seção: {section_title}
═══════════════════════════════════════════════════════════════

【LEMBRETES IMPORTANTES】
1. Leia atentamente as seções concluídas acima — NÃO repita o mesmo conteúdo!
2. Antes de começar, OBRIGATÓRIO chamar ferramentas para obter dados da simulação
3. Combine diferentes ferramentas — não use apenas uma
4. O conteúdo do relatório DEVE vir dos resultados da busca — NÃO use seu próprio conhecimento
5. Escreva TUDO em português do Brasil

【⚠️ ALERTA DE FORMATAÇÃO - OBRIGATÓRIO】
- ❌ NÃO escreva nenhum título (#, ##, ###, #### — NENHUM)
- ❌ NÃO escreva "{section_title}" como início
- ✅ O título da seção é adicionado automaticamente pelo sistema
- ✅ Escreva direto o texto corrido, use **negrito** no lugar de subtítulos

Comece:
1. Primeiro pense (Thought) em quais informações esta seção precisa
2. Depois chame uma ferramenta (Action) para obter dados da simulação
3. Após coletar informações suficientes, gere o Final Answer (texto corrido, sem nenhum título)"""

# ── Templates de mensagem dentro do ciclo ReACT ──

REACT_OBSERVATION_TEMPLATE = """\
Observação (resultado da busca):

═══ Ferramenta {tool_name} retornou ═══
{result}

═══════════════════════════════════════════════════════════════
Ferramentas chamadas: {tool_calls_count}/{max_tool_calls} (usadas: {used_tools_str}){unused_hint}
- Se a informação é suficiente: comece com "Final Answer:" e escreva o conteúdo da seção (DEVE citar o texto original acima)
- Se precisa de mais informações: chame uma ferramenta para continuar buscando
═══════════════════════════════════════════════════════════════"""

REACT_INSUFFICIENT_TOOLS_MSG = (
    "【ATENÇÃO】Você chamou ferramentas apenas {tool_calls_count} vezes — mínimo necessário: {min_tool_calls}. "
    "Chame mais ferramentas para obter mais dados da simulação antes de escrever o Final Answer.{unused_hint}"
)

REACT_INSUFFICIENT_TOOLS_MSG_ALT = (
    "Ferramentas chamadas apenas {tool_calls_count} vezes — mínimo necessário: {min_tool_calls}. "
    "Chame ferramentas para obter dados da simulação.{unused_hint}"
)

REACT_TOOL_LIMIT_MSG = (
    "Limite de chamadas de ferramentas atingido ({tool_calls_count}/{max_tool_calls}) — não é possível chamar mais. "
    'Agora escreva imediatamente o conteúdo da seção, começando com "Final Answer:".'
)

REACT_UNUSED_TOOLS_HINT = "\n💡 Você ainda não usou: {unused_list} — tente ferramentas diferentes para obter informações de múltiplos ângulos"

REACT_FORCE_FINAL_MSG = "Limite de chamadas atingido. Escreva diretamente o Final Answer: com o conteúdo da seção."

# ── Prompt de chat ──

CHAT_SYSTEM_PROMPT_TEMPLATE = """\
Você é um assistente de previsão simulada, conciso e eficiente.

【CONTEXTO】
Condição de previsão: {simulation_requirement}

【RELATÓRIO DE ANÁLISE GERADO】
{report_content}

【REGRAS】
1. Priorize responder com base no conteúdo do relatório acima
2. Responda diretamente, evite raciocínios longos
3. Só chame ferramentas se o conteúdo do relatório for insuficiente para responder
4. Respostas devem ser concisas, claras e organizadas
5. Responda SEMPRE em português do Brasil

【FERRAMENTAS DISPONÍVEIS】(use apenas quando necessário, máximo 1-2 chamadas)
{tools_description}

【FORMATO DE CHAMADA DE FERRAMENTAS】
<tool_call>
{{"name": "nome_da_ferramenta", "parameters": {{"nome_param": "valor_param"}}}}
</tool_call>

【ESTILO DE RESPOSTA】
- Conciso e direto, sem textos longos desnecessários
- Use formato > para citar conteúdo-chave
- Primeiro dê a conclusão, depois explique os motivos"""

CHAT_OBSERVATION_SUFFIX = "\n\nResponda a pergunta de forma concisa."


# ═══════════════════════════════════════════════════════════════
# ReportAgent
# ═══════════════════════════════════════════════════════════════


class ReportAgent:
    """
    Report Agent - Agent de geração de relatórios de simulação

    Usa o padrão ReACT (Reasoning + Acting)：
    1. Fase de planejamento: analisa requisitos e planeja estrutura
    2. Fase de geração: gera conteúdo seção por seção com múltiplas chamadas de ferramentas
    3. Fase de reflexão: verifica completude e precisão do conteúdo
    """
    
    # Máximo de chamadas de ferramentas (por seção)
    MAX_TOOL_CALLS_PER_SECTION = 5
    
    # Máximo de rodadas de reflexão
    MAX_REFLECTION_ROUNDS = 3
    
    # Máximo de chamadas de ferramentas no diálogo
    MAX_TOOL_CALLS_PER_CHAT = 2
    
    def __init__(
        self, 
        graph_id: str,
        simulation_id: str,
        simulation_requirement: str,
        llm_client: Optional[LLMClient] = None,
        zep_tools: Optional[ZepToolsService] = None
    ):
        """
        Inicializar Report Agent
        
        Args:
            graph_id: ID do grafo
            simulation_id: ID da simulação
            simulation_requirement: Descrição dos requisitos da simulação
            llm_client: Cliente LLM (opcional)
            zep_tools: Serviço de ferramentas Zep (opcional)
        """
        self.graph_id = graph_id
        self.simulation_id = simulation_id
        self.simulation_requirement = simulation_requirement
        
        self.llm = llm_client or LLMClient()
        self.zep_tools = zep_tools or ZepToolsService()
        
        # Ferramenta
        self.tools = self._define_tools()
        
        # generate_report
        self.report_logger: Optional[ReportLogger] = None
        # generate_report
        self.console_logger: Optional[ReportConsoleLogger] = None
        
        logger.info(t('report.agentInitDone', graphId=graph_id, simulationId=simulation_id))
    
    def _define_tools(self) -> Dict[str, Dict[str, Any]]:
        """Definir ferramentas disponíveis"""
        return {
            "insight_forge": {
                "name": "insight_forge",
                "description": TOOL_DESC_INSIGHT_FORGE,
                "parameters": {
                    "query": "Pergunta ou tópico que deseja analisar em profundidade",
                    "report_context": "Contexto da seção atual do relatório (opcional, ajuda a gerar sub-perguntas mais precisas)"
                }
            },
            "panorama_search": {
                "name": "panorama_search",
                "description": TOOL_DESC_PANORAMA_SEARCH,
                "parameters": {
                    "query": "Consulta de busca, para ordenação por relevância",
                    "include_expired": "Incluir conteúdo expirado/histórico (padrão True)"
                }
            },
            "quick_search": {
                "name": "quick_search",
                "description": TOOL_DESC_QUICK_SEARCH,
                "parameters": {
                    "query": "String de consulta de busca",
                    "limit": "Quantidade de resultados (opcional, padrão 10)"
                }
            },
            "interview_agents": {
                "name": "interview_agents",
                "description": TOOL_DESC_INTERVIEW_AGENTS,
                "parameters": {
                    "interview_topic": "Tema ou descrição da entrevista (ex: 'entender a visão dos consumidores sobre o novo produto')",
                    "max_agents": "Máximo de agentes a entrevistar (opcional, padrão 5, máx 10)"
                }
            }
        }
    
    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any], report_context: str = "") -> str:
        """
        Executar chamada de ferramenta
        
        Args:
            tool_name: Ferramenta
            parameters: Ferramenta
            report_context: RelatórioInsightForge
            
        Returns:
            FerramentaResultado
        """
        logger.info(t('report.executingTool', toolName=tool_name, params=parameters))
        
        try:
            if tool_name == "insight_forge":
                query = parameters.get("query", "")
                ctx = parameters.get("report_context", "") or report_context
                result = self.zep_tools.insight_forge(
                    graph_id=self.graph_id,
                    query=query,
                    simulation_requirement=self.simulation_requirement,
                    report_context=ctx
                )
                return result.to_text()
            
            elif tool_name == "panorama_search":
                query = parameters.get("query", "")
                include_expired = parameters.get("include_expired", True)
                if isinstance(include_expired, str):
                    include_expired = include_expired.lower() in ['true', '1', 'yes']
                result = self.zep_tools.panorama_search(
                    graph_id=self.graph_id,
                    query=query,
                    include_expired=include_expired
                )
                return result.to_text()
            
            elif tool_name == "quick_search":
                # - Busca
                query = parameters.get("query", "")
                limit = parameters.get("limit", 10)
                if isinstance(limit, str):
                    limit = int(limit)
                result = self.zep_tools.quick_search(
                    graph_id=self.graph_id,
                    query=query,
                    limit=limit
                )
                return result.to_text()
            
            elif tool_name == "interview_agents":
                # - OASISAPISimulaçãoAgent
                interview_topic = parameters.get("interview_topic", parameters.get("query", ""))
                max_agents = parameters.get("max_agents", 5)
                if isinstance(max_agents, str):
                    max_agents = int(max_agents)
                max_agents = min(max_agents, 10)
                result = self.zep_tools.interview_agents(
                    simulation_id=self.simulation_id,
                    interview_requirement=interview_topic,
                    simulation_requirement=self.simulation_requirement,
                    max_agents=max_agents
                )
                return result.to_text()
            
            # ========== FerramentaFerramenta ==========
            
            elif tool_name == "search_graph":
                # quick_search
                logger.info(t('report.redirectToQuickSearch'))
                return self._execute_tool("quick_search", parameters, report_context)
            
            elif tool_name == "get_graph_statistics":
                result = self.zep_tools.get_graph_statistics(self.graph_id)
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_entity_summary":
                entity_name = parameters.get("entity_name", "")
                result = self.zep_tools.get_entity_summary(
                    graph_id=self.graph_id,
                    entity_name=entity_name
                )
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_simulation_context":
                # insight_forge
                logger.info(t('report.redirectToInsightForge'))
                query = parameters.get("query", self.simulation_requirement)
                return self._execute_tool("insight_forge", {"query": query}, report_context)
            
            elif tool_name == "get_entities_by_type":
                entity_type = parameters.get("entity_type", "")
                nodes = self.zep_tools.get_entities_by_type(
                    graph_id=self.graph_id,
                    entity_type=entity_type
                )
                result = [n.to_dict() for n in nodes]
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            else:
                return f"Ferramenta desconhecida: {tool_name}. Use uma das seguintes: insight_forge, panorama_search, quick_search"
                
        except Exception as e:
            logger.error(t('report.toolExecFailed', toolName=tool_name, error=str(e)))
            return f"Falha na execução da ferramenta: {str(e)}"
    
    # Ferramenta JSON
    VALID_TOOL_NAMES = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}

    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        Parsear chamadas de ferramenta da resposta do LLM

        1. <tool_call>{"name": "tool_name", "parameters": {...}}</tool_call>
        2.  JSONFerramenta JSON
        """
        tool_calls = []

        # 1: XML
        xml_pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
        for match in re.finditer(xml_pattern, response, re.DOTALL):
            try:
                call_data = json.loads(match.group(1))
                tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        if tool_calls:
            return tool_calls

        # 2:  - LLM  JSON <tool_call>
        # 1 JSON
        stripped = response.strip()
        if stripped.startswith('{') and stripped.endswith('}'):
            try:
                call_data = json.loads(stripped)
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
                    return tool_calls
            except json.JSONDecodeError:
                pass

        # +  JSON JSON
        json_pattern = r'(\{"(?:name|tool)"\s*:.*?\})\s*$'
        match = re.search(json_pattern, stripped, re.DOTALL)
        if match:
            try:
                call_data = json.loads(match.group(1))
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        return tool_calls

    def _is_valid_tool_call(self, data: dict) -> bool:
        """ JSON Ferramenta"""
        # {"name": ..., "parameters": ...}  {"tool": ..., "params": ...}
        tool_name = data.get("name") or data.get("tool")
        if tool_name and tool_name in self.VALID_TOOL_NAMES:
            # name / parameters
            if "tool" in data:
                data["name"] = data.pop("tool")
            if "params" in data and "parameters" not in data:
                data["parameters"] = data.pop("params")
            return True
        return False
    
    def _get_tools_description(self) -> str:
        """Gerar texto de descrição das ferramentas"""
        desc_parts = ["Ferramentas disponíveis:"]
        for name, tool in self.tools.items():
            params_desc = ", ".join([f"{k}: {v}" for k, v in tool["parameters"].items()])
            desc_parts.append(f"- {name}: {tool['description']}")
            if params_desc:
                desc_parts.append(f"  Parâmetros: {params_desc}")
        return "\n".join(desc_parts)
    
    def plan_outline(
        self, 
        progress_callback: Optional[Callable] = None
    ) -> ReportOutline:
        """
        Planejar outline do relatório
        
        Usa o LLM para analisar requisitos e planejar a estrutura do relatório
        
        Args:
            progress_callback: Função callback de progresso
            
        Returns:
            ReportOutline: Outline do relatório
        """
        logger.info(t('report.startPlanningOutline'))
        
        if progress_callback:
            progress_callback("planning", 0, t('progress.analyzingRequirements'))
        
        # Primeiro obtém o contexto da simulação
        context = self.zep_tools.get_simulation_context(
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement
        )
        
        if progress_callback:
            progress_callback("planning", 30, t('progress.generatingOutline'))
        
        system_prompt = f"{PLAN_SYSTEM_PROMPT}\n\n{get_language_instruction()}"
        user_prompt = PLAN_USER_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            total_nodes=context.get('graph_statistics', {}).get('total_nodes', 0),
            total_edges=context.get('graph_statistics', {}).get('total_edges', 0),
            entity_types=list(context.get('graph_statistics', {}).get('entity_types', {}).keys()),
            total_entities=context.get('total_entities', 0),
            related_facts_json=json.dumps(context.get('related_facts', [])[:10], ensure_ascii=False, indent=2),
        )

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            if progress_callback:
                progress_callback("planning", 80, t('progress.parsingOutline'))
            
            # Parsear outline
            sections = []
            for section_data in response.get("sections", []):
                sections.append(ReportSection(
                    title=section_data.get("title", ""),
                    content=""
                ))
            
            outline = ReportOutline(
                title=response.get("title", "Relatório de Análise Preditiva"),
                summary=response.get("summary", ""),
                sections=sections
            )
            
            # ── Pós-processamento: forçar português ──
            outline = self._ensure_portuguese_outline(outline)
            
            if progress_callback:
                progress_callback("planning", 100, t('progress.outlinePlanComplete'))
            
            logger.info(t('report.outlinePlanDone', count=len(sections)))
            return outline
            
        except Exception as e:
            logger.error(t('report.outlinePlanFailed', error=str(e)))
            # Retornar outline padrão (3 seções, como fallback)
            return ReportOutline(
                title="Relatório de Previsão Futura",
                summary="Análise de tendências e riscos futuros baseada em simulação preditiva",
                sections=[
                    ReportSection(title="Cenários de Previsão e Descobertas Principais"),
                    ReportSection(title="Análise Preditiva de Comportamento dos Grupos"),
                    ReportSection(title="Perspectivas de Tendências e Alertas de Risco")
                ]
            )
    
    @staticmethod
    def _has_chinese(text: str) -> bool:
        """Detecta se o texto contém caracteres chineses"""
        if not text:
            return False
        return bool(re.search(r'[\u4e00-\u9fff]', text))
    
    def _ensure_portuguese_outline(self, outline: 'ReportOutline') -> 'ReportOutline':
        """
        Pós-processamento: se o título ou seções contêm chinês,
        chama o LLM para traduzir para português do Brasil.
        """
        texts_to_check = [outline.title, outline.summary] + [s.title for s in outline.sections]
        has_any_chinese = any(self._has_chinese(t) for t in texts_to_check)
        
        if not has_any_chinese:
            return outline
        
        logger.warning("Detectado chinês no outline — traduzindo para PT-BR...")
        
        try:
            sections_json = json.dumps(
                [{"title": s.title, "description": getattr(s, 'description', '')} for s in outline.sections],
                ensure_ascii=False
            )
            translate_prompt = (
                "Traduza o seguinte JSON para português do Brasil.\n"
                "Mantenha EXATAMENTE a mesma estrutura JSON. Traduza TODOS os valores de string.\n"
                "NÃO deixe NENHUM texto em chinês. Retorne APENAS o JSON traduzido.\n\n"
                f'{{"title": "{outline.title}", "summary": "{outline.summary}", "sections": {sections_json}}}'
            )

            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": "Você é um tradutor. Traduza todo conteúdo para português do Brasil. Retorne JSON puro."},
                    {"role": "user", "content": translate_prompt}
                ],
                temperature=0.1
            )
            
            if response and "title" in response:
                outline.title = response.get("title", outline.title)
                outline.summary = response.get("summary", outline.summary)
                translated_sections = response.get("sections", [])
                for i, ts in enumerate(translated_sections):
                    if i < len(outline.sections):
                        outline.sections[i].title = ts.get("title", outline.sections[i].title)
                logger.info(f"Outline traduzido com sucesso: {outline.title}")
            
        except Exception as e:
            logger.error(f"Falha ao traduzir outline: {e}")
            default_titles = [
                "Resumo Executivo", "Cenários Futuros", "Fatores de Risco",
                "Mapa de Forças", "Cronologia por Rodada", "Padrões Emergentes",
                "Hipóteses Causais", "Recomendações Estratégicas", "Previsões"
            ]
            for i, dt in enumerate(default_titles):
                if i < len(outline.sections) and self._has_chinese(outline.sections[i].title):
                    outline.sections[i].title = dt
            if self._has_chinese(outline.title):
                outline.title = "Relatório de Previsão Futura"
            if self._has_chinese(outline.summary):
                outline.summary = "Análise preditiva baseada em simulação multiagente"
        
        return outline

    def _generate_section_react(
        self, 
        section: ReportSection,
        outline: ReportOutline,
        previous_sections: List[str],
        progress_callback: Optional[Callable] = None,
        section_index: int = 0
    ) -> str:
        """
        Gera conteúdo de uma seção usando o padrão ReACT
        
        ReACT
        1. Thought- Análise
        2. Action- Ferramenta
        3. Observation- AnáliseFerramentaResultado
        4. 
        5. Final Answer- GerarSeçãoConteúdo
        
        Args:
            section: GerarSeção
            outline: Outline
            previous_sections: SeçãoConteúdo
            progress_callback: Callback de progresso
            section_index: Seção
            
        Returns:
            SeçãoConteúdoMarkdown
        """
        logger.info(t('report.reactGenerateSection', title=section.title))
        
        # Seção
        if self.report_logger:
            self.report_logger.log_section_start(section.title, section_index)
        
        system_prompt = SECTION_SYSTEM_PROMPT_TEMPLATE.format(
            report_title=outline.title,
            report_summary=outline.summary,
            simulation_requirement=self.simulation_requirement,
            section_title=section.title,
            tools_description=self._get_tools_description(),
        )
        system_prompt = f"{system_prompt}\n\n{get_language_instruction()}"

        # prompt - ConcluídoSeção4000
        if previous_sections:
            previous_parts = []
            for sec in previous_sections:
                # Seção4000
                truncated = sec[:4000] + "..." if len(sec) > 4000 else sec
                previous_parts.append(truncated)
            previous_content = "\n\n---\n\n".join(previous_parts)
        else:
            previous_content = "(Esta é a primeira seção)"
        
        user_prompt = SECTION_USER_PROMPT_TEMPLATE.format(
            previous_content=previous_content,
            section_title=section.title,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # ReACT
        tool_calls_count = 0
        max_iterations = 5  # 
        min_tool_calls = 3  # Ferramenta
        conflict_retries = 0  # FerramentaFinal Answer
        used_tools = set()  # Ferramenta
        all_tools = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}

        # RelatórioInsightForgeGerar
        report_context = f"Título da seção: {section.title}\nRequisito da simulação: {self.simulation_requirement}"
        
        for iteration in range(max_iterations):
            if progress_callback:
                progress_callback(
                    "generating", 
                    int((iteration / max_iterations) * 100),
                    t('progress.deepSearchAndWrite', current=tool_calls_count, max=self.MAX_TOOL_CALLS_PER_SECTION)
                )
            
            response = self.llm.chat(
                messages=messages,
                temperature=0.5,
                max_tokens=4096
            )

            # LLM  NoneAPI Conteúdo
            if response is None:
                logger.warning(t('report.sectionIterNone', title=section.title, iteration=iteration + 1))
                # Se ainda houver iterações, adiciona mensagem e tenta novamente
                if iteration < max_iterations - 1:
                    messages.append({"role": "assistant", "content": "(resposta vazia)"})
                    messages.append({"role": "user", "content": "Por favor, continue gerando o conteúdo."})
                    continue
                # Última iteração também retornou None, sai do loop para encerramento forçado
                break

            logger.debug(f"LLM response: {response[:200]}...")

            # Parsear uma vez, reutilizar resultado
            tool_calls = self._parse_tool_calls(response)
            has_tool_calls = bool(tool_calls)
            has_final_answer = "Final Answer:" in response

            # ── LLM Ferramenta Final Answer ──
            if has_tool_calls and has_final_answer:
                conflict_retries += 1
                logger.warning(
                    t('report.sectionConflict', title=section.title, iteration=iteration+1, conflictCount=conflict_retries)
                )

                if conflict_retries <= 2:
                    # Primeiras duas vezes: descartar resposta e pedir nova ao LLM
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": (
                            "【ERRO DE FORMATO】Você incluiu chamada de ferramenta E Final Answer na mesma resposta — isso não é permitido.\n"
                            "Cada resposta deve fazer APENAS uma das duas coisas:\n"
                            "- Chamar uma ferramenta (um bloco <tool_call>, SEM escrever Final Answer)\n"
                            "- Gerar conteúdo final (começar com 'Final Answer:', SEM incluir <tool_call>)\n"
                            "Responda novamente, fazendo apenas uma das duas."
                        ),
                    })
                    continue
                else:
                    # Terceira vez: tratamento degradado, truncar e executar
                    logger.warning(
                        t('report.sectionConflictDowngrade', title=section.title, conflictCount=conflict_retries)
                    )
                    first_tool_end = response.find('</tool_call>')
                    if first_tool_end != -1:
                        response = response[:first_tool_end + len('</tool_call>')]
                        tool_calls = self._parse_tool_calls(response)
                        has_tool_calls = bool(tool_calls)
                    has_final_answer = False
                    conflict_retries = 0

            # Registrar log de resposta do LLM
            if self.report_logger:
                self.report_logger.log_llm_response(
                    section_title=section.title,
                    section_index=section_index,
                    response=response,
                    iteration=iteration + 1,
                    has_tool_calls=has_tool_calls,
                    has_final_answer=has_final_answer
                )

            # ── Caso1：LLM gerou Final Answer ──
            if has_final_answer:
                # Chamadas insuficientes, rejeitar e pedir mais chamadas
                if tool_calls_count < min_tool_calls:
                    messages.append({"role": "assistant", "content": response})
                    unused_tools = all_tools - used_tools
                    unused_hint = f"(Estas ferramentas ainda não foram usadas, recomendamos experimentá-las: {', '.join(unused_tools)})" if unused_tools else ""
                    messages.append({
                        "role": "user",
                        "content": REACT_INSUFFICIENT_TOOLS_MSG.format(
                            tool_calls_count=tool_calls_count,
                            min_tool_calls=min_tool_calls,
                            unused_hint=unused_hint,
                        ),
                    })
                    continue

                final_answer = response.split("Final Answer:")[-1].strip()
                logger.info(t('report.sectionGenDone', title=section.title, count=tool_calls_count))

                if self.report_logger:
                    self.report_logger.log_section_content(
                        section_title=section.title,
                        section_index=section_index,
                        content=final_answer,
                        tool_calls_count=tool_calls_count
                    )
                return final_answer

            # ── Caso2LLM Ferramenta ──
            if has_tool_calls:
                # Ferramenta →  Final Answer
                if tool_calls_count >= self.MAX_TOOL_CALLS_PER_SECTION:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": REACT_TOOL_LIMIT_MSG.format(
                            tool_calls_count=tool_calls_count,
                            max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        ),
                    })
                    continue

                # Ferramenta
                call = tool_calls[0]
                if len(tool_calls) > 1:
                    logger.info(t('report.multiToolOnlyFirst', total=len(tool_calls), toolName=call['name']))

                if self.report_logger:
                    self.report_logger.log_tool_call(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        parameters=call.get("parameters", {}),
                        iteration=iteration + 1
                    )

                result = self._execute_tool(
                    call["name"],
                    call.get("parameters", {}),
                    report_context=report_context
                )

                if self.report_logger:
                    self.report_logger.log_tool_result(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        result=result,
                        iteration=iteration + 1
                    )

                tool_calls_count += 1
                used_tools.add(call['name'])

                # Ferramenta
                unused_tools = all_tools - used_tools
                unused_hint = ""
                if unused_tools and tool_calls_count < self.MAX_TOOL_CALLS_PER_SECTION:
                    unused_hint = REACT_UNUSED_TOOLS_HINT.format(unused_list="、".join(unused_tools))

                messages.append({"role": "assistant", "content": response})
                messages.append({
                    "role": "user",
                    "content": REACT_OBSERVATION_TEMPLATE.format(
                        tool_name=call["name"],
                        result=result,
                        tool_calls_count=tool_calls_count,
                        max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        used_tools_str=", ".join(used_tools),
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # ── Caso3Ferramenta Final Answer ──
            messages.append({"role": "assistant", "content": response})

            if tool_calls_count < min_tool_calls:
                # FerramentaFerramenta
                unused_tools = all_tools - used_tools
                unused_hint = f"(Estas ferramentas ainda não foram usadas, recomendamos experimentá-las: {', '.join(unused_tools)})" if unused_tools else ""

                messages.append({
                    "role": "user",
                    "content": REACT_INSUFFICIENT_TOOLS_MSG_ALT.format(
                        tool_calls_count=tool_calls_count,
                        min_tool_calls=min_tool_calls,
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # FerramentaLLM Conteúdo "Final Answer:"
            # Conteúdo
            logger.info(t('report.sectionNoPrefix', title=section.title, count=tool_calls_count))
            final_answer = response.strip()

            if self.report_logger:
                self.report_logger.log_section_content(
                    section_title=section.title,
                    section_index=section_index,
                    content=final_answer,
                    tool_calls_count=tool_calls_count
                )
            return final_answer
        
        # GerarConteúdo
        logger.warning(t('report.sectionMaxIter', title=section.title))
        messages.append({"role": "user", "content": REACT_FORCE_FINAL_MSG})
        
        response = self.llm.chat(
            messages=messages,
            temperature=0.5,
            max_tokens=4096
        )

        # Encerramento forçado LLM  None
        if response is None:
            logger.error(t('report.sectionForceFailed', title=section.title))
            final_answer = t('report.sectionGenFailedContent')
        elif "Final Answer:" in response:
            final_answer = response.split("Final Answer:")[-1].strip()
        else:
            final_answer = response
        
        # SeçãoConteúdoGerar
        if self.report_logger:
            self.report_logger.log_section_content(
                section_title=section.title,
                section_index=section_index,
                content=final_answer,
                tool_calls_count=tool_calls_count
            )
        
        return final_answer
    
    def generate_report(
        self, 
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        report_id: Optional[str] = None
    ) -> Report:
        """
        Gerar relatório completoSeção
        
        SeçãoGerarPastaRelatório
        reports/{report_id}/
            meta.json       - Relatório
            outline.json    - Outline do relatório
            progress.json   - Gerar
            section_01.md   - 1Seção
            section_02.md   - 2Seção
            ...
            full_report.md  - Relatório
        
        Args:
            progress_callback: Função callback de progresso (stage, progress, message)
            report_id: RelatórioIDGerar
            
        Returns:
            Report: Relatório
        """
        import uuid
        
        # report_idGerar
        if not report_id:
            report_id = f"report_{uuid.uuid4().hex[:12]}"
        start_time = datetime.now()
        
        report = Report(
            report_id=report_id,
            simulation_id=self.simulation_id,
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement,
            status=ReportStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        
        # ConcluídoSeção
        completed_section_titles = []
        
        try:
            # RelatórioPasta
            ReportManager._ensure_report_folder(report_id)
            
            # agent_log.jsonl
            self.report_logger = ReportLogger(report_id)
            self.report_logger.log_start(
                simulation_id=self.simulation_id,
                graph_id=self.graph_id,
                simulation_requirement=self.simulation_requirement
            )
            
            # console_log.txt
            self.console_logger = ReportConsoleLogger(report_id)
            
            ReportManager.update_progress(
                report_id, "pending", 0, t('progress.initReport'),
                completed_sections=[]
            )
            ReportManager.save_report(report)
            
            # 1: Outline
            report.status = ReportStatus.PLANNING
            ReportManager.update_progress(
                report_id, "planning", 5, t('progress.startPlanningOutline'),
                completed_sections=[]
            )
            
            self.report_logger.log_planning_start()
            
            if progress_callback:
                progress_callback("planning", 0, t('progress.startPlanningOutline'))
            
            outline = self.plan_outline(
                progress_callback=lambda stage, prog, msg: 
                    progress_callback(stage, prog // 5, msg) if progress_callback else None
            )
            report.outline = outline
            
            self.report_logger.log_planning_complete(outline.to_dict())
            
            # Outline
            ReportManager.save_outline(report_id, outline)
            ReportManager.update_progress(
                report_id, "planning", 15, t('progress.outlineDone', count=len(outline.sections)),
                completed_sections=[]
            )
            ReportManager.save_report(report)
            
            logger.info(t('report.outlineSavedToFile', reportId=report_id))
            
            # 2: SeçãoGerarSeção
            report.status = ReportStatus.GENERATING
            
            total_sections = len(outline.sections)
            generated_sections = []  # Conteúdo
            
            for i, section in enumerate(outline.sections):
                section_num = i + 1
                base_progress = 20 + int((i / total_sections) * 70)
                
                # Atualizar progresso
                ReportManager.update_progress(
                    report_id, "generating", base_progress,
                    t('progress.generatingSection', title=section.title, current=section_num, total=total_sections),
                    current_section=section.title,
                    completed_sections=completed_section_titles
                )

                if progress_callback:
                    progress_callback(
                        "generating",
                        base_progress,
                        t('progress.generatingSection', title=section.title, current=section_num, total=total_sections)
                    )
                
                # GerarSeçãoConteúdo
                section_content = self._generate_section_react(
                    section=section,
                    outline=outline,
                    previous_sections=generated_sections,
                    progress_callback=lambda stage, prog, msg:
                        progress_callback(
                            stage, 
                            base_progress + int(prog * 0.7 / total_sections),
                            msg
                        ) if progress_callback else None,
                    section_index=section_num
                )
                
                section.content = section_content
                
                # ── Pós-processamento: traduzir conteúdo chinês para PT-BR ──
                if section_content and self._has_chinese(section_content):
                    logger.warning(f"Chinês detectado na seção '{section.title}' — traduzindo...")
                    try:
                        tr = self.llm.chat(
                            messages=[
                                {"role": "system", "content": "Traduza o texto abaixo integralmente para português do Brasil. Mantenha toda a formatação Markdown (negrito, listas, citações). NÃO deixe nenhuma palavra em chinês."},
                                {"role": "user", "content": section_content}
                            ],
                            temperature=0.1
                        )
                        if tr and not self._has_chinese(tr):
                            section.content = tr
                            section_content = tr
                            logger.info(f"Seção '{section.title}' traduzida com sucesso")
                    except Exception as te:
                        logger.error(f"Falha ao traduzir seção: {te}")
                
                generated_sections.append(f"## {section.title}\n\n{section_content}")

                # Salvar seção
                ReportManager.save_section(report_id, section_num, section)
                completed_section_titles.append(section.title)

                # Registrar log de conclusão da seção
                full_section_content = f"## {section.title}\n\n{section_content}"

                if self.report_logger:
                    self.report_logger.log_section_full_complete(
                        section_title=section.title,
                        section_index=section_num,
                        full_content=full_section_content.strip()
                    )

                logger.info(t('report.sectionSaved', reportId=report_id, sectionNum=f"{section_num:02d}"))
                
                # Atualizar progresso
                ReportManager.update_progress(
                    report_id, "generating", 
                    base_progress + int(70 / total_sections),
                    t('progress.sectionDone', title=section.title),
                    current_section=None,
                    completed_sections=completed_section_titles
                )
            
            # 3: Relatório
            if progress_callback:
                progress_callback("generating", 95, t('progress.assemblingReport'))
            
            ReportManager.update_progress(
                report_id, "generating", 95, t('progress.assemblingReport'),
                completed_sections=completed_section_titles
            )
            
            # ReportManagerRelatório
            report.markdown_content = ReportManager.assemble_full_report(report_id, outline)
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.now().isoformat()
            
            total_time_seconds = (datetime.now() - start_time).total_seconds()
            
            # Relatório
            if self.report_logger:
                self.report_logger.log_report_complete(
                    total_sections=total_sections,
                    total_time_seconds=total_time_seconds
                )
            
            # Relatório
            ReportManager.save_report(report)
            ReportManager.update_progress(
                report_id, "completed", 100, t('progress.reportComplete'),
                completed_sections=completed_section_titles
            )
            
            if progress_callback:
                progress_callback("completed", 100, t('progress.reportComplete'))
            
            logger.info(t('report.reportGenDone', reportId=report_id))
            
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report
            
        except Exception as e:
            logger.error(t('report.reportGenFailed', error=str(e)))
            report.status = ReportStatus.FAILED
            report.error = str(e)
            
            if self.report_logger:
                self.report_logger.log_error(str(e), "failed")
            
            # Falhou
            try:
                ReportManager.save_report(report)
                ReportManager.update_progress(
                    report_id, "failed", -1, t('progress.reportFailed', error=str(e)),
                    completed_sections=completed_section_titles
                )
            except Exception:
                pass  # Falhou
            
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report
    
    def chat(
        self, 
        message: str,
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Dialogar com o Report Agent
        
        AgentBuscaFerramenta
        
        Args:
            message: 
            chat_history: 
            
        Returns:
            {
                "response": "Resposta do Agente",
                "tool_calls": [Lista de ferramentas chamadas],
                "sources": [Fontes de informação]
            }
        """
        logger.info(t('report.agentChat', message=message[:50]))
        
        chat_history = chat_history or []
        
        # GerarRelatórioConteúdo
        report_content = ""
        try:
            report = ReportManager.get_report_by_simulation(self.simulation_id)
            if report and report.markdown_content:
                # Relatório
                report_content = report.markdown_content[:15000]
                if len(report.markdown_content) > 15000:
                    report_content += "\n\n... [conteúdo do relatório truncado] ..."
        except Exception as e:
            logger.warning(t('report.fetchReportFailed', error=e))
        
        system_prompt = CHAT_SYSTEM_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            report_content=report_content if report_content else "(relatório ainda não disponível)",
            tools_description=self._get_tools_description(),
        )
        system_prompt = f"{system_prompt}\n\n{get_language_instruction()}"

        messages = [{"role": "system", "content": system_prompt}]
        
        for h in chat_history[-10:]:  # 
            messages.append(h)
        
        messages.append({
            "role": "user", 
            "content": message
        })
        
        # ReACT
        tool_calls_made = []
        max_iterations = 2  # 
        
        for iteration in range(max_iterations):
            response = self.llm.chat(
                messages=messages,
                temperature=0.5
            )
            
            # Ferramenta
            tool_calls = self._parse_tool_calls(response)
            
            if not tool_calls:
                # Ferramenta
                clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', response, flags=re.DOTALL)
                clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
                
                return {
                    "response": clean_response.strip(),
                    "tool_calls": tool_calls_made,
                    "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
                }
            
            # Executar chamada de ferramenta
            tool_results = []
            for call in tool_calls[:1]:  # 1Ferramenta
                if len(tool_calls_made) >= self.MAX_TOOL_CALLS_PER_CHAT:
                    break
                result = self._execute_tool(call["name"], call.get("parameters", {}))
                tool_results.append({
                    "tool": call["name"],
                    "result": result[:1500]  # Resultado
                })
                tool_calls_made.append(call)
            
            # Resultado
            messages.append({"role": "assistant", "content": response})
            observation = "\n".join([f"[Resultado {r['tool']}]\n{r['result']}" for r in tool_results])
            messages.append({
                "role": "user",
                "content": observation + CHAT_OBSERVATION_SUFFIX
            })
        
        final_response = self.llm.chat(
            messages=messages,
            temperature=0.5
        )
        
        clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', final_response, flags=re.DOTALL)
        clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
        
        return {
            "response": clean_response.strip(),
            "tool_calls": tool_calls_made,
            "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
        }


class ReportManager:
    """
    Gerenciador de relatórios
    
    RelatórioBusca
    
    Seção
    reports/
      {report_id}/
        meta.json          - Relatório
        outline.json       - Outline do relatório
        progress.json      - Gerar
        section_01.md      - 1Seção
        section_02.md      - 2Seção
        ...
        full_report.md     - Relatório
    """
    
    # Relatório
    REPORTS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'reports')
    
    @classmethod
    def _ensure_reports_dir(cls):
        """Garantir que o diretório raiz dos relatórios exista"""
        os.makedirs(cls.REPORTS_DIR, exist_ok=True)
    
    @classmethod
    def _get_report_folder(cls, report_id: str) -> str:
        """Obter relatórioPasta"""
        return os.path.join(cls.REPORTS_DIR, report_id)
    
    @classmethod
    def _ensure_report_folder(cls, report_id: str) -> str:
        """RelatórioPasta"""
        folder = cls._get_report_folder(report_id)
        os.makedirs(folder, exist_ok=True)
        return folder
    
    @classmethod
    def _get_report_path(cls, report_id: str) -> str:
        """Obter relatório"""
        return os.path.join(cls._get_report_folder(report_id), "meta.json")
    
    @classmethod
    def _get_report_markdown_path(cls, report_id: str) -> str:
        """RelatórioMarkdown"""
        return os.path.join(cls._get_report_folder(report_id), "full_report.md")
    
    @classmethod
    def _get_outline_path(cls, report_id: str) -> str:
        """Outline"""
        return os.path.join(cls._get_report_folder(report_id), "outline.json")
    
    @classmethod
    def _get_progress_path(cls, report_id: str) -> str:
        """"""
        return os.path.join(cls._get_report_folder(report_id), "progress.json")
    
    @classmethod
    def _get_section_path(cls, report_id: str, section_index: int) -> str:
        """SeçãoMarkdown"""
        return os.path.join(cls._get_report_folder(report_id), f"section_{section_index:02d}.md")
    
    @classmethod
    def _get_agent_log_path(cls, report_id: str) -> str:
        """ Agent """
        return os.path.join(cls._get_report_folder(report_id), "agent_log.jsonl")
    
    @classmethod
    def _get_console_log_path(cls, report_id: str) -> str:
        """"""
        return os.path.join(cls._get_report_folder(report_id), "console_log.txt")
    
    @classmethod
    def get_console_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """
        Conteúdo
        
        RelatórioGerarINFOWARNING
         agent_log.jsonl 
        
        Args:
            report_id: RelatórioID
            from_line: 0 
            
        Returns:
            {
                "logs": [],
                "total_lines": ,
                "from_line": ,
                "has_more": 
            }
        """
        log_path = cls._get_console_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    logs.append(line.rstrip('\n\r'))
        
        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # 
        }
    
    @classmethod
    def get_console_log_stream(cls, report_id: str) -> List[str]:
        """
        
        Args:
            report_id: RelatórioID
            
        Returns:
        """
        result = cls.get_console_log(report_id, from_line=0)
        return result["logs"]
    
    @classmethod
    def get_agent_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """
         Agent Conteúdo
        
        Args:
            report_id: RelatórioID
            from_line: 0 
            
        Returns:
            {
                "logs": [],
                "total_lines": ,
                "from_line": ,
                "has_more": 
            }
        """
        log_path = cls._get_agent_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    try:
                        log_entry = json.loads(line.strip())
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        # Falhou
                        continue
        
        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # 
        }
    
    @classmethod
    def get_agent_log_stream(cls, report_id: str) -> List[Dict[str, Any]]:
        """
         Agent 
        
        Args:
            report_id: RelatórioID
            
        Returns:
        """
        result = cls.get_agent_log(report_id, from_line=0)
        return result["logs"]
    
    @classmethod
    def save_outline(cls, report_id: str, outline: ReportOutline) -> None:
        """
        Salvar outline do relatório
        
        """
        cls._ensure_report_folder(report_id)
        
        with open(cls._get_outline_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(outline.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(t('report.outlineSaved', reportId=report_id))
    
    @classmethod
    def save_section(
        cls,
        report_id: str,
        section_index: int,
        section: ReportSection
    ) -> str:
        """
        Seção

        SeçãoGerarSeção

        Args:
            report_id: RelatórioID
            section_index: Seção1
            section: Seção

        Returns:
        """
        cls._ensure_report_folder(report_id)

        # SeçãoMarkdownConteúdo -
        cleaned_content = cls._clean_section_content(section.content, section.title)
        md_content = f"## {section.title}\n\n"
        if cleaned_content:
            md_content += f"{cleaned_content}\n\n"

        file_suffix = f"section_{section_index:02d}.md"
        file_path = os.path.join(cls._get_report_folder(report_id), file_suffix)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        logger.info(t('report.sectionFileSaved', reportId=report_id, fileSuffix=file_suffix))
        return file_path
    
    @classmethod
    def _clean_section_content(cls, content: str, section_title: str) -> str:
        """
        SeçãoConteúdo
        
        1. ConteúdoSeçãoMarkdown
        2.  ### 
        
        Args:
            content: Conteúdo
            section_title: Seção
            
        Returns:
            Conteúdo
        """
        import re
        
        if not content:
            return content
        
        content = content.strip()
        lines = content.split('\n')
        cleaned_lines = []
        skip_next_empty = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Markdown
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            
            if heading_match:
                level = len(heading_match.group(1))
                title_text = heading_match.group(2).strip()
                
                # Seção5
                if i < 5:
                    if title_text == section_title or title_text.replace(' ', '') == section_title.replace(' ', ''):
                        skip_next_empty = True
                        continue
                
                # #, ##, ###, ####
                # SeçãoConteúdo
                cleaned_lines.append(f"**{title_text}**")
                cleaned_lines.append("")  # 
                continue
            
            if skip_next_empty and stripped == '':
                skip_next_empty = False
                continue
            
            skip_next_empty = False
            cleaned_lines.append(line)
        
        while cleaned_lines and cleaned_lines[0].strip() == '':
            cleaned_lines.pop(0)
        
        while cleaned_lines and cleaned_lines[0].strip() in ['---', '***', '___']:
            cleaned_lines.pop(0)
            while cleaned_lines and cleaned_lines[0].strip() == '':
                cleaned_lines.pop(0)
        
        return '\n'.join(cleaned_lines)
    
    @classmethod
    def update_progress(
        cls, 
        report_id: str, 
        status: str, 
        progress: int, 
        message: str,
        current_section: str = None,
        completed_sections: List[str] = None
    ) -> None:
        """
        RelatórioGerar
        
        progress.json
        """
        cls._ensure_report_folder(report_id)
        
        progress_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "current_section": current_section,
            "completed_sections": completed_sections or [],
            "updated_at": datetime.now().isoformat()
        }
        
        with open(cls._get_progress_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def get_progress(cls, report_id: str) -> Optional[Dict[str, Any]]:
        """Obter relatórioGerar"""
        path = cls._get_progress_path(report_id)
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @classmethod
    def get_generated_sections(cls, report_id: str) -> List[Dict[str, Any]]:
        """
        GerarSeção
        
        Seção
        """
        folder = cls._get_report_folder(report_id)
        
        if not os.path.exists(folder):
            return []
        
        sections = []
        for filename in sorted(os.listdir(folder)):
            if filename.startswith('section_') and filename.endswith('.md'):
                file_path = os.path.join(folder, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Seção
                parts = filename.replace('.md', '').split('_')
                section_index = int(parts[1])

                sections.append({
                    "filename": filename,
                    "section_index": section_index,
                    "content": content
                })

        return sections
    
    @classmethod
    def assemble_full_report(cls, report_id: str, outline: ReportOutline) -> str:
        """
        Relatório
        
        SeçãoRelatório
        """
        folder = cls._get_report_folder(report_id)
        
        # Relatório
        md_content = f"# {outline.title}\n\n"
        md_content += f"> {outline.summary}\n\n"
        md_content += f"---\n\n"
        
        # Seção
        sections = cls.get_generated_sections(report_id)
        for section_info in sections:
            md_content += section_info["content"]
        
        # Relatório
        md_content = cls._post_process_report(md_content, outline)
        
        # Relatório
        full_path = cls._get_report_markdown_path(report_id)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(t('report.fullReportAssembled', reportId=report_id))
        return md_content
    
    @classmethod
    def _post_process_report(cls, content: str, outline: ReportOutline) -> str:
        """
        RelatórioConteúdo
        
        1. 
        2. Relatório(#)Seção(##)(###, ####)
        3. 
        
        Args:
            content: RelatórioConteúdo
            outline: Outline do relatório
            
        Returns:
            Conteúdo
        """
        import re
        
        lines = content.split('\n')
        processed_lines = []
        prev_was_heading = False
        
        # OutlineSeção
        section_titles = set()
        for section in outline.sections:
            section_titles.add(section.title)
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                # 5Conteúdo
                is_duplicate = False
                for j in range(max(0, len(processed_lines) - 5), len(processed_lines)):
                    prev_line = processed_lines[j].strip()
                    prev_match = re.match(r'^(#{1,6})\s+(.+)$', prev_line)
                    if prev_match:
                        prev_title = prev_match.group(2).strip()
                        if prev_title == title:
                            is_duplicate = True
                            break
                
                if is_duplicate:
                    i += 1
                    while i < len(lines) and lines[i].strip() == '':
                        i += 1
                    continue
                
                # - # (level=1) Relatório
                # - ## (level=2) Seção
                # - ###  (level>=3)
                
                if level == 1:
                    if title == outline.title:
                        # Relatório
                        processed_lines.append(line)
                        prev_was_heading = True
                    elif title in section_titles:
                        # Seção###
                        processed_lines.append(f"## {title}")
                        prev_was_heading = True
                    else:
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                elif level == 2:
                    if title in section_titles or title == outline.title:
                        # Seção
                        processed_lines.append(line)
                        prev_was_heading = True
                    else:
                        # Seção
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                else:
                    processed_lines.append(f"**{title}**")
                    processed_lines.append("")
                    prev_was_heading = False
                
                i += 1
                continue
            
            elif stripped == '---' and prev_was_heading:
                i += 1
                continue
            
            elif stripped == '' and prev_was_heading:
                if processed_lines and processed_lines[-1].strip() != '':
                    processed_lines.append(line)
                prev_was_heading = False
            
            else:
                processed_lines.append(line)
                prev_was_heading = False
            
            i += 1
        
        result_lines = []
        empty_count = 0
        for line in processed_lines:
            if line.strip() == '':
                empty_count += 1
                if empty_count <= 2:
                    result_lines.append(line)
            else:
                empty_count = 0
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    @classmethod
    def save_report(cls, report: Report) -> None:
        """RelatórioRelatório"""
        cls._ensure_report_folder(report.report_id)
        
        # JSON
        with open(cls._get_report_path(report.report_id), 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        
        # Outline
        if report.outline:
            cls.save_outline(report.report_id, report.outline)
        
        # MarkdownRelatório
        if report.markdown_content:
            with open(cls._get_report_markdown_path(report.report_id), 'w', encoding='utf-8') as f:
                f.write(report.markdown_content)
        
        logger.info(t('report.reportSaved', reportId=report.report_id))
    
    @classmethod
    def get_report(cls, report_id: str) -> Optional[Report]:
        """Obter relatório"""
        path = cls._get_report_path(report_id)
        
        if not os.path.exists(path):
            # Compatível com formato antigoreports
            old_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.json")
            if os.path.exists(old_path):
                path = old_path
            else:
                return None
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Report
        outline = None
        if data.get('outline'):
            outline_data = data['outline']
            sections = []
            for s in outline_data.get('sections', []):
                sections.append(ReportSection(
                    title=s['title'],
                    content=s.get('content', '')
                ))
            outline = ReportOutline(
                title=outline_data['title'],
                summary=outline_data['summary'],
                sections=sections
            )
        else:
            # Fallback: carregar outline.json quando report.json estiver desatualizado
            outline_path = cls._get_outline_path(report_id)
            if os.path.exists(outline_path):
                try:
                    with open(outline_path, 'r', encoding='utf-8') as f:
                        outline_data = json.load(f)
                    sections = []
                    for s in outline_data.get('sections', []):
                        sections.append(ReportSection(
                            title=s.get('title', ''),
                            content=s.get('content', '')
                        ))
                    outline = ReportOutline(
                        title=outline_data.get('title', 'Relatório de Previsão'),
                        summary=outline_data.get('summary', ''),
                        sections=sections
                    )
                except Exception:
                    outline = None

        # Hidratar conteúdo de seções a partir dos arquivos section_XX.md
        # Isso evita tela vazia no primeiro carregamento enquanto report.json ainda não refletiu tudo.
        if outline and outline.sections:
            generated_sections = cls.get_generated_sections(report_id)
            if generated_sections:
                by_index = {s.get("section_index"): s.get("content", "") for s in generated_sections}
                for i, section in enumerate(outline.sections, start=1):
                    if not (section.content or '').strip():
                        content = by_index.get(i, "")
                        if content:
                            section.content = content

        # markdown_contentfull_report.md
        markdown_content = data.get('markdown_content', '')
        if not markdown_content:
            full_report_path = cls._get_report_markdown_path(report_id)
            if os.path.exists(full_report_path):
                with open(full_report_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
        
        return Report(
            report_id=data['report_id'],
            simulation_id=data['simulation_id'],
            graph_id=data['graph_id'],
            simulation_requirement=data['simulation_requirement'],
            status=ReportStatus(data['status']),
            outline=outline,
            markdown_content=markdown_content,
            created_at=data.get('created_at', ''),
            completed_at=data.get('completed_at', ''),
            error=data.get('error')
        )
    
    @classmethod
    def get_report_by_simulation(cls, simulation_id: str) -> Optional[Report]:
        """ID da simulaçãoObter relatório"""
        cls._ensure_reports_dir()
        
        for item in os.listdir(cls.REPORTS_DIR):
            item_path = os.path.join(cls.REPORTS_DIR, item)
            # Novo formato：Pasta
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report and report.simulation_id == simulation_id:
                    return report
            # Compatível com formato antigo：Arquivo JSON
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report and report.simulation_id == simulation_id:
                    return report
        
        return None
    
    @classmethod
    def list_reports(cls, simulation_id: Optional[str] = None, limit: int = 50) -> List[Report]:
        """Listar relatórios"""
        cls._ensure_reports_dir()
        
        reports = []
        for item in os.listdir(cls.REPORTS_DIR):
            item_path = os.path.join(cls.REPORTS_DIR, item)
            # Novo formato：Pasta
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
            # Compatível com formato antigo：Arquivo JSON
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
        
        reports.sort(key=lambda r: r.created_at, reverse=True)
        
        return reports[:limit]
    
    @classmethod
    def delete_report(cls, report_id: str) -> bool:
        """RelatórioPasta"""
        import shutil
        
        folder_path = cls._get_report_folder(report_id)
        
        # Novo formatoPasta
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
            logger.info(t('report.reportFolderDeleted', reportId=report_id))
            return True
        
        # Compatível com formato antigo
        deleted = False
        old_json_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.json")
        old_md_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.md")
        
        if os.path.exists(old_json_path):
            os.remove(old_json_path)
            deleted = True
        if os.path.exists(old_md_path):
            os.remove(old_md_path)
            deleted = True
        
        return deleted
