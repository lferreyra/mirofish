"""
AUGUR Report Prompts v2 — Pipeline reconstruído de trás pra frente.

Substitui os prompts de report_agent.py para gerar JSON estruturado
no formato definido por report_schema.py.

O loop ReAct (tool calls → data gathering) permanece inalterado.
O que muda: o "Final Answer" agora é JSON tipado, não texto livre.

Uso:
    from app.schemas.report_schema import AugurReportSchema
    from app.services.report_prompts_v2 import (
        PLAN_SYSTEM_PROMPT_V2,
        PLAN_USER_PROMPT_V2,
        get_section_prompt,
        SECTION_OUTPUT_SCHEMAS,
        REACT_OBSERVATION_TEMPLATE_V2,
    )
"""

import json

# ============================================================
# PLAN PROMPT — Gera o plano com 16 seções fixas
# ============================================================
# Diferença da v1: não pede ao LLM para "inventar" seções.
# As 16 seções são FIXAS. O LLM apenas gera o título e
# as instruções de busca para cada seção.
# ============================================================

PLAN_SYSTEM_PROMPT_V2 = """\
Você é o estrategista-chefe do AUGUR — plataforma de previsão de mercado por IA.
Seu relatório substitui uma consultoria de R$200.000.

══════════════════════════════════════════════════════════════
【MISSÃO】
══════════════════════════════════════════════════════════════

Gerar o PLANO de um relatório de previsão com EXATAMENTE 16 seções.
As seções são FIXAS — você NÃO inventa seções novas.
Você gera o título específico e as instruções de busca para cada seção.

══════════════════════════════════════════════════════════════
【AS 16 SEÇÕES OBRIGATÓRIAS】
══════════════════════════════════════════════════════════════

1. resumo_executivo — Veredicto GO/NO-GO/AJUSTAR + frase-chave + 5 KPIs
2. dashboard_kpis — Métricas quantitativas: ticket, margem, break-even, investimento
3. cenarios_futuros — EXATAMENTE 3 cenários com probabilidades somando 100%
4. cenarios_financeiros — Projeção de faturamento 24 meses por cenário
5. fatores_risco — 5-7 riscos com probabilidade e impacto
6. analise_emocional — 6 emoções com % + evolução temporal 24 meses
7. perfis_agentes — Cada agente com nome, perfil, posição e citação-chave
8. mapa_forcas — Blocos de poder com base de clientes quantificada
9. cronologia — 4 fases: Curiosidade/Teste/Virada/Disciplina
10. padroes_emergentes — 5-7 padrões surpreendentes
11. recomendacoes — 3-5 recomendações com STACK RANKING (#1 decide sobrevivência)
12. checklist_go — 8-10 condições mensuráveis para transformar AJUSTAR em GO
13. previsoes_confianca — 6-8 previsões com probabilidade ± margem de erro
14. posicionamento — Percebido vs desejado + 3 rótulos a evitar + posicionamento vencedor
15. roi_analise — Custo de errar vs custo de saber + ROI multiplicador
16. sintese_final — Radar 5 eixos + veredicto + 3 direcionamentos

══════════════════════════════════════════════════════════════
【OUTPUT — JSON OBRIGATÓRIO】
══════════════════════════════════════════════════════════════

{
    "title": "Relatório de Previsão: [tema] — [VEREDICTO]",
    "summary": "VEREDICTO: [GO/NO-GO/AJUSTAR]. [Uma frase de 25 palavras]",
    "sections": [
        {
            "key": "resumo_executivo",
            "title": "Resumo Executivo",
            "search_instructions": "Buscar: veredicto geral, KPIs principais, citações de decisão..."
        },
        ... (16 seções, cada uma com key, title e search_instructions)
    ]
}

REGRAS:
- sections DEVE ter EXATAMENTE 16 elementos
- cada section DEVE ter "key" correspondendo à lista acima
- search_instructions guia o ReAct loop sobre O QUE buscar nas ferramentas
- 100% português do Brasil
- ZERO caracteres chineses
"""


PLAN_USER_PROMPT_V2 = """\
【Cenário de previsão】
Requisito da simulação: {simulation_requirement}

【Escala do mundo simulado】
- Entidades na simulação: {total_nodes}
- Relações entre entidades: {total_edges}
- Distribuição de tipos: {entity_types}
- Agentes ativos: {total_entities}

【Amostra de fatos simulados】
{related_facts_json}

Gere o plano do relatório com as 16 seções obrigatórias.
Adapte os search_instructions ao contexto específico desta simulação.
"""


# ============================================================
# SECTION PROMPTS — Um prompt por tipo de seção
# ============================================================
# Cada seção tem:
# - Instruções específicas de O QUE buscar
# - O schema JSON EXATO que deve retornar no "Final Answer"
# - Exemplo de output para o LLM seguir
# ============================================================

# Schema de output por seção (o que o LLM deve retornar como JSON)
SECTION_OUTPUT_SCHEMAS = {
    "resumo_executivo": {
        "tipo": "GO | NO-GO | AJUSTAR",
        "score_viabilidade": "0-100 (int)",
        "frase_chave": "max 200 chars, a frase que resume tudo",
        "resumo_executivo": "2-4 parágrafos narrativos com dados da simulação",
        "leitura_para_decisao": "1 parágrafo: o que o dono deve fazer segunda-feira",
        "top5_fatos": [{"titulo": "max 60 chars", "descricao": "1-2 frases com dados"}],
    },
    "dashboard_kpis": {
        "ticket_medio": "range em R$ (ex: R$160-240)",
        "volume_breakeven": "quantidade/mês para break-even",
        "margem_bruta_alvo": "range % esperado",
        "capital_giro_necessario": "range R$ para operação",
        "recompra_alvo": "% mínimo para sobrevivência",
        "vendas_por_indicacao": "% esperado M12-24",
        "erosao_margem_sazonal": "% de perda em datas fortes",
        "breakeven_cenario1": "período (ex: M11-15)",
        "contatos_mes_inicial": "range contatos/mês M1-3",
        "conversao_inicial": "% de conversão M1-3",
        "faturamento_maduro": "R$/mês quando estável",
        "prob_sobrevivencia_24m": "% probabilidade",
        "investimento_total_estimado": "R$ total necessário",
        "composicao_investimento": [{"item": "nome", "valor": "R$ range"}],
        "sinais_consolidacao": ["lista de sinais verdes"],
        "sinais_alerta": ["lista de sinais amarelos"],
        "sinais_risco_critico": ["lista de sinais vermelhos"],
    },
    "cenarios_futuros": {
        "cenarios": [
            {
                "nome": "título descritivo do cenário",
                "probabilidade": "int 0-100 (soma dos 3 = 100)",
                "impacto_financeiro": "positivo moderado | negativo relevante | etc",
                "breakeven": "período ou 'Não ocorre em 24 meses'",
                "faturamento_m24": "R$/mês no mês 24",
                "margem_bruta": "range %",
                "recompra": "range %",
                "risco_central": "principal ameaça deste cenário",
                "capital_giro": "R$ necessário",
                "descricao": "2-3 parágrafos com dados da simulação",
                "citacao_agente": "a citação mais reveladora",
                "projecao_faturamento_24m": "[lista de 25 floats: faturamento R$mil/mês, M0 a M24]"
            }
        ],
        "ponto_bifurcacao": "o que separa os cenários (1-2 frases)",
    },
    "cenarios_financeiros": "MESMOS DADOS de cenarios_futuros (esta seção usa os mesmos dados para renderizar o gráfico area chart e a tabela comparativa)",
    "fatores_risco": {
        "texto_introducao": "1-2 frases contextuais",
        "riscos": [
            {
                "numero": "int 1-7",
                "titulo": "TEXTO COMPLETO, NUNCA truncar (max 80 chars)",
                "probabilidade": "int 0-100",
                "impacto": "Alto | Medio | Baixo",
                "descricao": "2-3 frases com dados",
                "citacao_agente": "a citação mais reveladora",
            }
        ],
    },
    "analise_emocional": {
        "emocoes": [
            {"nome": "Confiança|Ceticismo|Empolgação|Medo|FOMO|Indiferença", "percentual": "int 0-100"}
        ],
        "saldo_positivo_vs_negativo": "ex: 49% vs 36%",
        "texto_confianca": "parágrafo sobre confiança",
        "citacao_confianca": "citação",
        "texto_ceticismo": "parágrafo",
        "citacao_ceticismo": "citação",
        "texto_empolgacao": "parágrafo",
        "texto_medo": "parágrafo",
        "evolucao_24m": {
            "confianca": "[25 floats: intensidade % M0 a M24]",
            "ceticismo": "[25 floats]",
            "empolgacao": "[25 floats]",
            "medo": "[25 floats]"
        },
    },
    "perfis_agentes": [
        {
            "nome": "nome do agente",
            "descricao": "perfil demográfico em 1 linha",
            "tipo": "Apoiador | Neutro | Resistente | Cauteloso",
            "posicao_espectro": "float 0.0 (apoiador) a 1.0 (resistente)",
            "citacao_chave": "a fala mais reveladora",
            "papel_na_dinamica": "ex: Early adopter pragmático",
        }
    ],
    "mapa_forcas": {
        "blocos": [
            {
                "nome": "ex: Bloco dominante: lider de mercado + base fidelizada",
                "base_clientes": "ex: 3.000-4.500 clientes ativos",
                "descricao": "2-3 frases",
                "poder_relativo": "int 1-10",
                "citacao": "citação ou null",
            }
        ],
        "hierarquia_poder": "ranking textual: 1. X (motivo). 2. Y (motivo). ...",
        "coalizao_entrante": "quem pode ser aliado do entrante",
    },
    "cronologia": {
        "fases": [
            {
                "nome": "Curiosidade | Teste | Virada | Disciplina",
                "periodo": "ex: M0-3",
                "mes_inicio": "int",
                "mes_fim": "int",
                "descricao": "2-3 frases",
                "citacao": "citação do agente",
                "marcos": ["lista de marcos importantes nesta fase"],
            }
        ],
    },
    "padroes_emergentes": [
        {"numero": "int", "titulo": "título do padrão", "descricao": "2-3 frases"}
    ],
    "recomendacoes": [
        {
            "rank": "int 1-5 (#1 = mais importante)",
            "titulo": "ex: #1 Acao prioritaria que decide viabilidade do negocio",
            "descricao": "2-3 frases",
            "citacao": "citação de suporte ou null",
            "impacto_relativo": "int 0-100 (para barra de stack ranking)",
        }
    ],
    "checklist_go": [
        {
            "titulo": "condição mensurável",
            "timing": "Pré-lançamento | Mês 1 | M1-3 | M6-12 | Permanente",
            "justificativa": "por que isso é necessário",
            "condicao_mensuravel": "como medir se foi atingido",
            "prioridade": "Urgente | Alta | Media | Baixa",
        }
    ],
    "previsoes_confianca": [
        {
            "periodo": "ex: M1-3",
            "titulo": "descrição da previsão",
            "probabilidade": "int 0-100",
            "margem_erro": "int (± p.p.)",
            "descricao": "métricas concretas",
        }
    ],
    "posicionamento": {
        "percebido_descricao": "como o mercado vai ler inicialmente",
        "percebido_citacao": "citação",
        "desejado_descricao": "como deveria ser lido",
        "desejado_citacao": "citação",
        "rotulos_a_evitar": ["lista de 3 rótulos perigosos"],
        "posicionamento_vencedor": "ex: Lá eles resolvem.",
        "players": [
            {"nome": "player", "x": "int 0-100 (preço)", "y": "int 0-100 (funcional→aspiracional)", "papel": "papel"}
        ],
    },
    "roi_analise": {
        "riscos_evitados": [
            {"titulo": "nome do risco", "valor_risco": "R$ range", "solucao": "como AUGUR evitou"}
        ],
        "custo_analise": "R$ range",
        "risco_total_evitado": "R$ range",
        "roi_multiplicador": "ex: 30-75x",
        "citacoes": ["2-3 citações de valor percebido"],
    },
    "sintese_final": {
        "scores": {
            "viabilidade_financeira": "int 0-100",
            "demanda": "int 0-100",
            "timing": "int 0-100",
            "risco_operacional": "int 0-100",
            "competitividade": "int 0-100",
        },
        "veredicto_final": "GO | NO-GO | AJUSTAR",
        "cenario_mais_provavel": "resumo do cenário #1",
        "risco_principal": "resumo do risco #1",
        "direcionamento": ["3 ações prioritárias"],
        "sinais_consolidacao": ["sinais verdes"],
        "sinais_alerta": ["sinais amarelos"],
        "sinais_risco": ["sinais vermelhos"],
    },
}


def get_section_system_prompt(
    section_key: str,
    report_title: str,
    report_summary: str,
    simulation_requirement: str,
    tools_description: str,
    completed_sections_text: str = "",
) -> str:
    """
    Gera o system prompt para uma seção específica.
    
    O prompt mantém o loop ReAct (tool calls → data gathering) da v1,
    mas muda o formato do "Final Answer" para JSON estruturado.
    """
    
    schema = SECTION_OUTPUT_SCHEMAS.get(section_key, {})
    schema_json = json.dumps(schema, ensure_ascii=False, indent=2)
    
    # Seções que compartilham dados
    shared_note = ""
    if section_key == "cenarios_financeiros":
        shared_note = """
NOTA: Esta seção usa os MESMOS dados da seção "cenarios_futuros".
Se cenarios_futuros já foi gerada, use os mesmos dados.
O que muda é a RENDERIZAÇÃO: esta seção gera o gráfico area chart e a tabela comparativa.
Retorne o mesmo JSON de cenarios_futuros."""

    return f"""\
Você é um especialista do AUGUR escrevendo a seção "{section_key}" do relatório.

Título do relatório: {report_title}
Resumo: {report_summary}
Cenário simulado: {simulation_requirement}

══════════════════════════════════════════════════════════════
【MISSÃO】
══════════════════════════════════════════════════════════════

Use as ferramentas para observar o mundo simulado (mínimo 3 chamadas).
Depois, gere o "Final Answer:" como um JSON ESTRUTURADO no formato abaixo.

{shared_note}

══════════════════════════════════════════════════════════════
【SCHEMA JSON OBRIGATÓRIO PARA ESTA SEÇÃO】
══════════════════════════════════════════════════════════════

{schema_json}

══════════════════════════════════════════════════════════════
【REGRAS CRÍTICAS】
══════════════════════════════════════════════════════════════

1. USAR FERRAMENTAS: Mínimo 3 chamadas antes do Final Answer
2. FORMATO: Final Answer DEVE ser JSON válido no schema acima
3. DADOS REAIS: Cada número, %, citação DEVE vir da simulação
4. CITAÇÕES: Traduzir para PT-BR se necessário
5. NUNCA TRUNCAR: Títulos e textos SEMPRE completos
6. ZERO CHINÊS: Nenhum caractere chinês no output
7. PT-BR: 100% português do Brasil

══════════════════════════════════════════════════════════════
【FERRAMENTAS DISPONÍVEIS】(chamar 3-5 vezes)
══════════════════════════════════════════════════════════════

{tools_description}

- insight_forge: Análise profunda multidimensional
- panorama_search: Visão panorâmica de eventos e timeline
- quick_search: Verificação rápida de ponto específico
- interview_agents: Entrevistar agentes para citações diretas

══════════════════════════════════════════════════════════════
【FLUXO DE TRABALHO】
══════════════════════════════════════════════════════════════

Opção A — Chamar ferramenta:
<tool_call>
{{"name": "nome_ferramenta", "parameters": {{"param": "valor"}}}}
</tool_call>

Opção B — Gerar Final Answer (JSON):
Final Answer:
{{
  ... JSON no schema acima ...
}}

⚠️ PROIBIDO: ferramenta E Final Answer na mesma resposta.

══════════════════════════════════════════════════════════════
【SEÇÕES JÁ CONCLUÍDAS — EVITE REPETIÇÃO】
══════════════════════════════════════════════════════════════

{completed_sections_text if completed_sections_text else "(nenhuma seção concluída ainda)"}
"""


# ============================================================
# REACT TEMPLATES (mantém compatibilidade com o loop existente)
# ============================================================

REACT_OBSERVATION_TEMPLATE_V2 = """\
Observação (resultado da busca):

═══ Ferramenta {tool_name} retornou ═══
{result}

═══════════════════════════════════════════════════════════════
Ferramentas chamadas: {tool_calls_count}/{max_tool_calls} (usadas: {used_tools_str}){unused_hint}
- Se informação suficiente: "Final Answer:" + JSON no schema da seção
- Se precisa mais dados: chame outra ferramenta
LEMBRE: o Final Answer DEVE ser JSON válido, não texto livre.
═══════════════════════════════════════════════════════════════"""

REACT_INSUFFICIENT_TOOLS_MSG_V2 = (
    "【ATENÇÃO】Ferramentas chamadas apenas {tool_calls_count} vezes — mínimo: {min_tool_calls}. "
    "Chame mais ferramentas antes do Final Answer.{unused_hint}"
)

REACT_TOOL_LIMIT_MSG_V2 = (
    "Limite de chamadas atingido ({tool_calls_count}/{max_tool_calls}). "
    'Escreva agora o Final Answer: com o JSON estruturado da seção.'
)

REACT_FORCE_FINAL_MSG_V2 = (
    "Limite atingido. Escreva Final Answer: com JSON da seção AGORA."
)


# ============================================================
# PARSE DO FINAL ANSWER — Extrai JSON do output do LLM
# ============================================================

def parse_section_json(raw_response: str, section_key: str) -> dict:
    """
    Extrai o JSON estruturado do Final Answer do LLM.
    
    O LLM pode retornar:
    - "Final Answer: { ... }" (ideal)
    - "Final Answer:\n```json\n{ ... }\n```" (com markdown)
    - "Final Answer:\n{ ... }\n\nAlgum texto extra" (com lixo)
    
    Esta função extrai o JSON em todos os casos.
    """
    import re
    
    # Extrair tudo após "Final Answer:"
    if "Final Answer:" not in raw_response:
        # Fallback: tentar encontrar JSON direto
        json_match = re.search(r'\{[\s\S]*\}', raw_response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {"_error": "No Final Answer found", "_raw": raw_response[:500]}
    
    content = raw_response.split("Final Answer:")[-1].strip()
    
    # Remover markdown code fences
    content = re.sub(r'^```json\s*', '', content)
    content = re.sub(r'^```\s*', '', content)
    content = re.sub(r'\s*```$', '', content)
    
    # Encontrar o JSON (primeiro { até último })
    # Para arrays, primeiro [ até último ]
    json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', content)
    if not json_match:
        return {"_error": "No JSON found in Final Answer", "_raw": content[:500]}
    
    json_str = json_match.group()
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        # Tentar fixes comuns
        # 1. Trailing commas
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
        # 2. Single quotes
        # (dangerous but sometimes needed)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {"_error": f"JSON parse error: {str(e)}", "_raw": json_str[:500]}


# ============================================================
# ASSEMBLER — Monta o AugurReportSchema a partir das seções
# ============================================================

def assemble_report(sections: dict[str, dict], meta: dict) -> dict:
    """
    Monta o JSON completo do relatório a partir das seções individuais.
    
    Args:
        sections: {"resumo_executivo": {...}, "dashboard_kpis": {...}, ...}
        meta: {"projeto": "...", "nicho": "...", ...}
    
    Returns:
        JSON no formato AugurReportSchema
    """
    report = {
        "meta": meta,
        "veredicto": sections.get("resumo_executivo", {}),
        "dashboard": sections.get("dashboard_kpis", {}),
        "cenarios": sections.get("cenarios_futuros", {}),
        "riscos": sections.get("fatores_risco", {}),
        "emocional": sections.get("analise_emocional", {}),
        "agentes": sections.get("perfis_agentes", []),
        "forcas": sections.get("mapa_forcas", {}),
        "cronologia": sections.get("cronologia", {}),
        "padroes": sections.get("padroes_emergentes", []),
        "recomendacoes": sections.get("recomendacoes", []),
        "checklist": sections.get("checklist_go", []),
        "previsoes": sections.get("previsoes_confianca", []),
        "posicionamento": sections.get("posicionamento", {}),
        "roi": sections.get("roi_analise", {}),
        "sintese": sections.get("sintese_final", {}),
    }
    return report


# ============================================================
# SECTION KEYS — Ordem de geração
# ============================================================

SECTION_KEYS_ORDERED = [
    "resumo_executivo",
    "dashboard_kpis",
    "cenarios_futuros",
    "cenarios_financeiros",  # usa dados de cenarios_futuros
    "fatores_risco",
    "analise_emocional",
    "perfis_agentes",
    "mapa_forcas",
    "cronologia",
    "padroes_emergentes",
    "recomendacoes",
    "checklist_go",
    "previsoes_confianca",
    "posicionamento",
    "roi_analise",
    "sintese_final",
]

# Seções que NÃO precisam de ReAct loop (usam dados de outras seções)
SECTIONS_NO_REACT = {"cenarios_financeiros"}
# cenarios_financeiros reutiliza os dados de cenarios_futuros


# ============================================================
# MIGRATION GUIDE — Como integrar no report_agent.py existente
# ============================================================
#
# 1. No __init__.py ou no topo do report_agent.py:
#    from app.schemas.report_schema import AugurReportSchema, validar_report_json
#    from app.services.report_prompts_v2 import (
#        PLAN_SYSTEM_PROMPT_V2, PLAN_USER_PROMPT_V2,
#        get_section_system_prompt, parse_section_json,
#        assemble_report, SECTION_KEYS_ORDERED, SECTIONS_NO_REACT,
#        REACT_OBSERVATION_TEMPLATE_V2, REACT_TOOL_LIMIT_MSG_V2,
#        REACT_INSUFFICIENT_TOOLS_MSG_V2, REACT_FORCE_FINAL_MSG_V2,
#    )
#
# 2. Em _generate_plan():
#    ANTES: system_prompt = f"{PLAN_SYSTEM_PROMPT}\n\n{get_language_instruction()}"
#    DEPOIS: system_prompt = f"{PLAN_SYSTEM_PROMPT_V2}\n\n{get_language_instruction()}"
#
# 3. Em _generate_section_react():
#    ANTES: system_prompt = SECTION_SYSTEM_PROMPT_TEMPLATE.format(...)
#    DEPOIS: system_prompt = get_section_system_prompt(section_key, ...)
#
# 4. Após "Final Answer:":
#    ANTES: final_answer = response.split("Final Answer:")[-1].strip()
#           section["content"] = final_answer  # texto livre
#    DEPOIS: section_json = parse_section_json(response, section_key)
#            section["data"] = section_json  # JSON estruturado
#            section["content"] = section_json  # compatibilidade
#
# 5. Em generate_report(), após todas as seções:
#    ANTES: return {"title": title, "sections": sections}
#    DEPOIS:
#        section_data = {s["key"]: s["data"] for s in sections}
#        report_json = assemble_report(section_data, meta)
#        errors = validar_report_json(report_json)
#        if errors:
#            logger.warning(f"Report validation errors: {errors}")
#        return {"title": title, "sections": sections, "structured": report_json}
#
# 6. No pdf_generator.py:
#    ANTES: parse texto com regex para extrair dados
#    DEPOIS: data = report["structured"]
#            cenarios = data["cenarios"]["cenarios"]
#            riscos = data["riscos"]["riscos"]
#            ... renderizar diretamente
#
# ============================================================
