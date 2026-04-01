"""
외부 데이터 통합 서비스
웹 검색, 뉴스, 시장 데이터, 소셜 트렌드를 수집합니다.

각 데이터 소스는 fallback chain으로 구성:
- 웹 검색: Brave → Tavily → SerpAPI
- 뉴스: NewsAPI → Google News RSS
- 시장: Alpha Vantage → Yahoo Finance
- 소셜: Reddit API

전부 실패해도 빈 결과 반환 (시뮬레이션은 계속 돌아감).
"""

import os
import time
import json
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import requests

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.external_data')


# ── 데이터 클래스 ──

@dataclass
class WebResult:
    """웹 검색 결과"""
    title: str
    url: str
    snippet: str
    published_at: Optional[str] = None

    def to_text(self) -> str:
        date_str = f" ({self.published_at})" if self.published_at else ""
        return f"[{self.title}]{date_str}\n{self.snippet}\nSource: {self.url}"


@dataclass
class NewsItem:
    """뉴스 검색 결과"""
    title: str
    source: str
    url: str
    summary: str
    published_at: str

    def to_text(self) -> str:
        return f"[{self.source}] {self.title} ({self.published_at})\n{self.summary}"


@dataclass
class MarketData:
    """시장 데이터"""
    symbol: str
    price: Optional[float] = None
    change_percent: Optional[float] = None
    volume: Optional[int] = None
    market_cap: Optional[float] = None
    timestamp: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_text(self) -> str:
        parts = [f"{self.symbol}"]
        if self.price is not None:
            parts.append(f"Price: ${self.price:,.2f}")
        if self.change_percent is not None:
            sign = "+" if self.change_percent >= 0 else ""
            parts.append(f"Change: {sign}{self.change_percent:.2f}%")
        if self.volume is not None:
            parts.append(f"Volume: {self.volume:,}")
        if self.timestamp:
            parts.append(f"As of: {self.timestamp}")
        return " | ".join(parts)


@dataclass
class TrendItem:
    """소셜 트렌드"""
    topic: str
    platform: str
    score: float
    summary: str
    post_count: Optional[int] = None

    def to_text(self) -> str:
        count_str = f" ({self.post_count} posts)" if self.post_count else ""
        return f"[{self.platform}] {self.topic}{count_str} (score: {self.score:.1f})\n{self.summary}"


@dataclass
class ExternalDataBatch:
    """외부 데이터 일괄 결과"""
    web_results: List[WebResult] = field(default_factory=list)
    news_items: List[NewsItem] = field(default_factory=list)
    market_data: List[MarketData] = field(default_factory=list)
    trends: List[TrendItem] = field(default_factory=list)
    fetched_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_text(self) -> str:
        """전체 결과를 텍스트로 변환 (그래프 주입용)."""
        sections = []
        if self.web_results:
            sections.append(f"[실시간 웹 데이터 - {self.fetched_at}]")
            for r in self.web_results:
                sections.append(r.to_text())

        if self.news_items:
            sections.append(f"\n[실시간 뉴스 - {self.fetched_at}]")
            for n in self.news_items:
                sections.append(n.to_text())

        if self.market_data:
            sections.append(f"\n[시장 데이터 - {self.fetched_at}]")
            for m in self.market_data:
                sections.append(m.to_text())

        if self.trends:
            sections.append(f"\n[소셜 트렌드 - {self.fetched_at}]")
            for t in self.trends:
                sections.append(t.to_text())

        return "\n".join(sections)

    @property
    def is_empty(self) -> bool:
        return not (self.web_results or self.news_items or self.market_data or self.trends)


# ── Provider 추상 클래스 ──

class BaseProvider(ABC):
    """외부 데이터 provider 추상 클래스"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._available = api_key is not None and api_key != ""

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    @abstractmethod
    def name(self) -> str:
        pass


# ── 웹 검색 Providers ──

class BraveSearchProvider(BaseProvider):
    name = "brave"
    API_URL = "https://api.search.brave.com/res/v1/web/search"

    def search(self, query: str, limit: int = 10) -> List[WebResult]:
        if not self.is_available:
            return []
        try:
            resp = requests.get(
                self.API_URL,
                headers={"X-Subscription-Token": self.api_key, "Accept": "application/json"},
                params={"q": query, "count": limit},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("web", {}).get("results", [])[:limit]:
                results.append(WebResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    published_at=item.get("age"),
                ))
            return results
        except Exception as e:
            logger.warning(f"Brave Search 실패: {e}")
            return []


class TavilySearchProvider(BaseProvider):
    name = "tavily"
    API_URL = "https://api.tavily.com/search"

    def search(self, query: str, limit: int = 10) -> List[WebResult]:
        if not self.is_available:
            return []
        try:
            resp = requests.post(
                self.API_URL,
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": limit,
                    "include_answer": False,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("results", [])[:limit]:
                results.append(WebResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    published_at=item.get("published_date"),
                ))
            return results
        except Exception as e:
            logger.warning(f"Tavily Search 실패: {e}")
            return []


class SerpApiProvider(BaseProvider):
    name = "serpapi"
    API_URL = "https://serpapi.com/search"

    def search(self, query: str, limit: int = 10) -> List[WebResult]:
        if not self.is_available:
            return []
        try:
            resp = requests.get(
                self.API_URL,
                params={"q": query, "api_key": self.api_key, "engine": "google", "num": limit},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("organic_results", [])[:limit]:
                results.append(WebResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    published_at=item.get("date"),
                ))
            return results
        except Exception as e:
            logger.warning(f"SerpAPI 실패: {e}")
            return []


# ── 뉴스 Providers ──

class NewsApiProvider(BaseProvider):
    name = "newsapi"
    API_URL = "https://newsapi.org/v2/everything"

    def search(self, topic: str, hours: int = 24, limit: int = 20) -> List[NewsItem]:
        if not self.is_available:
            return []
        try:
            from_date = (datetime.utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
            resp = requests.get(
                self.API_URL,
                params={
                    "q": topic,
                    "from": from_date,
                    "sortBy": "publishedAt",
                    "pageSize": limit,
                    "apiKey": self.api_key,
                    "language": "en",
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for article in data.get("articles", [])[:limit]:
                results.append(NewsItem(
                    title=article.get("title", ""),
                    source=article.get("source", {}).get("name", "Unknown"),
                    url=article.get("url", ""),
                    summary=article.get("description", "") or "",
                    published_at=article.get("publishedAt", ""),
                ))
            return results
        except Exception as e:
            logger.warning(f"NewsAPI 실패: {e}")
            return []


class GoogleNewsRssProvider(BaseProvider):
    """Google News RSS — API 키 불필요"""
    name = "google_news_rss"
    RSS_URL = "https://news.google.com/rss/search"

    def __init__(self):
        super().__init__(api_key="no_key_needed")

    def search(self, topic: str, hours: int = 24, limit: int = 20) -> List[NewsItem]:
        try:
            import xml.etree.ElementTree as ET
            resp = requests.get(
                self.RSS_URL,
                params={"q": topic, "hl": "en-US", "gl": "US", "ceid": "US:en"},
                timeout=15,
            )
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            results = []
            for item in root.findall('.//item')[:limit]:
                title = item.findtext('title', '')
                source = ""
                if ' - ' in title:
                    title, source = title.rsplit(' - ', 1)
                results.append(NewsItem(
                    title=title,
                    source=source,
                    url=item.findtext('link', ''),
                    summary=_strip_html(item.findtext('description', '')),
                    published_at=item.findtext('pubDate', ''),
                ))
            return results
        except Exception as e:
            logger.warning(f"Google News RSS 실패: {e}")
            return []


# ── 시장 데이터 Providers ──

class AlphaVantageProvider(BaseProvider):
    name = "alpha_vantage"
    API_URL = "https://www.alphavantage.co/query"

    def get_quote(self, symbol: str) -> Optional[MarketData]:
        if not self.is_available:
            return None
        try:
            # 암호화폐인지 주식인지 판별
            crypto_symbols = {"BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "DOT", "AVAX"}
            is_crypto = symbol.upper() in crypto_symbols

            if is_crypto:
                params = {
                    "function": "CURRENCY_EXCHANGE_RATE",
                    "from_currency": symbol.upper(),
                    "to_currency": "USD",
                    "apikey": self.api_key,
                }
                resp = requests.get(self.API_URL, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                rate_data = data.get("Realtime Currency Exchange Rate", {})
                if not rate_data:
                    return None
                return MarketData(
                    symbol=symbol.upper(),
                    price=float(rate_data.get("5. Exchange Rate", 0)),
                    timestamp=rate_data.get("6. Last Refreshed", ""),
                )
            else:
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol.upper(),
                    "apikey": self.api_key,
                }
                resp = requests.get(self.API_URL, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                quote = data.get("Global Quote", {})
                if not quote:
                    return None
                return MarketData(
                    symbol=symbol.upper(),
                    price=float(quote.get("05. price", 0)),
                    change_percent=float(quote.get("10. change percent", "0%").rstrip('%')),
                    volume=int(quote.get("06. volume", 0)),
                    timestamp=quote.get("07. latest trading day", ""),
                )
        except Exception as e:
            logger.warning(f"Alpha Vantage 실패 ({symbol}): {e}")
            return None


class YahooFinanceProvider(BaseProvider):
    """Yahoo Finance 스크래핑 — API 키 불필요"""
    name = "yahoo_finance"
    API_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

    def __init__(self):
        super().__init__(api_key="no_key_needed")

    def get_quote(self, symbol: str) -> Optional[MarketData]:
        try:
            # 암호화폐 심볼 변환
            crypto_map = {"BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD",
                          "XRP": "XRP-USD", "ADA": "ADA-USD", "DOGE": "DOGE-USD"}
            yf_symbol = crypto_map.get(symbol.upper(), symbol.upper())

            resp = requests.get(
                f"{self.API_URL}/{yf_symbol}",
                params={"interval": "1d", "range": "1d"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            result = data.get("chart", {}).get("result", [{}])[0]
            meta = result.get("meta", {})
            if not meta:
                return None

            price = meta.get("regularMarketPrice", 0)
            prev_close = meta.get("previousClose") or meta.get("chartPreviousClose", 0)
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0

            return MarketData(
                symbol=symbol.upper(),
                price=float(price),
                change_percent=round(change_pct, 2),
                volume=meta.get("regularMarketVolume"),
                timestamp=datetime.utcnow().isoformat(),
            )
        except Exception as e:
            logger.warning(f"Yahoo Finance 실패 ({symbol}): {e}")
            return None


# ── 소셜 트렌드 ──

class RedditTrendsProvider(BaseProvider):
    """Reddit 트렌드 — API 키 불필요"""
    name = "reddit"
    API_URL = "https://www.reddit.com/search.json"

    def __init__(self):
        super().__init__(api_key="no_key_needed")

    def search(self, topic: str, limit: int = 20) -> List[TrendItem]:
        try:
            resp = requests.get(
                self.API_URL,
                params={"q": topic, "sort": "relevance", "t": "day", "limit": limit},
                headers={"User-Agent": "MiroFish/1.0"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for post in data.get("data", {}).get("children", [])[:limit]:
                d = post.get("data", {})
                results.append(TrendItem(
                    topic=d.get("title", ""),
                    platform="reddit",
                    score=float(d.get("score", 0)),
                    summary=d.get("selftext", "")[:300] or d.get("title", ""),
                    post_count=d.get("num_comments", 0),
                ))
            return results
        except Exception as e:
            logger.warning(f"Reddit Trends 실패: {e}")
            return []


# ── 메인 서비스 ──

class ExternalDataService:
    """
    외부 데이터 통합 서비스

    각 데이터 소스는 fallback chain으로 구성.
    하나가 실패하면 자동으로 다음 provider로 전환.
    전부 실패해도 빈 결과 반환 (시뮬레이션 중단 없음).
    """

    def __init__(self):
        # 웹 검색 fallback chain
        self._web_providers = [
            BraveSearchProvider(os.environ.get('BRAVE_SEARCH_API_KEY')),
            TavilySearchProvider(os.environ.get('TAVILY_API_KEY')),
            SerpApiProvider(os.environ.get('SERP_API_KEY')),
        ]

        # 뉴스 fallback chain
        self._news_providers = [
            NewsApiProvider(os.environ.get('NEWS_API_KEY')),
            GoogleNewsRssProvider(),
        ]

        # 시장 데이터 fallback chain
        self._market_providers = [
            AlphaVantageProvider(os.environ.get('ALPHA_VANTAGE_API_KEY')),
            YahooFinanceProvider(),
        ]

        # 소셜 트렌드
        self._social_providers = [
            RedditTrendsProvider(),
        ]

        available = []
        for providers in [self._web_providers, self._news_providers,
                          self._market_providers, self._social_providers]:
            for p in providers:
                if p.is_available:
                    available.append(p.name)
        logger.info(f"외부 데이터 서비스 초기화: {len(available)}개 provider 활성 ({', '.join(available)})")

    def web_search(self, query: str, limit: int = 10) -> List[WebResult]:
        """웹 검색 (fallback chain)."""
        for provider in self._web_providers:
            if not provider.is_available:
                continue
            results = provider.search(query, limit)
            if results:
                logger.info(f"웹 검색 성공 (provider={provider.name}, query={query[:50]}, results={len(results)})")
                return results
        logger.warning(f"웹 검색 실패 (모든 provider 실패): {query[:50]}")
        return []

    def news_search(self, topic: str, hours: int = 24, limit: int = 20) -> List[NewsItem]:
        """뉴스 검색 (fallback chain)."""
        for provider in self._news_providers:
            if not provider.is_available:
                continue
            results = provider.search(topic, hours, limit)
            if results:
                logger.info(f"뉴스 검색 성공 (provider={provider.name}, topic={topic[:50]}, results={len(results)})")
                return results
        logger.warning(f"뉴스 검색 실패: {topic[:50]}")
        return []

    def market_data(self, symbol: str) -> Optional[MarketData]:
        """시장 데이터 (fallback chain)."""
        for provider in self._market_providers:
            if not provider.is_available:
                continue
            result = provider.get_quote(symbol)
            if result:
                logger.info(f"시장 데이터 성공 (provider={provider.name}, symbol={symbol})")
                return result
        logger.warning(f"시장 데이터 실패: {symbol}")
        return None

    def social_trends(self, topic: str, limit: int = 20) -> List[TrendItem]:
        """소셜 트렌드."""
        for provider in self._social_providers:
            if not provider.is_available:
                continue
            results = provider.search(topic, limit)
            if results:
                logger.info(f"소셜 트렌드 성공 (provider={provider.name}, results={len(results)})")
                return results
        logger.warning(f"소셜 트렌드 실패: {topic[:50]}")
        return []

    def fetch_all(self, topic: str, symbols: Optional[List[str]] = None) -> ExternalDataBatch:
        """
        주제에 대한 모든 외부 데이터를 한 번에 수집합니다.
        그래프 빌드 시 사용.
        """
        batch = ExternalDataBatch()
        batch.web_results = self.web_search(topic, limit=10)
        batch.news_items = self.news_search(topic, hours=72, limit=15)

        if symbols:
            for sym in symbols:
                data = self.market_data(sym)
                if data:
                    batch.market_data.append(data)

        batch.trends = self.social_trends(topic, limit=10)

        if batch.is_empty:
            logger.warning(f"외부 데이터 전체 수집 실패: {topic}")
        else:
            total = len(batch.web_results) + len(batch.news_items) + len(batch.market_data) + len(batch.trends)
            logger.info(f"외부 데이터 수집 완료: {total}건 (topic={topic[:50]})")

        return batch


# ── 유틸리티 ──

def _strip_html(text: str) -> str:
    """HTML 태그를 제거합니다."""
    return re.sub(r'<[^>]+>', '', text).strip()


# ── 글로벌 인스턴스 ──

_external_data_service: Optional[ExternalDataService] = None


def get_external_data_service() -> ExternalDataService:
    """글로벌 ExternalDataService 인스턴스를 반환합니다."""
    global _external_data_service
    if _external_data_service is None:
        _external_data_service = ExternalDataService()
    return _external_data_service
