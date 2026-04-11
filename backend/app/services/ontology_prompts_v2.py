"""
AUGUR Ontology Prompts v2 — Grafos de conhecimento por nicho.

Substitui o ONTOLOGY_SYSTEM_PROMPT do ontology_generator.py para gerar
entidades com PAPÉIS FUNCIONAIS (Incumbente, Entrante, Canal_Digital)
em vez de tipos genéricos (Person, Organization).

Cada nicho de negócio tem um template que define:
- Quais entidades são ESPERADAS naquele mercado
- Quais relações existem entre elas
- Quais benchmarks calibram a simulação

Caminho no repo: backend/app/services/ontology_prompts_v2.py

Uso:
    from app.services.ontology_prompts_v2 import (
        detect_niche,
        get_ontology_system_prompt,
        get_ontology_user_prompt,
        NICHE_TEMPLATES,
    )
"""

import json
from typing import Optional


# ============================================================
# TEMPLATES DE GRAFO POR NICHO
# ============================================================
# Cada template define as entidades, relações e benchmarks
# que são ESPERADOS para aquele tipo de negócio.
# O LLM usa isso como guia — pode adicionar entidades extras
# se o contexto exigir, mas DEVE incluir as esperadas.
# ============================================================

NICHE_TEMPLATES = {
    "varejo_local": {
        "descricao": "Loja física em cidade pequena/média (calçados, roupas, eletrônicos, móveis, etc.)",
        "keywords": ["loja", "calcado", "roupa", "varejo", "comercio", "sapato", "tenis", "vestido",
                     "moda", "boutique", "loja fisica", "ponto comercial", "shopping", "centro",
                     "eletronico", "movel", "decoracao", "brinquedo", "papelaria", "perfumaria",
                     "relojoaria", "otica", "joalheria", "bijuteria", "bolsa", "acessorio"],
        "entidades": [
            {"papel": "Incumbente", "tipo_sugerido": "LojaEstabelecida",
             "descricao": "Loja(s) dominante(s) do mercado local — a referência que todo entrante precisa enfrentar",
             "atributos": ["base_clientes", "num_lojas", "crediario_ativo", "tempo_mercado", "faturamento_estimado", "localizacao"]},
            {"papel": "Entrante", "tipo_sugerido": "NovaLoja",
             "descricao": "A nova loja proposta pelo cliente — o objeto da simulação",
             "atributos": ["investimento_inicial", "nicho_proposto", "canal_primario", "diferencial"]},
            {"papel": "CanalDigital", "tipo_sugerido": "MarketplaceDigital",
             "descricao": "Shopee, Shein, Mercado Livre, Amazon — âncora mental de preço",
             "atributos": ["base_usuarios_local", "preco_referencia", "frete_gratis_acima", "categorias_fortes"]},
            {"papel": "CanalInformal", "tipo_sugerido": "ComercianteInformal",
             "descricao": "Sacoleiras, vendedores de WhatsApp, Instagram sellers — competem por preço e conveniência",
             "atributos": ["faturamento_mensal", "desconto_vs_varejo", "frequencia_reposicao", "canais_venda"]},
            {"papel": "ConsumidorFiel", "tipo_sugerido": "ClienteCrediario",
             "descricao": "Cliente com crediário ativo no incumbente — alta barreira de troca",
             "atributos": ["faixa_etaria", "crediario_valor", "frequencia_compra", "ticket_medio", "tempo_cliente"]},
            {"papel": "ConsumidorLivre", "tipo_sugerido": "ClientePotencial",
             "descricao": "Cliente sem vínculo de crediário — alvo primário do entrante",
             "atributos": ["faixa_etaria", "canais_compra_atuais", "sensibilidade_preco", "necessidades_nao_atendidas"]},
            {"papel": "ConsumidorDigital", "tipo_sugerido": "CompradorOnline",
             "descricao": "Cliente que compra majoritariamente online — referência de preço",
             "atributos": ["apps_usados", "categorias_online", "ticket_medio_online", "resistencia_loja_fisica"]},
            {"papel": "InfluenciadorLocal", "tipo_sugerido": "FormadorOpiniao",
             "descricao": "Pessoa com circulação social alta na cidade — vetor de indicação",
             "atributos": ["alcance_local", "plataformas", "credibilidade", "relacao_com_comercio"]},
            # Fallbacks obrigatórios
            {"papel": "Fallback_Pessoa", "tipo_sugerido": "Person",
             "descricao": "Qualquer pessoa física sem tipo específico",
             "atributos": ["full_name", "role", "location"]},
            {"papel": "Fallback_Org", "tipo_sugerido": "Organization",
             "descricao": "Qualquer organização sem tipo específico",
             "atributos": ["org_name", "type", "location"]},
        ],
        "relacoes": [
            {"tipo": "COMPETE_COM", "source": "Incumbente", "target": "Entrante", "descricao": "Competição direta no mercado local"},
            {"tipo": "ANCORA_PRECO", "source": "CanalDigital", "target": "Incumbente", "descricao": "Marketplace define referência mental de preço"},
            {"tipo": "COMPRIME_MARGEM", "source": "CanalInformal", "target": "Entrante", "descricao": "Vendedor informal compete por preço abaixo do varejo"},
            {"tipo": "FIDELIZADO_POR", "source": "ConsumidorFiel", "target": "Incumbente", "descricao": "Cliente preso por crediário/confiança/hábito"},
            {"tipo": "DISPONIVEL_PARA", "source": "ConsumidorLivre", "target": "Entrante", "descricao": "Cliente sem vínculo, disponível para captação"},
            {"tipo": "COMPRA_DE", "source": "ConsumidorDigital", "target": "CanalDigital", "descricao": "Compra habitual via marketplace"},
            {"tipo": "INFLUENCIA", "source": "InfluenciadorLocal", "target": "ConsumidorLivre", "descricao": "Influência via indicação/boca a boca"},
            {"tipo": "MIGRA_PARA", "source": "ConsumidorFiel", "target": "Entrante", "descricao": "Troca de loja (quando ocorre)"},
        ],
        "benchmarks": {
            "ticket_medio_setor": "R$120-280",
            "margem_bruta_tipica": "45-60%",
            "taxa_recompra_saudavel": "15-25%",
            "custo_crediario_inadimplencia": "3-8%",
            "sazonalidades": ["Dia das Mães (mai)", "Dia dos Namorados (jun)", "Dia dos Pais (ago)", "Black Friday (nov)", "Natal (dez)"],
            "base_clientes_tipica_incumbente": "2.000-5.000 cadastros ativos",
            "tempo_breakeven_entrante": "12-24 meses",
        }
    },

    "saas_b2b": {
        "descricao": "Software as a Service para empresas",
        "keywords": ["saas", "software", "plataforma", "app", "sistema", "erp", "crm",
                     "b2b", "api", "cloud", "assinatura", "recorrente", "startup",
                     "tecnologia", "automacao", "inteligencia artificial", "dashboard"],
        "entidades": [
            {"papel": "Incumbente", "tipo_sugerido": "SaaSEstabelecido",
             "descricao": "Competidor(es) estabelecido(s) no mercado — referência de pricing e features",
             "atributos": ["arr", "num_clientes", "churn_mensal", "pricing_modelo", "features_chave"]},
            {"papel": "Entrante", "tipo_sugerido": "NovoSaaS",
             "descricao": "O produto/plataforma proposto pelo cliente",
             "atributos": ["investimento", "diferencial", "pricing_proposto", "stack_tech", "mvp_status"]},
            {"papel": "ICP_Decisor", "tipo_sugerido": "DecislorCompra",
             "descricao": "Quem decide a compra na empresa-cliente (CEO, CTO, gerente)",
             "atributos": ["cargo", "empresa_tipo", "dor_principal", "budget_anual", "processo_compra"]},
            {"papel": "ICP_Usuario", "tipo_sugerido": "UsuarioFinal",
             "descricao": "Quem usa o software no dia a dia",
             "atributos": ["cargo", "frustracao_atual", "tempo_adocao", "resistencia_mudanca"]},
            {"papel": "CanalAquisicao", "tipo_sugerido": "CanalMarketing",
             "descricao": "Canais de aquisição: LinkedIn, Google Ads, content, indicação, PLG",
             "atributos": ["tipo", "cac_estimado", "conversion_rate", "tempo_ciclo_venda"]},
            {"papel": "Integrador", "tipo_sugerido": "ParceiroTecnologico",
             "descricao": "Empresas que integram/revendem/indicam — canal indireto",
             "atributos": ["tipo_parceria", "base_clientes", "comissao"]},
            {"papel": "Regulador", "tipo_sugerido": "ReguladorDigital",
             "descricao": "LGPD, compliance, certificações necessárias",
             "atributos": ["requisito", "prazo", "penalidade"]},
            {"papel": "Investidor", "tipo_sugerido": "InvestidorVC",
             "descricao": "VCs, angels, aceleradoras — validação de mercado",
             "atributos": ["tese", "ticket", "stage"]},
            {"papel": "Fallback_Pessoa", "tipo_sugerido": "Person",
             "descricao": "Qualquer pessoa física", "atributos": ["full_name", "role"]},
            {"papel": "Fallback_Org", "tipo_sugerido": "Organization",
             "descricao": "Qualquer organização", "atributos": ["org_name", "type"]},
        ],
        "relacoes": [
            {"tipo": "COMPETE_COM", "source": "Incumbente", "target": "Entrante", "descricao": "Competição direta por features/preço"},
            {"tipo": "DECIDE_COMPRA", "source": "ICP_Decisor", "target": "Entrante", "descricao": "Processo de decisão de compra"},
            {"tipo": "USA_PRODUTO", "source": "ICP_Usuario", "target": "Incumbente", "descricao": "Uso diário do software"},
            {"tipo": "ADQUIRE_VIA", "source": "ICP_Decisor", "target": "CanalAquisicao", "descricao": "Canal por onde descobre o produto"},
            {"tipo": "INTEGRA_COM", "source": "Integrador", "target": "Entrante", "descricao": "Parceria técnica/comercial"},
            {"tipo": "REGULA", "source": "Regulador", "target": "Entrante", "descricao": "Compliance/regulação"},
            {"tipo": "INVESTE_EM", "source": "Investidor", "target": "Entrante", "descricao": "Investimento/validação"},
            {"tipo": "MIGRA_PARA", "source": "ICP_Usuario", "target": "Entrante", "descricao": "Troca de fornecedor"},
        ],
        "benchmarks": {
            "cac_medio": "R$500-5000",
            "ltv_cac_ratio_saudavel": "3:1 mínimo",
            "churn_mensal_aceitavel": "2-5%",
            "margem_bruta_saas": "70-85%",
            "tempo_payback_cac": "6-18 meses",
            "nps_bom": ">50",
            "ciclo_venda_b2b": "30-90 dias",
        }
    },

    "alimentacao": {
        "descricao": "Restaurante, lanchonete, padaria, food truck, delivery, confeitaria",
        "keywords": ["restaurante", "lanchonete", "padaria", "food", "delivery", "comida",
                     "cafe", "bar", "pizza", "hamburguer", "acai", "sorvete", "confeitaria",
                     "marmita", "refeicao", "ifood", "rappi", "uber eats", "food truck"],
        "entidades": [
            {"papel": "Incumbente", "tipo_sugerido": "RestauranteEstabelecido",
             "descricao": "Restaurante(s) dominante(s) na região",
             "atributos": ["base_clientes", "ticket_medio", "avaliacao_google", "tempo_mercado", "delivery_ativo"]},
            {"papel": "Entrante", "tipo_sugerido": "NovoRestaurante",
             "descricao": "O negócio de alimentação proposto",
             "atributos": ["investimento_inicial", "cardapio_proposto", "diferencial", "modelo_operacao"]},
            {"papel": "PlataformaDelivery", "tipo_sugerido": "AppDelivery",
             "descricao": "iFood, Rappi, Uber Eats — canal obrigatório mas com taxa alta",
             "atributos": ["taxa_comissao", "base_usuarios_local", "ranking_algoritmo"]},
            {"papel": "ClienteRecorrente", "tipo_sugerido": "ClienteFiel",
             "descricao": "Cliente que frequenta 2+ vezes por semana",
             "atributos": ["frequencia_semanal", "ticket_medio", "preferencia_canal", "sensibilidade_preco"]},
            {"papel": "ClienteOcasional", "tipo_sugerido": "ClienteNovo",
             "descricao": "Cliente que experimenta por curiosidade ou indicação",
             "atributos": ["gatilho_visita", "expectativa", "canais_descoberta"]},
            {"papel": "Fornecedor", "tipo_sugerido": "FornecedorInsumos",
             "descricao": "Fornecedores de insumos — impacto direto na margem",
             "atributos": ["tipo_insumo", "prazo_entrega", "condicao_pagamento"]},
            {"papel": "Regulador", "tipo_sugerido": "VigilanciaSanitaria",
             "descricao": "ANVISA, Vigilância Sanitária, Bombeiros — licenças obrigatórias",
             "atributos": ["licenca_necessaria", "prazo", "custo"]},
            {"papel": "InfluenciadorFood", "tipo_sugerido": "FoodBlogger",
             "descricao": "Influenciadores de gastronomia locais",
             "atributos": ["plataforma", "alcance", "credibilidade"]},
            {"papel": "Fallback_Pessoa", "tipo_sugerido": "Person",
             "descricao": "Qualquer pessoa", "atributos": ["full_name", "role"]},
            {"papel": "Fallback_Org", "tipo_sugerido": "Organization",
             "descricao": "Qualquer organização", "atributos": ["org_name", "type"]},
        ],
        "relacoes": [
            {"tipo": "COMPETE_COM", "source": "Incumbente", "target": "Entrante", "descricao": "Competição direta"},
            {"tipo": "COBRA_COMISSAO", "source": "PlataformaDelivery", "target": "Entrante", "descricao": "Taxa de 12-30% por pedido"},
            {"tipo": "FREQUENTA", "source": "ClienteRecorrente", "target": "Incumbente", "descricao": "Hábito de consumo"},
            {"tipo": "FORNECE_PARA", "source": "Fornecedor", "target": "Entrante", "descricao": "Cadeia de suprimentos"},
            {"tipo": "FISCALIZA", "source": "Regulador", "target": "Entrante", "descricao": "Compliance sanitário"},
            {"tipo": "DIVULGA", "source": "InfluenciadorFood", "target": "Entrante", "descricao": "Marketing via influência"},
        ],
        "benchmarks": {
            "ticket_medio_almoco": "R$25-45",
            "ticket_medio_jantar": "R$40-80",
            "margem_bruta_restaurante": "55-70%",
            "custo_comida_ideal": "28-35% do faturamento",
            "taxa_ifood": "12-27%",
            "avaliacao_minima_viavel": "4.2 estrelas",
        }
    },

    "servicos": {
        "descricao": "Prestação de serviços: consultoria, agência, clínica, escritório, academia, salão",
        "keywords": ["consultoria", "agencia", "clinica", "escritorio", "academia", "salao",
                     "personal", "coach", "advocacia", "contabilidade", "marketing digital",
                     "design", "fotografia", "arquitetura", "engenharia", "freelancer",
                     "curso", "treinamento", "mentoria", "terapia", "psicologia"],
        "entidades": [
            {"papel": "Incumbente", "tipo_sugerido": "PrestadorEstabelecido",
             "descricao": "Concorrente(s) estabelecido(s) na região/segmento",
             "atributos": ["base_clientes", "reputacao", "tempo_mercado", "pricing", "especializacao"]},
            {"papel": "Entrante", "tipo_sugerido": "NovoPrestador",
             "descricao": "O negócio de serviços proposto",
             "atributos": ["investimento", "diferencial", "pricing_proposto", "qualificacao"]},
            {"papel": "ClienteIdeal", "tipo_sugerido": "ClienteAlvo",
             "descricao": "Perfil do cliente ideal que mais gera valor",
             "atributos": ["dor_principal", "budget", "frequencia_uso", "canal_descoberta"]},
            {"papel": "Indicador", "tipo_sugerido": "FonteIndicacao",
             "descricao": "Quem indica clientes — o canal mais poderoso em serviços",
             "atributos": ["tipo", "volume_indicacoes", "taxa_conversao"]},
            {"papel": "PlataformaAquisicao", "tipo_sugerido": "CanalDigital",
             "descricao": "Google, Instagram, LinkedIn — canal de descoberta",
             "atributos": ["cac", "conversion_rate", "tipo_conteudo"]},
            {"papel": "Regulador", "tipo_sugerido": "ConselhoClasse",
             "descricao": "CRM, OAB, CRC, CREA — regulação profissional",
             "atributos": ["requisito", "anuidade", "fiscalizacao"]},
            {"papel": "Fallback_Pessoa", "tipo_sugerido": "Person",
             "descricao": "Qualquer pessoa", "atributos": ["full_name", "role"]},
            {"papel": "Fallback_Org", "tipo_sugerido": "Organization",
             "descricao": "Qualquer organização", "atributos": ["org_name", "type"]},
        ],
        "relacoes": [
            {"tipo": "COMPETE_COM", "source": "Incumbente", "target": "Entrante", "descricao": "Competição"},
            {"tipo": "CONTRATA", "source": "ClienteIdeal", "target": "Entrante", "descricao": "Contratação do serviço"},
            {"tipo": "INDICA_PARA", "source": "Indicador", "target": "ClienteIdeal", "descricao": "Indicação/referral"},
            {"tipo": "DESCOBRE_VIA", "source": "ClienteIdeal", "target": "PlataformaAquisicao", "descricao": "Descoberta digital"},
            {"tipo": "REGULA", "source": "Regulador", "target": "Entrante", "descricao": "Regulação profissional"},
        ],
        "benchmarks": {
            "taxa_indicacao_saudavel": "30-50% dos clientes",
            "churn_mensal_servicos": "3-8%",
            "margem_bruta_servicos": "60-80%",
            "nps_bom": ">60",
            "tempo_fidelizacao": "3-6 meses",
        }
    },
}


# ============================================================
# DETECÇÃO DE NICHO
# ============================================================

def detect_niche(simulation_requirement: str) -> str:
    """
    Detecta o nicho do negócio a partir do texto da simulação.
    Retorna a key do NICHE_TEMPLATES mais provável.
    Fallback: "varejo_local" (mais genérico).
    """
    text = simulation_requirement.lower()
    
    scores = {}
    for niche_key, template in NICHE_TEMPLATES.items():
        score = sum(1 for kw in template["keywords"] if kw in text)
        scores[niche_key] = score
    
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "varejo_local"  # fallback
    return best


# ============================================================
# PROMPTS DE ONTOLOGIA POR NICHO
# ============================================================

def get_ontology_system_prompt(niche_key: str) -> str:
    """
    Gera o system prompt de ontologia customizado para o nicho.
    Inclui as entidades esperadas, relações e benchmarks.
    """
    template = NICHE_TEMPLATES.get(niche_key, NICHE_TEMPLATES["varejo_local"])
    
    # Formatar entidades esperadas
    entities_text = ""
    for i, ent in enumerate(template["entidades"], 1):
        attrs = ", ".join(ent["atributos"])
        entities_text += f"""
{i}. **{ent['papel']}** (tipo sugerido: `{ent['tipo_sugerido']}`)
   Descrição: {ent['descricao']}
   Atributos esperados: {attrs}
"""

    # Formatar relações
    relations_text = ""
    for rel in template["relacoes"]:
        relations_text += f"- `{rel['tipo']}`: {rel['source']} → {rel['target']} ({rel['descricao']})\n"
    
    # Formatar benchmarks
    benchmarks_text = ""
    for key, val in template["benchmarks"].items():
        label = key.replace("_", " ").title()
        if isinstance(val, list):
            val = ", ".join(val)
        benchmarks_text += f"- {label}: {val}\n"

    return f"""\
Você é um especialista em design de ontologias para grafos de conhecimento.
Sua tarefa: projetar entidades e relacionamentos para simulação de opinião pública.

**Nicho do negócio: {template['descricao']}**

══════════════════════════════════════════════════════════════
【ENTIDADES ESPERADAS PARA ESTE NICHO】
══════════════════════════════════════════════════════════════

As seguintes entidades são ESPERADAS para este tipo de negócio.
Você DEVE incluir todas elas, adaptando nomes e atributos ao contexto específico.
Pode adicionar 1-2 entidades extras se o contexto exigir.

{entities_text}

══════════════════════════════════════════════════════════════
【RELAÇÕES ESPERADAS】
══════════════════════════════════════════════════════════════

{relations_text}

Pode adicionar relações extras se necessário.

══════════════════════════════════════════════════════════════
【BENCHMARKS DO SETOR】
══════════════════════════════════════════════════════════════

Use estes benchmarks para CALIBRAR os atributos das entidades.
Quando a simulação gerar números, devem ser realistas para o setor.

{benchmarks_text}

══════════════════════════════════════════════════════════════
【FORMATO DE SAÍDA — JSON OBRIGATÓRIO】
══════════════════════════════════════════════════════════════

Retorne JSON com a seguinte estrutura:

{{
    "nicho_detectado": "{niche_key}",
    "entity_types": [
        {{
            "name": "NomeTipoEntidade (PascalCase em inglês)",
            "papel": "Incumbente | Entrante | CanalDigital | ... (papel funcional)",
            "description": "Descrição em PORTUGUÊS DO BRASIL (max 100 chars)",
            "attributes": [
                {{
                    "name": "nome_atributo (snake_case inglês)",
                    "type": "text",
                    "description": "Descrição em PT-BR"
                }}
            ],
            "examples": ["Exemplo real em PT-BR"],
            "benchmarks": {{"atributo": "valor de referência"}}
        }}
    ],
    "edge_types": [
        {{
            "name": "NOME_RELACAO (UPPER_SNAKE_CASE)",
            "description": "Descrição em PT-BR (max 100 chars)",
            "source_targets": [
                {{"source": "TipoOrigem", "target": "TipoDestino"}}
            ],
            "attributes": []
        }}
    ],
    "analysis_summary": "Resumo da análise em PT-BR",
    "benchmarks_aplicados": {{}}
}}

══════════════════════════════════════════════════════════════
【REGRAS ABSOLUTAS】
══════════════════════════════════════════════════════════════

1. EXATAMENTE 10 entity_types (8 específicos + 2 fallback: Person e Organization)
2. Cada entidade DEVE ter um "papel" funcional (Incumbente, Entrante, etc.)
3. Nomes de tipos: INGLÊS PascalCase
4. Nomes de relações: INGLÊS UPPER_SNAKE_CASE
5. Nomes de atributos: INGLÊS snake_case
6. Descrições, examples, analysis_summary: PORTUGUÊS DO BRASIL
7. ZERO caracteres chineses em qualquer campo
8. Atributos proibidos: name, uuid, group_id, created_at, summary (reservados)
9. Entidades devem ser AGENTES reais que podem agir em redes sociais
10. NÃO criar conceitos abstratos como entidades
"""


def get_ontology_user_prompt(
    simulation_requirement: str,
    document_texts: str,
    niche_key: str,
    additional_context: str = "",
) -> str:
    """Gera o user prompt com contexto do negócio e template do nicho."""
    
    template = NICHE_TEMPLATES.get(niche_key, NICHE_TEMPLATES["varejo_local"])
    benchmarks_json = json.dumps(template["benchmarks"], ensure_ascii=False, indent=2)
    
    prompt = f"""## Requisito da Simulação

{simulation_requirement}

## Nicho Detectado: {niche_key}
{template['descricao']}

## Benchmarks de Referência para este Setor
{benchmarks_json}

## Conteúdo Documental

{document_texts}
"""
    
    if additional_context:
        prompt += f"""
## Contexto Adicional
{additional_context}
"""
    
    prompt += """
Com base no conteúdo acima, projete os tipos de entidades e relacionamentos.

**Regras obrigatórias**:
1. EXATAMENTE 10 tipos de entidades
2. Os 2 últimos DEVEM ser fallback: Person e Organization
3. Os 8 primeiros são tipos específicos com PAPÉIS FUNCIONAIS
4. Cada tipo DEVE ter o campo "papel" (Incumbente, Entrante, etc.)
5. Use os benchmarks do setor para calibrar os atributos
6. Tudo em PORTUGUÊS DO BRASIL (exceto nomes técnicos em inglês)
"""
    
    return prompt


# ============================================================
# GUIA DE INTEGRAÇÃO no ontology_generator.py
# ============================================================
#
# ANTES (ontology_generator.py, método generate):
#
#   system_prompt = f"{ONTOLOGY_SYSTEM_PROMPT}\n\n{lang_instruction}"
#   user_message = self._build_user_message(document_texts, simulation_requirement)
#
# DEPOIS:
#
#   from app.services.ontology_prompts_v2 import (
#       detect_niche, get_ontology_system_prompt, get_ontology_user_prompt
#   )
#
#   niche = detect_niche(simulation_requirement)
#   logger.info(f"Nicho detectado: {niche}")
#
#   system_prompt = get_ontology_system_prompt(niche)
#   system_prompt += f"\n\n{get_language_instruction()}"
#
#   user_message = get_ontology_user_prompt(
#       simulation_requirement=simulation_requirement,
#       document_texts="\n\n---\n\n".join(document_texts),
#       niche_key=niche,
#       additional_context=additional_context or "",
#   )
#
# O resultado terá:
# - Entidades com "papel" funcional (Incumbente, Entrante, etc.)
# - Benchmarks aplicados
# - Relações específicas do nicho
# - Tudo em PT-BR
#
# O campo "nicho_detectado" no output permite que as camadas
# posteriores (simulação, relatório) saibam qual template usar.
#
# ============================================================
"""


if __name__ == "__main__":
    # Testes
    print("=== DETECÇÃO DE NICHO ===")
    tests = [
        ("abertura de loja de calçados de nicho em Santo Antonio de Padua", "varejo_local"),
        ("lançamento de plataforma SaaS de CRM para PMEs", "saas_b2b"),
        ("abertura de restaurante japonês em Copacabana", "alimentacao"),
        ("escritório de advocacia especializado em startups", "servicos"),
        ("venda de roupas femininas em cidade pequena", "varejo_local"),
        ("app de delivery de marmitas fitness", "alimentacao"),
    ]
    for req, expected in tests:
        detected = detect_niche(req)
        status = "✓" if detected == expected else f"✗ (esperado: {expected})"
        print(f"  {status} '{req[:50]}...' → {detected}")
    
    print(f"\n=== TEMPLATES DISPONÍVEIS: {len(NICHE_TEMPLATES)} ===")
    for k, v in NICHE_TEMPLATES.items():
        print(f"  {k}: {v['descricao'][:60]}... ({len(v['entidades'])} entidades, {len(v['relacoes'])} relações)")
    
    print("\n=== PROMPT GERADO ===")
    prompt = get_ontology_system_prompt("varejo_local")
    print(f"  Tamanho: {len(prompt)} chars")
    print(f"  Contém 'Incumbente': {'Incumbente' in prompt}")
    print(f"  Contém chinês: {any(ord(c) > 0x4e00 and ord(c) < 0x9fff for c in prompt)}")
"""
