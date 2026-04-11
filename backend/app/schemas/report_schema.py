# ============================================================
# AUGUR — CONTRATO DE DADOS DO RELATÓRIO v1.0
# ============================================================
#
# Este arquivo define o schema COMPLETO que o relatório precisa.
# É o contrato entre 3 camadas:
#
#   CAMADA 1: Zep (grafo de conhecimento)
#     → Produz: ontologia tipada por nicho
#     → Consumido por: OpenAI (simulação + análise)
#
#   CAMADA 2: OpenAI (simulação + report_agent)
#     → Produz: JSON estruturado com 16 seções tipadas
#     → Consumido por: Report Renderer (PDF + Web)
#
#   CAMADA 3: Report Renderer (pdf_generator + ReportView)
#     → Consome: JSON estruturado
#     → Produz: PDF de 22 páginas + visualização web
#
# REGRA DE OURO: Nenhuma camada inventa dados.
# Se o campo não existe no JSON, a seção não é renderizada.
# Se o campo existe, é renderizado exatamente como definido.
#
# Aprovado pelo Conselho AUGUR: 61/61 votos
# ============================================================

from typing import TypedDict, Optional
from enum import Enum


# ============================================================
# ENUMS
# ============================================================

class Veredicto(str, Enum):
    GO = "GO"
    NO_GO = "NO-GO"
    AJUSTAR = "AJUSTAR"

class Impacto(str, Enum):
    ALTO = "Alto"
    MEDIO = "Medio"
    BAIXO = "Baixo"

class Urgencia(str, Enum):
    URGENTE = "Urgente"
    ALTA = "Alta"
    MEDIA = "Media"
    BAIXA = "Baixa"

class TipoAgente(str, Enum):
    APOIADOR = "Apoiador"
    NEUTRO = "Neutro"
    RESISTENTE = "Resistente"
    CAUTELOSO = "Cauteloso"

class FaseTimeline(str, Enum):
    CURIOSIDADE = "Curiosidade"
    TESTE = "Teste"
    VIRADA = "Virada"
    DISCIPLINA = "Disciplina"

class NichoNegocio(str, Enum):
    VAREJO_LOCAL = "varejo_local"
    SAAS_B2B = "saas_b2b"
    ALIMENTACAO = "alimentacao"
    SERVICOS = "servicos"
    MARKETPLACE = "marketplace"
    INDUSTRIA = "industria"
    EDUCACAO = "educacao"
    SAUDE = "saude"


# ============================================================
# CAMADA 1: ZEP — TEMPLATE DE GRAFO POR NICHO
# ============================================================
# O Zep precisa armazenar entidades com PAPÉIS funcionais,
# não tipos genéricos. Cada nicho tem um template diferente.
# 
# PROBLEMA ATUAL: O ontology_generator.py gera entidades como
# "Conceito", "Pessoa", "Organização" — genérico demais.
# O grafo não distingue "incumbente" de "entrante" de "regulador".
#
# SOLUÇÃO: Templates de grafo por nicho que definem quais
# entidades e relações são ESPERADAS para cada tipo de negócio.
# ============================================================

class ZepEntityTemplate(TypedDict):
    """Template de entidade para o grafo Zep"""
    papel: str          # Incumbente | Entrante | Canal | Regulador | Informal | Consumidor
    tipo_entidade: str  # PascalCase: PersonEntity, Company, MarketplaceDigital, etc.
    atributos_esperados: list[str]  # ["base_clientes", "faturamento_mensal", "moat"]
    descricao: str      # Descrição em PT-BR do papel no ecossistema

class ZepRelationTemplate(TypedDict):
    """Template de relação para o grafo Zep"""
    tipo: str           # UPPER_SNAKE_CASE: COMPETE_COM, FORNECE_PARA, REGULA
    source_papel: str   # Papel da entidade source
    target_papel: str   # Papel da entidade target
    atributos: list[str]  # ["intensidade", "tipo_competicao"]


# Templates por nicho
ZEP_TEMPLATES: dict[str, dict] = {
    "varejo_local": {
        "descricao": "Loja fisica em cidade pequena/media: calcados, roupas, eletronicos, etc.",
        "entidades_esperadas": [
            {"papel": "Incumbente", "tipo": "Company", "atributos": ["base_clientes", "num_lojas", "crediario_ativo", "tempo_mercado", "faturamento_estimado"]},
            {"papel": "Entrante", "tipo": "Company", "atributos": ["investimento_inicial", "nicho_proposto", "canal_primario"]},
            {"papel": "Canal_Digital", "tipo": "MarketplaceDigital", "atributos": ["base_usuarios_local", "preco_referencia", "frete_gratis_acima"]},
            {"papel": "Canal_Informal", "tipo": "PersonGroup", "atributos": ["faturamento_mensal", "desconto_vs_varejo", "frequencia_viagem"]},
            {"papel": "Consumidor_Fiel", "tipo": "PersonProfile", "atributos": ["faixa_etaria", "crediario_ativo", "frequencia_compra", "ticket_medio"]},
            {"papel": "Consumidor_Livre", "tipo": "PersonProfile", "atributos": ["faixa_etaria", "canais_compra", "sensibilidade_preco"]},
            {"papel": "Consumidor_Digital", "tipo": "PersonProfile", "atributos": ["apps_usados", "categorias_online", "resistencia_local"]},
            {"papel": "Regulador", "tipo": "GovernmentAgency", "atributos": ["procon", "vigilancia", "impostos_locais"]},
        ],
        "relacoes_esperadas": [
            {"tipo": "COMPETE_COM", "source": "Incumbente", "target": "Entrante"},
            {"tipo": "ANCORA_PRECO", "source": "Canal_Digital", "target": "Incumbente"},
            {"tipo": "COMPRIME_MARGEM", "source": "Canal_Informal", "target": "Entrante"},
            {"tipo": "FIDELIZADO_POR", "source": "Consumidor_Fiel", "target": "Incumbente"},
            {"tipo": "DISPONIVEL_PARA", "source": "Consumidor_Livre", "target": "Entrante"},
        ],
        "benchmarks": {
            "ticket_medio_setor": "R$120-280",
            "margem_bruta_tipica": "45-60%",
            "taxa_recompra_saudavel": "15-25%",
            "custo_crediario_inadimplencia": "3-8%",
            "sazonalidades": ["Dia das Maes (mai)", "Dia dos Namorados (jun)", "Dia dos Pais (ago)", "Black Friday (nov)", "Natal (dez)"],
        }
    },
    "saas_b2b": {
        "descricao": "Software as a Service para empresas",
        "entidades_esperadas": [
            {"papel": "Incumbente", "tipo": "Company", "atributos": ["arr", "num_clientes", "churn_mensal", "pricing"]},
            {"papel": "Entrante", "tipo": "Company", "atributos": ["investimento", "diferencial", "pricing_proposto"]},
            {"papel": "ICP", "tipo": "PersonProfile", "atributos": ["cargo", "empresa_tipo", "dor_principal", "budget"]},
            {"papel": "Canal_Aquisicao", "tipo": "Channel", "atributos": ["tipo", "cac", "conversion_rate"]},
            {"papel": "Regulador", "tipo": "GovernmentAgency", "atributos": ["lgpd", "certificacoes"]},
        ],
        "relacoes_esperadas": [
            {"tipo": "COMPETE_COM", "source": "Incumbente", "target": "Entrante"},
            {"tipo": "ADQUIRE_VIA", "source": "ICP", "target": "Canal_Aquisicao"},
        ],
        "benchmarks": {
            "cac_medio": "R$500-5000",
            "ltv_cac_ratio_saudavel": "3:1",
            "churn_mensal_aceitavel": "2-5%",
            "margem_bruta_saas": "70-85%",
            "tempo_payback_cac": "6-18 meses",
        }
    },
    # Outros nichos: alimentacao, servicos, marketplace, etc.
    # Serão adicionados conforme demanda
}


# ============================================================
# CAMADA 2: OPENAI — OUTPUT SCHEMA DA ANÁLISE
# ============================================================
# Este é o JSON EXATO que o report_agent.py deve pedir ao GPT.
# Cada campo mapeia diretamente para uma seção do relatório.
# Nenhum campo é texto livre não-estruturado.
# ============================================================

class MetaAnalise(TypedDict):
    """Metadados da análise"""
    projeto: str                    # Nome do projeto analisado
    nicho: str                      # NichoNegocio enum
    data_geracao: str               # ISO 8601
    modelo_ia: str                  # "GPT-5.4"
    num_agentes: int                # Quantidade de agentes na simulação
    num_rodadas: int                # Quantidade de rodadas
    periodo_simulado_meses: int     # Ex: 24


class VeredictoPrincipal(TypedDict):
    """Seção: Decisão em 30 Segundos + Resumo Executivo"""
    tipo: str                       # Veredicto: GO | NO-GO | AJUSTAR
    score_viabilidade: int          # 0-100
    frase_chave: str                # Uma frase que resume tudo (max 200 chars)
    resumo_executivo: str           # 2-4 parágrafos narrativos
    leitura_para_decisao: str       # 1 parágrafo: o que o dono deve fazer
    top5_fatos: list[dict]          # [{titulo, descricao}] — os 5 fatos que definem a decisão


class DashboardKPIs(TypedDict):
    """Seção NOVA: Dashboard de KPIs — 24 meses"""
    ticket_medio: str               # "R$160-240"
    volume_breakeven: str           # "70-110 pares/mês"
    margem_bruta_alvo: str          # "45-55%"
    capital_giro_necessario: str    # "R$30-50k"
    recompra_alvo: str              # "15%+"
    vendas_por_indicacao: str       # "20-30%"
    erosao_margem_sazonal: str      # "8-15%"
    breakeven_cenario1: str         # "M11-15"
    contatos_mes_inicial: str       # "80-180"
    conversao_inicial: str          # "5-12%"
    faturamento_maduro: str         # "R$25-40k/mês"
    prob_sobrevivencia_24m: str     # "74%"
    # Investimento consolidado (NOVO — pedido por Hormozi/Cuban)
    investimento_total_estimado: str  # "R$80-150k" (soma de tudo)
    composicao_investimento: list[dict]  # [{item, valor}] — detalhamento
    # Semáforo
    sinais_consolidacao: list[str]  # ["Recompra acima de 15%", ...]
    sinais_alerta: list[str]        # ["Conversão abaixo de 8%", ...]
    sinais_risco_critico: list[str] # ["Break-even não atinge até M18", ...]


class Cenario(TypedDict):
    """Um cenário futuro"""
    nome: str                       # "Nicho útil com canal direto vira alternativa estável"
    probabilidade: int              # 0-100 (soma dos 3 = 100)
    impacto_financeiro: str         # "positivo moderado" | "negativo relevante" | etc.
    breakeven: str                  # "M11-15" | "M16-21" | "Não ocorre em 24 meses"
    faturamento_m24: str            # "R$35-60k/mês"
    margem_bruta: str               # "45-55%"
    recompra: str                   # "15-25%"
    risco_central: str              # "Recompra fraca"
    capital_giro: str               # "R$30-50k"
    descricao: str                  # 2-3 parágrafos narrativos
    citacao_agente: str             # A citação mais reveladora
    # Projeção mensal (NOVO — para gráfico area chart)
    projecao_faturamento_24m: list[float]  # [0, 2, 4, ...] — 24 valores em R$ mil


class CenariosFuturos(TypedDict):
    """Seção: Cenários Futuros + Cenários Financeiros Comparados"""
    cenarios: list[Cenario]         # EXATAMENTE 3 cenários
    ponto_bifurcacao: str           # Texto: o que separa os cenários


class FatorRisco(TypedDict):
    """Um fator de risco"""
    numero: int                     # 1-7
    titulo: str                     # Max 80 chars, texto completo SEM TRUNCAR
    probabilidade: int              # 0-100
    impacto: str                    # Impacto: Alto | Medio | Baixo
    descricao: str                  # 2-3 frases
    citacao_agente: str             # A citação mais reveladora


class FatoresRisco(TypedDict):
    """Seção: Fatores de Risco"""
    texto_introducao: str           # 1-2 frases contextuais
    riscos: list[FatorRisco]        # 5-7 riscos, ordenados por probabilidade desc


class DistribuicaoEmocional(TypedDict):
    """Seção: Análise Emocional"""
    emocoes: list[dict]             # [{nome: "Confiança", percentual: 31}, ...]
    # Obrigatórias: Confiança, Ceticismo, Empolgação, Medo, FOMO, Indiferença
    saldo_positivo_vs_negativo: str # "49% vs 36%"
    texto_confianca: str            # Parágrafo sobre confiança
    citacao_confianca: str
    texto_ceticismo: str            # Parágrafo sobre ceticismo
    citacao_ceticismo: str
    texto_empolgacao: str
    texto_medo: str
    # Evolução temporal (para gráfico de linhas)
    evolucao_24m: dict[str, list[float]]  # {"confianca": [15, 17, 19, ...], "ceticismo": [...]}


class PerfilAgente(TypedDict):
    """Seção NOVA: Perfis dos Agentes"""
    nome: str                       # "Tiago"
    descricao: str                  # "Jovem, early adopter, busca sneakers e performance"
    tipo: str                       # TipoAgente: Apoiador | Neutro | Resistente | Cauteloso
    posicao_espectro: float         # 0.0 (apoiador total) a 1.0 (resistente total)
    citacao_chave: str              # A fala mais reveladora
    papel_na_dinamica: str          # "Early adopter pragmático"


class BlocoForca(TypedDict):
    """Um bloco no mapa de forças"""
    nome: str                       # "Bloco dominante: Pecanha + crediário + capital social"
    base_clientes: str              # "3.000-4.500 clientes ativos"
    descricao: str                  # 2-3 frases
    poder_relativo: int             # 1-10
    citacao: Optional[str]


class MapaForcas(TypedDict):
    """Seção: Mapa de Forças"""
    blocos: list[BlocoForca]        # 3-5 blocos
    hierarquia_poder: str           # "1. Pecanha (retenção). 2. Marketplaces (preço). ..."
    coalizao_entrante: str          # Quem pode ser aliado
    # Dados para grafo visual
    nodes: list[dict]               # [{nome, x, y, papel, tamanho}]
    edges: list[dict]               # [{source, target, tipo, forca}]


class FaseTimeline(TypedDict):
    """Uma fase na cronologia"""
    nome: str                       # "Curiosidade"
    periodo: str                    # "M0-3"
    mes_inicio: int                 # 0
    mes_fim: int                    # 3
    descricao: str                  # 2-3 frases
    citacao: str                    # Citação do agente
    marcos: list[str]               # ["Lançamento", "Fim curiosidade inicial"]


class Cronologia(TypedDict):
    """Seção: Cronologia da Simulação"""
    fases: list[FaseTimeline]       # EXATAMENTE 4 fases


class PadraoEmergente(TypedDict):
    """Seção: Padrões Emergentes"""
    numero: int
    titulo: str
    descricao: str


class Recomendacao(TypedDict):
    """Seção: Recomendações Estratégicas"""
    rank: int                       # 1 = mais importante
    titulo: str                     # "#1 Construir base própria de recompra via showroom + WhatsApp"
    descricao: str                  # 2-3 frases
    citacao: Optional[str]          # Citação de suporte
    impacto_relativo: int           # 0-100 (para barra de stack ranking)


class ItemChecklist(TypedDict):
    """Seção NOVA: Checklist AJUSTAR → GO"""
    titulo: str                     # "Capital de giro R$30-50k reservado para crediário"
    timing: str                     # "Pré-lançamento" | "Mês 1" | "M6-12" | "Permanente"
    justificativa: str              # "Sem isso, crediário estrangula caixa em 6 meses"
    condicao_mensuravel: str        # "R$30-50k disponível em conta"
    prioridade: str                 # Urgencia enum


class Previsao(TypedDict):
    """Seção: Previsões com Intervalo de Confiança"""
    periodo: str                    # "M1-3"
    titulo: str                     # "Captação inicial com conversão baixa"
    probabilidade: int              # 0-100
    margem_erro: int                # +/- p.p.
    descricao: str                  # Métricas concretas


class Posicionamento(TypedDict):
    """Seção: Posicionamento Percebido vs Desejado"""
    percebido_descricao: str        # Como o mercado vai ler a loja inicialmente
    percebido_citacao: str
    desejado_descricao: str         # Como a loja DEVERIA ser lida
    desejado_citacao: str
    rotulos_a_evitar: list[str]     # ["Mais uma multimarcas", "Boutique de internet", ...]
    posicionamento_vencedor: str    # "Lá eles resolvem."
    # Dados para gráfico 2D
    players: list[dict]             # [{nome, x, y, papel}] — posição no quadrante
    eixo_x_label: str               # "Preço acessível <---> Preço premium"
    eixo_y_label: str               # "Funcional <---> Aspiracional"


class ROIAnalise(TypedDict):
    """Seção NOVA: ROI da Análise"""
    riscos_evitados: list[dict]     # [{titulo, valor_risco, solucao}]
    custo_analise: str              # "R$2-5k"
    risco_total_evitado: str        # "R$75-150k"
    roi_multiplicador: str          # "30-75x"
    citacoes: list[str]             # 2-3 citações de valor


class SinteseFinal(TypedDict):
    """Seção: Síntese Final e Direcionamento"""
    # Radar de viabilidade (5 eixos)
    scores: dict                    # {"viabilidade_financeira": 67, "demanda": 81, "timing": 50, ...}
    veredicto_final: str            # Veredicto enum
    cenario_mais_provavel: str      # Resumo do cenário #1
    risco_principal: str            # Resumo do risco #1
    direcionamento: list[str]       # 3 ações prioritárias
    sinais_consolidacao: list[str]
    sinais_alerta: list[str]
    sinais_risco: list[str]


# ============================================================
# SCHEMA COMPLETO DO RELATÓRIO
# ============================================================

class AugurReportSchema(TypedDict):
    """
    CONTRATO FINAL: Este é o JSON que o report_agent DEVE produzir
    e que o pdf_generator/ReportView DEVE consumir.
    
    ZERO texto livre não-estruturado.
    ZERO parsing de regex.
    ZERO surpresas.
    """
    # Meta
    meta: MetaAnalise
    
    # P1-2: Capa + Decisão 30s
    veredicto: VeredictoPrincipal
    
    # P3: Dashboard KPIs (NOVO)
    dashboard: DashboardKPIs
    
    # P4-5: Cenários Futuros + Financeiros (NOVO)
    cenarios: CenariosFuturos
    
    # P6-7: Fatores de Risco
    riscos: FatoresRisco
    
    # P8: Análise Emocional
    emocional: DistribuicaoEmocional
    
    # P9: Perfis dos Agentes (NOVO)
    agentes: list[PerfilAgente]
    
    # P10: Mapa de Forças
    forcas: MapaForcas
    
    # P11: Cronologia
    cronologia: Cronologia
    
    # P12: Padrões Emergentes
    padroes: list[PadraoEmergente]
    
    # P13: Recomendações Estratégicas
    recomendacoes: list[Recomendacao]
    
    # P14: Checklist GO/NO-GO (NOVO)
    checklist: list[ItemChecklist]
    
    # P15: Previsões com Intervalo de Confiança
    previsoes: list[Previsao]
    
    # P16: Posicionamento
    posicionamento: Posicionamento
    
    # P17: ROI da Análise (NOVO)
    roi: ROIAnalise
    
    # P18: Síntese Final
    sintese: SinteseFinal


# ============================================================
# EXEMPLO: JSON de saída para o caso "loja de calçados"
# ============================================================
# Este exemplo serve como referência para o prompt do GPT.
# O report_agent.py DEVE incluir este exemplo no system prompt
# para que o GPT entenda o formato exato esperado.
# ============================================================

EXEMPLO_OUTPUT = {
    "meta": {
        "projeto": "Abertura de loja de calcados de nicho em Santo Antonio de Padua",
        "nicho": "varejo_local",
        "data_geracao": "2026-04-11T03:47:00Z",
        "modelo_ia": "GPT-5.4",
        "num_agentes": 6,
        "num_rodadas": 5,
        "periodo_simulado_meses": 24
    },
    "veredicto": {
        "tipo": "AJUSTAR",
        "score_viabilidade": 52,
        "frase_chave": "Ha espaco para entrar, mas somente com diferenciacao clara, disciplina de margem e narrativa comunitaria para enfrentar Grupo Pecanha, marketplaces e sacoleiras.",
        "resumo_executivo": "A simulacao aponta que o negocio sobrevive nos 24 meses...",
        "leitura_para_decisao": "A previsao nao autoriza lancamento padrao. Autoriza entrada ajustada...",
        "top5_fatos": [
            {"titulo": "Confianca do incumbente blinda a base", "descricao": "Grupo Pecanha mantem 3.000 a 4.500 clientes ativos de crediario..."},
            {"titulo": "Spasso operou com janela secundaria", "descricao": "Com 800 a 1.200 clientes ativos..."},
            {"titulo": "Captar cliente livre e o caminho viavel", "descricao": "A desvantagem de aquisicao e critica..."},
            {"titulo": "Lojas com crediario registram alta recorrencia", "descricao": "Retorno mensal de 40% a 60%..."},
            {"titulo": "Shopee ancora preco mental para todos", "descricao": "Conhecida por todos. Tenis de referencia a R$149..."}
        ]
    },
    "dashboard": {
        "ticket_medio": "R$160-240",
        "volume_breakeven": "70-110 pares/mes",
        "margem_bruta_alvo": "45-55%",
        "capital_giro_necessario": "R$30-50k",
        "recompra_alvo": "15%+",
        "vendas_por_indicacao": "20-30%",
        "erosao_margem_sazonal": "8-15%",
        "breakeven_cenario1": "M11-15",
        "contatos_mes_inicial": "80-180",
        "conversao_inicial": "5-12%",
        "faturamento_maduro": "R$25-40k/mes",
        "prob_sobrevivencia_24m": "74%",
        "investimento_total_estimado": "R$80-150k",
        "composicao_investimento": [
            {"item": "Capital de giro crediario", "valor": "R$30-50k"},
            {"item": "Estoque inicial (5 linhas)", "valor": "R$15-25k"},
            {"item": "Reforma e mobiliario", "valor": "R$10-20k"},
            {"item": "Marketing lancamento", "valor": "R$5-10k"},
            {"item": "Reserva 3 meses operacao", "valor": "R$20-45k"}
        ],
        "sinais_consolidacao": [
            "Recompra acima de 15%",
            "Indicacao espontanea acima de 20%",
            "Margem preservada acima de 45%",
            "Retencao acima de 40%"
        ],
        "sinais_alerta": [
            "Conversao abaixo de 8%",
            "Desconto acima de 15% fora de itens ancora",
            "Contatos abaixo de 100/mes ate M6"
        ],
        "sinais_risco_critico": [
            "Break-even nao atinge ate M18",
            "Guerra de preco sem disciplina",
            "Reputacao negativa no WhatsApp",
            "Retencao abaixo de 35%"
        ]
    },
    "cenarios": {
        "cenarios": [
            {
                "nome": "Nicho util com canal direto vira alternativa estavel ao dominante",
                "probabilidade": 45,
                "impacto_financeiro": "positivo moderado",
                "breakeven": "M11-15",
                "faturamento_m24": "R$35-60k/mes",
                "margem_bruta": "45-55%",
                "recompra": "15-25%",
                "risco_central": "Recompra fraca",
                "capital_giro": "R$30-50k",
                "descricao": "Neste futuro, a loja encontra espaco proprio ao operar como versao profissionalizada do comercio social local...",
                "citacao_agente": "O WhatsApp, pra mim, e onde a venda realmente acontece.",
                "projecao_faturamento_24m": [0,2,4,6,9,12,15,18,22,26,30,33,36,39,42,45,47,49,51,53,55,56,57,58,60]
            },
            {
                "nome": "Sobrevive com folego curto e break-even tardio",
                "probabilidade": 35,
                "impacto_financeiro": "negativo relevante",
                "breakeven": "M16-21",
                "faturamento_m24": "R$25-40k/mes",
                "margem_bruta": "35-45%",
                "recompra": "8-15%",
                "risco_central": "Caixa apertado",
                "capital_giro": "R$30-50k",
                "descricao": "Trafego existe, curiosidade existe, mas recompra avanca devagar...",
                "citacao_agente": "Pra continuar comprando, eu precisaria sentir que nao estou pagando mais caro so por ser diferente.",
                "projecao_faturamento_24m": [0,1,3,4,6,8,10,12,14,16,18,20,22,24,25,27,28,30,31,33,34,35,36,37,38]
            },
            {
                "nome": "Guerra sazonal de preco corroi margem",
                "probabilidade": 20,
                "impacto_financeiro": "negativo critico",
                "breakeven": "Nao ocorre em 24 meses",
                "faturamento_m24": "R$15-25k/mes",
                "margem_bruta": "20-30%",
                "recompra": "<8%",
                "risco_central": "Margem destruida",
                "capital_giro": "R$50k+ (deficit)",
                "descricao": "A loja entra em confronto direto com incumbentes nas datas sazonais...",
                "citacao_agente": "Se o negocio depende demais de promocao pesada pra vender, ai o risco e grande.",
                "projecao_faturamento_24m": [0,2,4,5,7,8,9,10,11,12,13,14,14,15,15,16,16,17,17,18,18,19,19,20,20]
            }
        ],
        "ponto_bifurcacao": "Quem captar primeiro (livre vs crediario), como usar canal alternativo (resolucao vs catalogo), como se comportar nas sazonalidades (seletivo vs guerra aberta)."
    },
    # ... demais seções seguem o mesmo padrão
}


# ============================================================
# MAPEAMENTO: CAMPO → GRÁFICO NO PDF
# ============================================================
# Define qual gráfico cada campo gera no relatório final.
# O pdf_generator usa este mapeamento para saber o que renderizar.
# ============================================================

GRAFICOS_POR_SECAO = {
    "veredicto": {
        "gauge_semicircular": {"dados": "veredicto.tipo", "escala": "NO-GO → AJUSTAR → GO"},
    },
    "dashboard": {
        "kpi_grid_3x4": {"dados": "dashboard.*", "layout": "3 rows x 4 cols"},
        "semaforo_3col": {"dados": "dashboard.sinais_*", "cores": "verde/amarelo/vermelho"},
    },
    "cenarios": {
        "barras_horizontais": {"dados": "cenarios[].probabilidade", "cores": "teal/amber/red"},
        "area_chart_24m": {"dados": "cenarios[].projecao_faturamento_24m", "3_linhas": True},
        "tabela_comparativa": {"dados": "cenarios[] menos descricao/citacao", "6_metricas": True},
    },
    "riscos": {
        "scatter_prob_x_impacto": {"dados": "riscos[].probabilidade + impacto", "bolhas_coloridas": True},
    },
    "emocional": {
        "radar_6_eixos": {"dados": "emocional.emocoes[]", "percentuais": True},
        "barras_horizontais": {"dados": "emocional.emocoes[]", "ordenadas": True},
        "linhas_evolucao_24m": {"dados": "emocional.evolucao_24m", "4_linhas": True},
    },
    "agentes": {
        "espectro_horizontal": {"dados": "agentes[].posicao_espectro", "gradiente": "teal→red"},
    },
    "forcas": {
        "grafo_rede": {"dados": "forcas.nodes + edges", "tamanho_por_poder": True},
    },
    "cronologia": {
        "timeline_horizontal": {"dados": "cronologia.fases[]", "cores_por_fase": True},
    },
    "recomendacoes": {
        "stack_ranking_barras": {"dados": "recomendacoes[].impacto_relativo", "decrescente": True},
    },
    "previsoes": {
        "barras_com_error_bars": {"dados": "previsoes[].probabilidade + margem_erro"},
    },
    "posicionamento": {
        "scatter_2d": {"dados": "posicionamento.players[]", "quadrante": True},
    },
    "roi": {
        "barras_comparativas": {"dados": "roi.riscos_evitados[]", "sem_vs_com": True},
    },
    "sintese": {
        "radar_5_eixos": {"dados": "sintese.scores", "viabilidade_geral": True},
    },
}


# ============================================================
# VALIDAÇÃO
# ============================================================

def validar_report_json(data: dict) -> list[str]:
    """Valida se o JSON do relatório está completo e correto."""
    erros = []
    
    campos_obrigatorios = [
        'meta', 'veredicto', 'dashboard', 'cenarios', 'riscos',
        'emocional', 'agentes', 'forcas', 'cronologia', 'padroes',
        'recomendacoes', 'checklist', 'previsoes', 'posicionamento',
        'roi', 'sintese'
    ]
    
    for campo in campos_obrigatorios:
        if campo not in data:
            erros.append(f"Campo obrigatorio ausente: {campo}")
    
    # Validações específicas
    if 'cenarios' in data:
        cens = data['cenarios'].get('cenarios', [])
        if len(cens) != 3:
            erros.append(f"Deve ter exatamente 3 cenarios, tem {len(cens)}")
        probs = sum(c.get('probabilidade', 0) for c in cens)
        if probs != 100:
            erros.append(f"Probabilidades dos cenarios devem somar 100, somam {probs}")
    
    if 'riscos' in data:
        risks = data['riscos'].get('riscos', [])
        if len(risks) < 3 or len(risks) > 7:
            erros.append(f"Deve ter 3-7 riscos, tem {len(risks)}")
    
    if 'agentes' in data:
        if len(data['agentes']) < 3:
            erros.append(f"Deve ter pelo menos 3 perfis de agentes")
    
    if 'recomendacoes' in data:
        if len(data['recomendacoes']) < 3 or len(data['recomendacoes']) > 5:
            erros.append(f"Deve ter 3-5 recomendacoes")
    
    if 'veredicto' in data:
        v = data['veredicto']
        if v.get('tipo') not in ['GO', 'NO-GO', 'AJUSTAR']:
            erros.append(f"Veredicto invalido: {v.get('tipo')}")
        if len(v.get('frase_chave', '')) > 250:
            erros.append(f"frase_chave muito longa: {len(v['frase_chave'])} chars (max 250)")
    
    # Verificar chinês
    import json
    json_str = json.dumps(data, ensure_ascii=False)
    import re
    chinese = re.findall(r'[\u4e00-\u9fff]', json_str)
    if chinese:
        erros.append(f"CRITICO: {len(chinese)} caracteres chineses encontrados no JSON")
    
    return erros


if __name__ == '__main__':
    erros = validar_report_json(EXEMPLO_OUTPUT)
    if erros:
        print("ERROS DE VALIDACAO:")
        for e in erros:
            print(f"  - {e}")
    else:
        print("Schema valido!")
    
    import json
    print(f"\nCampos no schema: {len(AugurReportSchema.__annotations__)}")
    print(f"Graficos mapeados: {sum(len(v) for v in GRAFICOS_POR_SECAO.values())}")
    print(f"Templates de nicho: {len(ZEP_TEMPLATES)}")
