"""
AUGUR Ontology Prompts v3 — Sistema bidimensional: SETOR × TIPO DE DECISÃO.

Evolução da v2: em vez de só detectar o nicho da indústria,
agora detecta DUAS dimensões:
  1. SETOR: qual indústria/mercado
  2. TIPO DE DECISÃO: o que o cliente quer fazer

Cada combinação gera entidades e relações diferentes.

Caminho no repo: backend/app/services/ontology_prompts_v3.py
"""

import json
from typing import Tuple

# ============================================================
# EIXO 1 — SETORES
# ============================================================

SETORES = {
    "varejo_local": {
        "nome": "Varejo local / comércio físico",
        "keywords": ["loja", "calcado", "roupa", "varejo", "comercio", "sapato", "tenis",
                     "moda", "boutique", "ponto comercial", "shopping", "centro",
                     "eletronico", "movel", "decoracao", "brinquedo", "papelaria",
                     "otica", "joalheria", "bolsa", "acessorio", "perfumaria",
                     "moveis", "colchao", "eletrodomestico", "cama", "mesa"],
    },
    "saas_b2b": {
        "nome": "SaaS / software / plataforma digital",
        "keywords": ["saas", "software", "plataforma", "sistema", "erp", "crm",
                     "b2b", "api", "cloud", "assinatura", "startup", "automacao",
                     "inteligencia artificial", "dashboard", "converzas", "chatbot"],
    },
    "industria_fmcg": {
        "nome": "Indústria / bens de consumo / FMCG",
        "keywords": ["fabrica", "industria", "papel", "higienico", "fabricante",
                     "producao", "manufatura", "cpg", "fmcg", "embalagem",
                     "distribuidora", "atacado", "companhia", "cia", "copapa",
                     "alimento industrializado", "bebida", "cerveja", "refrigerante"],
    },
    "telecom_isp": {
        "nome": "Telecomunicações / internet / ISP",
        "keywords": ["internet", "provedor", "fibra", "banda larga", "isp",
                     "telecom", "telecomunicacao", "wifi", "rede", "conectividade",
                     "milla", "dados moveis", "5g", "antena", "torre"],
    },
    "energia_tech": {
        "nome": "Energia / solar / EV / tecnologia limpa",
        "keywords": ["solar", "energia", "fotovoltaico", "carregador", "eletrico",
                     "ev", "veiculo eletrico", "bateria", "sustentavel", "evo",
                     "eletroposto", "estacao de carga", "painel solar"],
    },
    "alimentacao": {
        "nome": "Alimentação / restaurante / delivery / food",
        "keywords": ["restaurante", "lanchonete", "padaria", "food", "delivery",
                     "comida", "cafe", "bar", "pizza", "hamburguer", "acai",
                     "confeitaria", "marmita", "ifood", "rappi", "food truck",
                     "menu certo", "refeicao", "cardapio"],
    },
    "marketplace_app": {
        "nome": "App / marketplace / plataforma de intermediação",
        "keywords": ["app", "aplicativo", "marketplace", "plataforma", "uber",
                     "99", "delivery", "intermediacao", "dois lados", "comissao",
                     "usuario", "motorista", "entregador", "assinante"],
    },
    "servicos": {
        "nome": "Serviços profissionais / consultoria / saúde",
        "keywords": ["consultoria", "agencia", "clinica", "escritorio", "academia",
                     "salao", "personal", "advocacia", "contabilidade", "marketing",
                     "design", "arquitetura", "curso", "mentoria", "terapia"],
    },
    "franquia": {
        "nome": "Franquia / rede / expansão de marca",
        "keywords": ["franquia", "franqueado", "franqueador", "rede", "unidade",
                     "padronizacao", "royalties", "taxa de franquia", "manual"],
    },
}


# ============================================================
# EIXO 2 — TIPOS DE DECISÃO
# ============================================================

TIPOS_DECISAO = {
    "novo_negocio": {
        "nome": "Abrir novo negócio / empresa / loja",
        "keywords": ["abrir", "abertura", "novo", "nova", "comecar", "iniciar",
                     "empreender", "montar", "criar", "inaugurar", "fundar"],
        "entidades_extras": [
            {"papel": "Entrante", "descricao": "O novo negócio proposto"},
            {"papel": "Incumbente", "descricao": "Concorrente(s) já estabelecido(s)"},
            {"papel": "ConsumidorAlvo", "descricao": "Público-alvo primário"},
        ],
        "perguntas_chave": [
            "Qual o investimento total necessário?",
            "Quando atinge o break-even?",
            "Quem são os concorrentes e qual sua vantagem?",
            "Qual o tamanho do mercado local?",
        ],
    },
    "novo_produto": {
        "nome": "Lançar novo produto / linha / SKU",
        "keywords": ["lancar", "lancamento", "novo produto", "nova linha",
                     "sku", "produto", "inovacao", "extensao de linha",
                     "versao", "modelo", "variante"],
        "entidades_extras": [
            {"papel": "ProdutoNovo", "descricao": "O produto/linha sendo lançado"},
            {"papel": "ProdutoExistente", "descricao": "Produtos atuais da empresa"},
            {"papel": "ConcorrenteDireto", "descricao": "Quem já vende produto similar"},
            {"papel": "CanalDistribuicao", "descricao": "Como o produto chega ao consumidor"},
        ],
        "perguntas_chave": [
            "O mercado precisa desse produto?",
            "Canibaliza produtos existentes?",
            "Qual o preço ideal vs concorrência?",
            "Quais canais de distribuição usar?",
        ],
    },
    "promocao_campanha": {
        "nome": "Promoção / campanha / ação de marketing",
        "keywords": ["promocao", "campanha", "desconto", "sorteio", "dar",
                     "ganhar", "premiar", "copa", "black friday", "natal",
                     "dia das maes", "acao", "marketing", "engajamento",
                     "fidelizacao", "cashback", "cupom", "brinde", "tv"],
        "entidades_extras": [
            {"papel": "BaseAtual", "descricao": "Clientes/usuários atuais da empresa"},
            {"papel": "PublicoNovo", "descricao": "Público que a promoção quer atrair"},
            {"papel": "ConcorrenteReacao", "descricao": "Como concorrentes vão reagir"},
            {"papel": "CustoPromocao", "descricao": "Investimento total na ação"},
            {"papel": "MidiaCanal", "descricao": "Canais de divulgação da promoção"},
        ],
        "perguntas_chave": [
            "Qual o ROI esperado da promoção?",
            "Quantos clientes novos atrai vs custo?",
            "O concorrente vai contra-atacar?",
            "A mecânica é clara e atrativa?",
            "Gera retenção ou só pico temporário?",
        ],
    },
    "expansao_geografica": {
        "nome": "Expandir para nova cidade / região / filial",
        "keywords": ["filial", "expandir", "expansao", "nova cidade", "abrir em",
                     "regional", "nova unidade", "ponto", "sucursal", "regiao"],
        "entidades_extras": [
            {"papel": "MatrizOrigem", "descricao": "A empresa/loja original que já opera"},
            {"papel": "MercadoDestino", "descricao": "A nova cidade/região alvo"},
            {"papel": "ConcorrenteLocal", "descricao": "Quem já opera no destino"},
            {"papel": "ConsumidorLocal", "descricao": "Perfil do público na nova região"},
        ],
        "perguntas_chave": [
            "O modelo que funciona na origem replica no destino?",
            "Qual o tamanho do mercado local?",
            "Quem já domina essa praça?",
            "Qual o custo de operação remota?",
        ],
    },
    "expansao_franquia": {
        "nome": "Abrir franquia / unidade franqueada",
        "keywords": ["franquia", "franqueado", "franquear", "rede", "unidade",
                     "modelo de franquia", "royalties"],
        "entidades_extras": [
            {"papel": "Franqueador", "descricao": "A marca que vende a franquia"},
            {"papel": "Franqueado", "descricao": "Quem compra e opera a unidade"},
            {"papel": "MercadoLocal", "descricao": "A cidade/bairro onde vai operar"},
            {"papel": "ConcorrenteLocal", "descricao": "Quem já compete nessa praça"},
        ],
        "perguntas_chave": [
            "A marca tem força suficiente na região?",
            "O modelo financeiro da franquia fecha?",
            "Qual o suporte do franqueador?",
            "A praça comporta mais uma unidade?",
        ],
    },
    "precificacao": {
        "nome": "Mudança de preço / estratégia de pricing",
        "keywords": ["preco", "precificacao", "pricing", "aumentar preco",
                     "desconto permanente", "tabela", "margem", "reajuste"],
        "entidades_extras": [
            {"papel": "BaseClientes", "descricao": "Clientes atuais que serão afetados"},
            {"papel": "ConcorrentePreco", "descricao": "Referência de preço do mercado"},
            {"papel": "Elasticidade", "descricao": "Sensibilidade do cliente a preço"},
        ],
        "perguntas_chave": [
            "Quantos clientes perco com esse aumento?",
            "O concorrente está mais caro ou mais barato?",
            "A percepção de valor justifica o preço?",
        ],
    },
}


# ============================================================
# DETECÇÃO BIDIMENSIONAL
# ============================================================

def detect_sector_and_decision(simulation_requirement: str) -> Tuple[str, str]:
    """
    Detecta SETOR e TIPO DE DECISÃO a partir do texto.
    
    Returns:
        (setor_key, decisao_key)
    
    Exemplos:
        "abrir loja de calçados em Pádua" → ("varejo_local", "novo_negocio")
        "Menu Certo promoção TV Copa" → ("marketplace_app", "promocao_campanha")
        "Copapa lançar papel higiênico" → ("industria_fmcg", "novo_produto")
        "Milla Internet filial São Fidélis" → ("telecom_isp", "expansao_geografica")
    """
    text = simulation_requirement.lower()
    
    # Detectar setor
    sector_scores = {}
    for key, template in SETORES.items():
        score = sum(2 if kw in text else 0 for kw in template["keywords"])
        # Bonus for exact match on longer keywords
        for kw in template["keywords"]:
            if len(kw) > 5 and kw in text:
                score += 3
        sector_scores[key] = score
    
    best_sector = max(sector_scores, key=sector_scores.get)
    if sector_scores[best_sector] == 0:
        best_sector = "varejo_local"  # fallback
    
    # Detectar tipo de decisão
    decision_scores = {}
    for key, template in TIPOS_DECISAO.items():
        score = sum(2 if kw in text else 0 for kw in template["keywords"])
        for kw in template["keywords"]:
            if len(kw) > 5 and kw in text:
                score += 3
        decision_scores[key] = score
    
    best_decision = max(decision_scores, key=decision_scores.get)
    if decision_scores[best_decision] == 0:
        best_decision = "novo_negocio"  # fallback
    
    # Ajustes de contexto cruzado
    # Se tem "franquia" no setor, o tipo provavelmente é expansão
    if best_sector == "franquia" and best_decision == "novo_negocio":
        best_decision = "expansao_franquia"
        # E o setor real é outro — tentar segundo melhor
        sector_scores.pop("franquia")
        best_sector = max(sector_scores, key=sector_scores.get) if sector_scores else "varejo_local"
    
    # Se detectou "delivery" ou "app" no alimentação, pode ser marketplace
    if best_sector == "alimentacao" and any(kw in text for kw in ["app", "delivery", "aplicativo"]):
        if sector_scores.get("marketplace_app", 0) > 0:
            best_sector = "marketplace_app"
    
    return best_sector, best_decision


def get_ontology_system_prompt_v3(sector: str, decision: str) -> str:
    """
    Gera prompt de ontologia combinando SETOR + TIPO DE DECISÃO.
    
    Cada combinação gera entidades diferentes:
    - varejo_local + novo_negocio → Incumbente, Entrante, ConsumidorFiel...
    - marketplace_app + promocao_campanha → BaseAtual, PublicoNovo, CustoPromocao...
    - industria_fmcg + novo_produto → ProdutoNovo, CanalDistribuicao, ConcorrenteDireto...
    """
    setor_info = SETORES.get(sector, SETORES["varejo_local"])
    decisao_info = TIPOS_DECISAO.get(decision, TIPOS_DECISAO["novo_negocio"])
    
    # Montar entidades da decisão
    entities_text = ""
    for i, ent in enumerate(decisao_info["entidades_extras"], 1):
        entities_text += f"  {i}. **{ent['papel']}**: {ent['descricao']}\n"
    
    # Montar perguntas-chave
    perguntas_text = "\n".join(f"  - {p}" for p in decisao_info["perguntas_chave"])
    
    return f"""\
Você é especialista em design de ontologias para grafos de conhecimento.
Projete entidades e relacionamentos para simulação de opinião pública.

══════════════════════════════════════════════════════════════
【CONTEXTO BIDIMENSIONAL】
══════════════════════════════════════════════════════════════

**SETOR:** {setor_info['nome']}
**TIPO DE DECISÃO:** {decisao_info['nome']}

Esta combinação determina QUAIS ENTIDADES são relevantes.
Não invente entidades genéricas — foque nas que importam para ESTA decisão.

══════════════════════════════════════════════════════════════
【ENTIDADES OBRIGATÓRIAS PARA ESTE TIPO DE DECISÃO】
══════════════════════════════════════════════════════════════

{entities_text}

Adapte os nomes e atributos ao SETOR específico ({setor_info['nome']}).
Adicione 4-6 entidades extras relevantes para este setor.
Os 2 últimos DEVEM ser fallback: Person e Organization.
Total: EXATAMENTE 10 entity_types.

══════════════════════════════════════════════════════════════
【PERGUNTAS QUE O RELATÓRIO DEVE RESPONDER】
══════════════════════════════════════════════════════════════

As entidades e relações devem gerar dados suficientes para responder:

{perguntas_text}

Projete entidades que PRODUZAM esses dados durante a simulação.

══════════════════════════════════════════════════════════════
【FORMATO DE SAÍDA — JSON】
══════════════════════════════════════════════════════════════

{{
    "setor_detectado": "{sector}",
    "tipo_decisao": "{decision}",
    "entity_types": [
        {{
            "name": "PascalCase em inglês",
            "papel": "papel funcional (Entrante, Incumbente, etc.)",
            "description": "PT-BR (max 100 chars)",
            "attributes": [{{"name": "snake_case", "type": "text", "description": "PT-BR"}}],
            "examples": ["Exemplo em PT-BR"]
        }}
    ],
    "edge_types": [
        {{
            "name": "UPPER_SNAKE_CASE",
            "description": "PT-BR",
            "source_targets": [{{"source": "Tipo", "target": "Tipo"}}]
        }}
    ],
    "analysis_summary": "PT-BR",
    "perguntas_chave": {json.dumps(decisao_info['perguntas_chave'], ensure_ascii=False)}
}}

══════════════════════════════════════════════════════════════
【REGRAS】
══════════════════════════════════════════════════════════════

1. EXATAMENTE 10 entity_types (8 específicos + Person + Organization)
2. Cada entidade DEVE ter "papel" funcional
3. Nomes técnicos: INGLÊS (PascalCase / UPPER_SNAKE_CASE / snake_case)
4. Descrições: PORTUGUÊS DO BRASIL
5. ZERO caracteres chineses
6. Entidades = AGENTES reais que podem agir, NÃO conceitos abstratos
7. Atributos proibidos: name, uuid, group_id, created_at, summary
"""


# ============================================================
# TABELA DE EXEMPLOS — Para referência e testes
# ============================================================

EXEMPLOS_CENARIOS = [
    {
        "descricao": "Menu Certo app de delivery quer fazer promocao de dar uma TV na Copa",
        "setor_esperado": "marketplace_app",
        "decisao_esperada": "promocao_campanha",
        "entidades_chave": ["BaseUsuariosAtual", "PublicoNovo", "ConcorrenteDelivery",
                           "CustoPromocao", "MidiaCanal", "RestaurantesParceiros"],
    },
    {
        "descricao": "Copapa companhia de papeis quer lancar novo papel higienico",
        "setor_esperado": "industria_fmcg",
        "decisao_esperada": "novo_produto",
        "entidades_chave": ["ProdutoNovo", "ProdutoExistente", "ConcorrenteFMCG",
                           "Varejista", "ConsumidorFinal", "CanalDistribuicao"],
    },
    {
        "descricao": "Evo Solar quer lancar eletro carregadores Evo Mov",
        "setor_esperado": "energia_tech",
        "decisao_esperada": "novo_produto",
        "entidades_chave": ["CarregadorEV", "MercadoVeiculosEletricos", "ConcorrenteTech",
                           "ConsumidorEV", "ReguladorEnergia", "PontosInstalacao"],
    },
    {
        "descricao": "Menu Certo quer abrir franquia em Nova Friburgo",
        "setor_esperado": "marketplace_app",
        "decisao_esperada": "expansao_franquia",
        "entidades_chave": ["Franqueador", "MercadoLocal", "ConcorrenteLocal",
                           "ConsumidorLocal", "RestaurantesRegiao"],
    },
    {
        "descricao": "Milla Internet quer abrir filial em Sao Fidelis",
        "setor_esperado": "telecom_isp",
        "decisao_esperada": "expansao_geografica",
        "entidades_chave": ["ProvedorOrigem", "MercadoDestino", "ConcorrenteISP",
                           "ConsumidorLocal", "InfraestruturaFibra"],
    },
    {
        "descricao": "itcast quer lancar o SaaS Converzas",
        "setor_esperado": "saas_b2b",
        "decisao_esperada": "novo_produto",
        "entidades_chave": ["NovoProdutoSaaS", "ICPDecisor", "ConcorrenteSaaS",
                           "CanalAquisicao", "Integrador"],
    },
    {
        "descricao": "Fernando quer abrir loja de moveis em Criciuma",
        "setor_esperado": "varejo_local",
        "decisao_esperada": "novo_negocio",
        "entidades_chave": ["NovaLoja", "Incumbente", "ConsumidorAlvo",
                           "CanalDigital", "CanalInformal"],
    },
]


if __name__ == "__main__":
    print("=" * 70)
    print("TESTE DE DETECÇÃO BIDIMENSIONAL")
    print("=" * 70)
    
    acertos = 0
    total = len(EXEMPLOS_CENARIOS)
    
    for ex in EXEMPLOS_CENARIOS:
        setor, decisao = detect_sector_and_decision(ex["descricao"])
        ok_setor = setor == ex["setor_esperado"]
        ok_decisao = decisao == ex["decisao_esperada"]
        ok = ok_setor and ok_decisao
        if ok: acertos += 1
        
        status = "✓" if ok else "✗"
        print(f"\n{status} {ex['descricao'][:60]}")
        print(f"  Setor:   {setor:20} {'✓' if ok_setor else '✗ esperado: ' + ex['setor_esperado']}")
        print(f"  Decisao: {decisao:20} {'✓' if ok_decisao else '✗ esperado: ' + ex['decisao_esperada']}")
    
    print(f"\n{'=' * 70}")
    print(f"RESULTADO: {acertos}/{total} cenarios corretos ({acertos/total*100:.0f}%)")
    print(f"Setores: {len(SETORES)} | Tipos decisao: {len(TIPOS_DECISAO)}")
    print(f"Combinacoes possiveis: {len(SETORES) * len(TIPOS_DECISAO)}")
