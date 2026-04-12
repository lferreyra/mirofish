"""
AUGUR Market Research — Pesquisa de mercado via Perplexity API.

Executa ANTES da simulação para calibrar o grafo Zep com dados reais.
Cada nicho (setor × tipo_decisao) gera queries específicas.

Custo: ~R$0,25-0,50 por simulação (8-12 queries)
Tempo: +20-40 segundos (queries paralelas)

Caminho: backend/app/services/market_research.py
"""

import os
import json
import logging
import re
import time
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

PERPLEXITY_API_KEY = os.environ.get('PERPLEXITY_API_KEY', '')
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = "sonar"


# ============================================================
# TEMPLATES DE QUERIES POR NICHO
# ============================================================

QUERY_TEMPLATES = {
    "varejo_local": {
        "novo_negocio": [
            "população {location} IBGE dados demográficos renda média",
            "lojas de {setor_detalhe} em {location} concorrentes principais",
            "preço médio {setor_detalhe} varejo {location} região",
            "aluguel comercial {location} centro preço metro quadrado",
            "comércio {location} economia local crescimento",
            "marketplaces digitais mais usados em cidades pequenas interior Brasil 2025 2026",
            "sazonalidade vendas {setor_detalhe} Brasil meses fortes",
            "taxa inadimplência crediário varejo Brasil 2025 2026",
        ],
        "novo_produto": [
            "mercado {setor_detalhe} Brasil tamanho market share 2025 2026",
            "concorrentes {setor_detalhe} principais marcas Brasil",
            "preço médio {setor_detalhe} varejo atacado",
            "tendências consumo {setor_detalhe} Brasil 2025 2026",
            "canais distribuição {setor_detalhe} Brasil",
        ],
        "promocao_campanha": [
            "promoções mais eficazes varejo brasileiro 2025 2026",
            "ROI promoções sorteio premiação varejo Brasil",
            "engajamento redes sociais promoção varejo Brasil",
            "regulamentação promoção sorteio SEAE Caixa Econômica",
        ],
    },
    "saas_b2b": {
        "novo_negocio": [
            "mercado SaaS Brasil tamanho TAM SAM 2025 2026",
            "concorrentes {setor_detalhe} SaaS Brasil pricing",
            "CAC médio SaaS B2B Brasil 2025 2026",
            "churn rate SaaS B2B Brasil benchmark",
            "investimento seed SaaS Brasil valores médios 2025 2026",
            "canais aquisição SaaS B2B Brasil mais eficientes",
        ],
        "novo_produto": [
            "mercado {setor_detalhe} Brasil concorrentes funcionalidades",
            "pricing SaaS {setor_detalhe} Brasil modelos",
            "demanda {setor_detalhe} PME Brasil",
            "integrações mais pedidas {setor_detalhe} SaaS",
        ],
    },
    "industria_fmcg": {
        "novo_produto": [
            "mercado {setor_detalhe} Brasil tamanho market share 2025 2026",
            "concorrentes {setor_detalhe} principais marcas participação mercado",
            "preço {setor_detalhe} atacado varejo margem distribuição",
            "canais distribuição {setor_detalhe} Brasil supermercados atacado",
            "regulamentação {setor_detalhe} ANVISA INMETRO requisitos",
            "tendências consumo {setor_detalhe} Brasil sustentabilidade",
            "custo produção {setor_detalhe} matéria prima Brasil",
        ],
    },
    "alimentacao": {
        "novo_negocio": [
            "restaurantes {setor_detalhe} em {location} concorrentes avaliações",
            "preço médio refeição {setor_detalhe} {location}",
            "custo aluguel ponto comercial {location} alimentação",
            "taxa iFood Rappi restaurante 2025 2026 comissão",
            "vigilância sanitária {location} requisitos restaurante",
            "população {location} hábitos alimentares",
        ],
        "promocao_campanha": [
            "promoções delivery app resultados ROI 2025 2026",
            "engajamento promoção restaurante redes sociais Brasil",
            "custo aquisição cliente delivery app Brasil",
            "promoções Copa do Mundo restaurantes delivery resultados",
        ],
    },
    "marketplace_app": {
        "promocao_campanha": [
            "promoções apps delivery Brasil ROI resultados 2025 2026",
            "custo aquisição usuário app delivery Brasil",
            "retenção usuário após promoção app delivery",
            "regulamentação promoção sorteio app digital SEAE",
            "promoções Copa do Mundo apps resultados engajamento",
            "concorrentes {setor_detalhe} promoções recentes",
        ],
        "expansao_franquia": [
            "{setor_detalhe} franquia modelo custos taxa",
            "mercado delivery {location} concorrentes",
            "população {location} dados demográficos delivery",
            "custo operação franquia delivery {location}",
        ],
    },
    "telecom_isp": {
        "expansao_geografica": [
            "provedores internet {location} concorrentes preços",
            "cobertura fibra óptica {location} infraestrutura",
            "população {location} domicílios conectados internet",
            "Anatel dados telecomunicações {location} região",
            "custo implantação fibra óptica cidade pequena Brasil",
            "ticket médio internet banda larga {location} região",
        ],
    },
    "energia_tech": {
        "novo_produto": [
            "mercado veículos elétricos Brasil 2025 2026 crescimento",
            "estações carregamento elétrico Brasil quantidade localização",
            "preço carregador veículo elétrico Brasil concorrentes",
            "regulamentação ANEEL estação carregamento elétrico",
            "demanda carregamento elétrico rodovias Brasil",
            "incentivos governo veículos elétricos Brasil 2025 2026",
        ],
    },
    "servicos": {
        "novo_negocio": [
            "{setor_detalhe} em {location} concorrentes preços",
            "demanda {setor_detalhe} {location} região",
            "preço médio {setor_detalhe} Brasil 2025 2026",
            "regulamentação {setor_detalhe} conselho classe requisitos",
            "canais aquisição clientes {setor_detalhe} Brasil",
        ],
    },
}

GENERIC_QUERIES = [
    "{requirement} mercado Brasil dados 2025 2026",
    "{requirement} concorrentes principais",
    "{requirement} preço custo investimento",
    "{requirement} tendências oportunidades riscos",
    "população economia {location} dados recentes",
]


# ============================================================
# HELPERS
# ============================================================

def extract_location(text: str) -> str:
    """Extrai cidade/região do texto da simulação."""
    patterns = [
        r'em\s+([A-Z][a-zà-ú]+(?:\s+(?:de|do|da|dos|das)\s+)?(?:[A-Z][a-zà-ú]+)?(?:\s+(?:de|do|da|dos|das)\s+)?(?:[A-Z][a-zà-ú]+)?)',
        r'(?:para|em|de)\s+([A-Z][a-zà-ú]+(?:\s+[A-Z][a-zà-ú]+)*)',
    ]
    stopwords = {'Brasil', 'Brasileiro', 'Nacional', 'Empresa', 'Loja', 'App', 'Novo', 'Nova'}
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            loc = match.group(1).strip()
            if loc not in stopwords and len(loc) > 3:
                return loc
    return "Brasil"


def extract_sector_detail(text: str) -> str:
    """Extrai detalhe do setor (ex: 'calçados', 'papel higiênico')."""
    cleaned = re.sub(r'^(abertura de|lancamento de|lançar|abrir|criar|montar)\s+', '', text.lower())
    cleaned = re.sub(r'\s+(em|para|de|do|da)\s+.*$', '', cleaned)
    words = cleaned.split()[:4]
    return ' '.join(words) if words else text[:30]


# ============================================================
# SERVIÇO PRINCIPAL
# ============================================================

class MarketResearcher:
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or PERPLEXITY_API_KEY
        if not self.api_key:
            logger.warning("PERPLEXITY_API_KEY não configurada. Market research desabilitado.")
    
    @property
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def research(self, simulation_requirement: str, sector: str, decision: str, max_queries: int = 8) -> dict:
        if not self.is_available:
            return self._empty_result()
        
        start = time.time()
        location = extract_location(simulation_requirement)
        setor_detalhe = extract_sector_detail(simulation_requirement)
        
        logger.info(f"Market research: setor={sector}, decisao={decision}, local={location}, detalhe={setor_detalhe}")
        
        queries = self._get_queries(sector, decision, simulation_requirement, location, setor_detalhe, max_queries)
        results = self._execute_parallel(queries)
        
        fontes_unicas = list(set(f for r in results for f in r.get("fontes", [])))
        contexto = self._format_context(results, location, setor_detalhe)
        elapsed = time.time() - start
        custo = len(results) * 0.005
        
        logger.info(f"Market research: {len(results)} queries, {len(fontes_unicas)} fontes, {elapsed:.1f}s, ~${custo:.3f}")
        
        return {
            "dados_mercado": results,
            "fontes_unicas": fontes_unicas,
            "contexto_formatado": contexto,
            "custo_estimado": custo,
            "queries_executadas": len(results),
            "tempo_segundos": round(elapsed, 1),
            "localizacao_detectada": location,
            "setor_detalhe": setor_detalhe,
        }
    
    def _get_queries(self, sector, decision, requirement, location, setor_detalhe, max_queries) -> list[str]:
        sector_templates = QUERY_TEMPLATES.get(sector, {})
        templates = sector_templates.get(decision, GENERIC_QUERIES)
        
        queries = []
        for t in templates[:max_queries]:
            q = t.format(
                requirement=requirement[:80],
                location=location,
                setor_detalhe=setor_detalhe,
            )
            queries.append(q)
        return queries
    
    def _execute_parallel(self, queries: list[str], max_workers: int = 4) -> list[dict]:
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._query_perplexity, q): q for q in queries}
            for future in as_completed(futures):
                query = futures[future]
                try:
                    results.append(future.result())
                except Exception as e:
                    logger.warning(f"Query falhou: {query[:50]}... - {e}")
                    results.append({"query": query, "resposta": f"Erro: {e}", "fontes": []})
        return results
    
    def _query_perplexity(self, query: str) -> dict:
        import requests
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": PERPLEXITY_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Você é um pesquisador de mercado brasileiro. "
                        "Responda de forma concisa e factual com dados numéricos quando possível. "
                        "Cite fontes. Responda em português do Brasil. "
                        "Foque em dados de 2024-2026."
                    ),
                },
                {"role": "user", "content": query},
            ],
            "max_tokens": 500,
            "temperature": 0.1,
            "return_citations": True,
        }
        
        response = requests.post(PERPLEXITY_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        citations = data.get("citations", [])
        
        return {
            "query": query,
            "resposta": answer,
            "fontes": citations if isinstance(citations, list) else [],
        }
    
    def _format_context(self, results: list[dict], location: str, setor_detalhe: str) -> str:
        parts = [
            f"## DADOS DE MERCADO VERIFICADOS (Pesquisa Perplexity — {len(results)} consultas)",
            f"## Localização: {location}",
            f"## Setor: {setor_detalhe}",
            "",
            "Use estes dados para CALIBRAR as entidades e atributos da ontologia.",
            "",
        ]
        for i, r in enumerate(results, 1):
            if r.get("resposta") and "Erro" not in r["resposta"]:
                parts.append(f"### Dado {i}: {r['query'][:60]}")
                parts.append(r["resposta"])
                if r.get("fontes"):
                    parts.append(f"Fontes: {', '.join(r['fontes'][:3])}")
                parts.append("")
        return "\n".join(parts)
    
    def _empty_result(self) -> dict:
        return {
            "dados_mercado": [], "fontes_unicas": [], "contexto_formatado": "",
            "custo_estimado": 0, "queries_executadas": 0, "tempo_segundos": 0,
            "localizacao_detectada": "", "setor_detalhe": "",
        }


# ============================================================
# SEÇÃO DO RELATÓRIO: Contexto de Mercado
# ============================================================

def build_market_context_section(research_data: dict) -> dict:
    """Monta seção 'Contexto de Mercado' para o AugurReportSchema."""
    if not research_data or not research_data.get("dados_mercado"):
        return {}
    
    dados = research_data["dados_mercado"]
    dados_validos = [d for d in dados if d.get("resposta") and "Erro" not in d["resposta"] and len(d["resposta"]) > 20]
    
    if not dados_validos:
        return {}
    
    return {
        "localizacao": research_data.get("localizacao_detectada", ""),
        "setor_detalhe": research_data.get("setor_detalhe", ""),
        "dados": [
            {
                "titulo": d["query"][:80],
                "conteudo": d["resposta"],
                "fontes": d.get("fontes", [])[:3],
            }
            for d in dados_validos
        ],
        "fontes_unicas": research_data.get("fontes_unicas", [])[:15],
        "total_queries": research_data.get("queries_executadas", 0),
        "disclaimer": (
            f"Dados obtidos de fontes públicas via Perplexity AI em "
            f"{research_data.get('tempo_segundos', 0)}s. "
            "Verifique informações críticas antes de tomar decisões."
        ),
    }
