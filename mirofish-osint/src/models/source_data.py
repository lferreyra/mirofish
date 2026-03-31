from pydantic import BaseModel


class WebSearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    date: str = ""
    relevance_score: float = 0.0


class ArticleData(BaseModel):
    title: str
    url: str
    full_text: str
    date: str = ""
    source_name: str = ""


class GdeltEvent(BaseModel):
    title: str
    url: str
    tone: float = 0.0
    date: str = ""
    source_country: str = ""


class NewsHeadline(BaseModel):
    title: str
    url: str
    source: str = ""
    date: str = ""
    category: str = ""


class GoogleTrendsData(BaseModel):
    interest_over_time: dict = {}
    related_queries: list[str] = []
    geographic: dict = {}


class RedditPost(BaseModel):
    title: str
    subreddit: str = ""
    score: int = 0
    num_comments: int = 0
    date: str = ""
    url: str = ""


class WikipediaData(BaseModel):
    summary: str
    key_entities: list[str] = []
    url: str = ""


class GeminiGroundingData(BaseModel):
    text: str
    citations: list[dict] = []
    search_queries: list[str] = []


class GeminiDeepResearchData(BaseModel):
    report: str
    status: str = "completed"


class CollectedSources(BaseModel):
    web_search: list[WebSearchResult] = []
    articles: list[ArticleData] = []
    gdelt_events: list[GdeltEvent] = []
    news_headlines: list[NewsHeadline] = []
    google_trends: GoogleTrendsData | None = None
    reddit_posts: list[RedditPost] = []
    wikipedia: WikipediaData | None = None
    gemini_grounding: GeminiGroundingData | None = None
    gemini_deep_research: GeminiDeepResearchData | None = None


class SourceStatus(BaseModel):
    name: str
    status: str  # "active" | "degraded" | "down"
    description: str
