"""
AUGUR — Contrato de Dados do Relatório v1.1

Define o schema completo que todas as camadas do pipeline usam:
  Zep (ontologia) → OpenAI (análise) → PDF/Web (renderização)

Regra: se o campo não existe no JSON, a seção não renderiza.
Se existe, renderiza exatamente como definido. Zero surpresas.

Caminho: backend/app/schemas/report_schema.py
"""

from typing import TypedDict, Optional
from enum import Enum
import json
import re


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

class SetorNegocio(str, Enum):
    VAREJO_LOCAL = "varejo_local"
    SAAS_B2B = "saas_b2b"
    INDUSTRIA_FMCG = "industria_fmcg"
    TELECOM_ISP = "telecom_isp"
    ENERGIA_TECH = "energia_tech"
    ALIMENTACAO = "alimentacao"
    MARKETPLACE_APP = "marketplace_app"
    SERVICOS = "servicos"
    FRANQUIA = "franquia"

class TipoDecisao(str, Enum):
    NOVO_NEGOCIO = "novo_negocio"
    NOVO_PRODUTO = "novo_produto"
    PROMOCAO_CAMPANHA = "promocao_campanha"
    EXPANSAO_GEOGRAFICA = "expansao_geografica"
    EXPANSAO_FRANQUIA = "expansao_franquia"
    PRECIFICACAO = "precificacao"


# ============================================================
# SEÇÕES DO RELATÓRIO — TypeDicts
# ============================================================

class MetaAnalise(TypedDict):
    projeto: str
    setor: str                      # SetorNegocio
    tipo_decisao: str               # TipoDecisao
    data_geracao: str               # ISO 8601
    modelo_ia: str
    num_agentes: int
    num_rodadas: int
    periodo_simulado_meses: int


class VeredictoPrincipal(TypedDict):
    tipo: str                       # GO | NO-GO | AJUSTAR
    score_viabilidade: int          # 0-100
    frase_chave: str                # max 200 chars
    resumo_executivo: str
    leitura_para_decisao: str
    top5_fatos: list[dict]          # [{titulo, descricao}]


class DashboardKPIs(TypedDict):
    ticket_medio: str
    volume_breakeven: str
    margem_bruta_alvo: str
    capital_giro_necessario: str
    recompra_alvo: str
    vendas_por_indicacao: str
    erosao_margem_sazonal: str
    breakeven_cenario1: str
    contatos_mes_inicial: str
    conversao_inicial: str
    faturamento_maduro: str
    prob_sobrevivencia_24m: str
    investimento_total_estimado: str
    composicao_investimento: list[dict]  # [{item, valor}]
    sinais_consolidacao: list[str]
    sinais_alerta: list[str]
    sinais_risco_critico: list[str]


class Cenario(TypedDict):
    nome: str
    probabilidade: int              # 0-100, soma dos 3 = 100
    impacto_financeiro: str
    breakeven: str
    faturamento_m24: str
    margem_bruta: str
    recompra: str
    risco_central: str
    capital_giro: str
    descricao: str
    citacao_agente: str
    projecao_faturamento_24m: list[float]  # 25 valores (M0-M24)


class CenariosFuturos(TypedDict):
    cenarios: list[Cenario]         # EXATAMENTE 3
    ponto_bifurcacao: str


class FatorRisco(TypedDict):
    numero: int
    titulo: str                     # NUNCA truncar
    probabilidade: int
    impacto: str                    # Alto | Medio | Baixo
    descricao: str
    citacao_agente: str


class FatoresRisco(TypedDict):
    texto_introducao: str
    riscos: list[FatorRisco]        # 5-7 riscos


class DistribuicaoEmocional(TypedDict):
    emocoes: list[dict]             # [{nome, percentual}]
    saldo_positivo_vs_negativo: str
    texto_confianca: str
    citacao_confianca: str
    texto_ceticismo: str
    citacao_ceticismo: str
    texto_empolgacao: str
    texto_medo: str
    evolucao_24m: dict[str, list[float]]


class PerfilAgente(TypedDict):
    nome: str
    descricao: str
    tipo: str                       # Apoiador | Neutro | Resistente | Cauteloso
    posicao_espectro: float         # 0.0 a 1.0
    citacao_chave: str
    papel_na_dinamica: str


class BlocoForca(TypedDict):
    nome: str
    base_clientes: str
    descricao: str
    poder_relativo: int             # 1-10
    citacao: Optional[str]


class MapaForcas(TypedDict):
    blocos: list[BlocoForca]
    hierarquia_poder: str
    coalizao_entrante: str


class FaseCronologia(TypedDict):
    nome: str
    periodo: str
    mes_inicio: int
    mes_fim: int
    descricao: str
    citacao: str
    marcos: list[str]


class Cronologia(TypedDict):
    fases: list[FaseCronologia]     # 4 fases


class PadraoEmergente(TypedDict):
    numero: int
    titulo: str
    descricao: str


class Recomendacao(TypedDict):
    rank: int
    titulo: str
    descricao: str
    citacao: Optional[str]
    impacto_relativo: int           # 0-100


class ItemChecklist(TypedDict):
    titulo: str
    timing: str
    justificativa: str
    condicao_mensuravel: str
    prioridade: str                 # Urgencia


class Previsao(TypedDict):
    periodo: str
    titulo: str
    probabilidade: int
    margem_erro: int
    descricao: str


class Posicionamento(TypedDict):
    percebido_descricao: str
    percebido_citacao: str
    desejado_descricao: str
    desejado_citacao: str
    rotulos_a_evitar: list[str]
    posicionamento_vencedor: str
    players: list[dict]             # [{nome, x, y, papel}]


class ROIAnalise(TypedDict):
    riscos_evitados: list[dict]     # [{titulo, valor_risco, solucao}]
    custo_analise: str
    risco_total_evitado: str
    roi_multiplicador: str
    citacoes: list[str]


class DadoMercado(TypedDict):
    titulo: str
    conteudo: str
    fontes: list[str]


class ContextoMercado(TypedDict):
    """Seção NOVA: Dados de mercado verificados via Perplexity."""
    localizacao: str
    setor_detalhe: str
    dados: list[DadoMercado]
    fontes_unicas: list[str]
    total_queries: int
    disclaimer: str


class SinteseFinal(TypedDict):
    scores: dict                    # {viabilidade_financeira: 67, demanda: 81, ...}
    veredicto_final: str
    cenario_mais_provavel: str
    risco_principal: str
    direcionamento: list[str]
    sinais_consolidacao: list[str]
    sinais_alerta: list[str]
    sinais_risco: list[str]


# ============================================================
# SCHEMA COMPLETO
# ============================================================

class AugurReportSchema(TypedDict):
    meta: MetaAnalise
    veredicto: VeredictoPrincipal
    dashboard: DashboardKPIs
    contexto_mercado: Optional[ContextoMercado]  # Perplexity — dados verificados
    cenarios: CenariosFuturos
    riscos: FatoresRisco
    emocional: DistribuicaoEmocional
    agentes: list[PerfilAgente]
    forcas: MapaForcas
    cronologia: Cronologia
    padroes: list[PadraoEmergente]
    recomendacoes: list[Recomendacao]
    checklist: list[ItemChecklist]
    previsoes: list[Previsao]
    posicionamento: Posicionamento
    roi: ROIAnalise
    sintese: SinteseFinal


# ============================================================
# MAPEAMENTO CAMPO → GRÁFICO
# ============================================================

GRAFICOS_POR_SECAO = {
    "veredicto": {"gauge_semicircular": {"dados": "veredicto.tipo"}},
    "dashboard": {
        "kpi_grid_3x4": {"dados": "dashboard.*"},
        "semaforo_3col": {"dados": "dashboard.sinais_*"},
    },
    "contexto_mercado": {
        "cards_dados_verificados": {"dados": "contexto_mercado.dados[]"},
    },
    "cenarios": {
        "barras_horizontais": {"dados": "cenarios[].probabilidade"},
        "area_chart_24m": {"dados": "cenarios[].projecao_faturamento_24m"},
        "tabela_comparativa": {"dados": "cenarios[]"},
    },
    "riscos": {"scatter_prob_x_impacto": {"dados": "riscos[].probabilidade+impacto"}},
    "emocional": {
        "radar_6_eixos": {"dados": "emocional.emocoes[]"},
        "barras_horizontais": {"dados": "emocional.emocoes[]"},
        "linhas_evolucao_24m": {"dados": "emocional.evolucao_24m"},
    },
    "agentes": {"espectro_horizontal": {"dados": "agentes[].posicao_espectro"}},
    "forcas": {"grafo_rede": {"dados": "forcas.blocos"}},
    "cronologia": {"timeline_horizontal": {"dados": "cronologia.fases[]"}},
    "recomendacoes": {"stack_ranking_barras": {"dados": "recomendacoes[].impacto_relativo"}},
    "previsoes": {"barras_com_error_bars": {"dados": "previsoes[].probabilidade+margem_erro"}},
    "posicionamento": {"scatter_2d": {"dados": "posicionamento.players[]"}},
    "roi": {"barras_comparativas": {"dados": "roi.riscos_evitados[]"}},
    "sintese": {"radar_5_eixos": {"dados": "sintese.scores"}},
}


# ============================================================
# VALIDAÇÃO
# ============================================================

def validar_report_json(data: dict) -> list[str]:
    erros = []

    campos = [
        'meta', 'veredicto', 'dashboard', 'cenarios', 'riscos',
        'emocional', 'agentes', 'forcas', 'cronologia', 'padroes',
        'recomendacoes', 'checklist', 'previsoes', 'posicionamento',
        'roi', 'sintese'
    ]
    for c in campos:
        if c not in data:
            erros.append(f"Campo obrigatorio ausente: {c}")

    if 'cenarios' in data:
        cens = data['cenarios'].get('cenarios', [])
        if len(cens) != 3:
            erros.append(f"Deve ter 3 cenarios, tem {len(cens)}")
        probs = sum(c.get('probabilidade', 0) for c in cens)
        if probs != 100:
            erros.append(f"Probabilidades somam {probs}, devem somar 100")

    if 'riscos' in data:
        n = len(data['riscos'].get('riscos', []))
        if n < 3 or n > 7:
            erros.append(f"Deve ter 3-7 riscos, tem {n}")

    if 'agentes' in data and len(data['agentes']) < 3:
        erros.append("Deve ter pelo menos 3 agentes")

    if 'recomendacoes' in data:
        n = len(data['recomendacoes'])
        if n < 3 or n > 5:
            erros.append(f"Deve ter 3-5 recomendacoes, tem {n}")

    if 'veredicto' in data:
        v = data['veredicto']
        if v.get('tipo') not in ['GO', 'NO-GO', 'AJUSTAR']:
            erros.append(f"Veredicto invalido: {v.get('tipo')}")

    # Chinês
    json_str = json.dumps(data, ensure_ascii=False)
    chinese = re.findall(r'[\u4e00-\u9fff]', json_str)
    if chinese:
        erros.append(f"CRITICO: {len(chinese)} caracteres chineses no JSON")

    return erros
