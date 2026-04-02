# BettaFish 國際平台擴充研究報告

> 研究日期：2026-04-02
> 目標：調研如何將 BettaFish (微輿) 的 MindSpider 爬蟲系統擴充至國際社群平台

---

## 目錄

1. [現有架構分析](#1-現有架構分析)
2. [各國際平台推薦工具](#2-各國際平台推薦工具)
3. [統一整合方案](#3-統一整合方案)
4. [擴充實作步驟](#4-擴充實作步驟)
5. [優先順序建議](#5-優先順序建議)
6. [費用與風險](#6-費用與風險)
7. [MiroFish 協同使用](#7-mirofish-協同使用)

---

## 1. 現有架構分析

### 1.1 MindSpider 兩階段流水線

```
Stage 1: BroadTopicExtraction（熱門話題抓取）
  → 從 13+ 新聞源抓取熱門新聞
  → LLM (DeepSeek) 提取關鍵詞和話題摘要
  → 存入 daily_news / daily_topics 表

Stage 2: DeepSentimentCrawling（深度爬取）
  → KeywordManager 從 DB 讀取關鍵詞
  → PlatformCrawler 派發到 MediaCrawler 子模組（子進程方式）
  → 爬取結果存入各平台專屬表（xhs_note, weibo_note 等）
  → InsightEngine 讀取做情感分析（已支援 22 種語言）
```

### 1.2 目前支援的平台（僅中國）

| 平台代碼 | 平台名稱 | 資料表 |
|---------|---------|--------|
| `xhs` | 小紅書 | `xhs_note` |
| `dy` | 抖音 | `douyin_aweme` |
| `ks` | 快手 | `kuaishou_video` |
| `bili` | Bilibili | `bilibili_video` |
| `wb` | 微博 | `weibo_note` |
| `tieba` | 百度貼吧 | `tieba_note` |
| `zhihu` | 知乎 | `zhihu_content` |

### 1.3 平台派發機制

`MindSpider/main.py` 中的平台別名映射：

```python
PLATFORM_CHOICES = ['xhs', 'dy', 'ks', 'bili', 'wb', 'tieba', 'zhihu']

PLATFORM_ALIASES = {
    'weibo': 'wb', '微博': 'wb',
    'douyin': 'dy', '抖音': 'dy',
    'kuaishou': 'ks', '快手': 'ks',
    'bilibili': 'bili', 'b站': 'bili',
    'xiaohongshu': 'xhs', '小红书': 'xhs',
    'zhihu': 'zhihu', '知乎': 'zhihu',
    'tieba': 'tieba', '贴吧': 'tieba',
}
```

### 1.4 擴充切入點

新增國際平台需要修改的位置：

1. **`MindSpider/main.py`** — 加入新平台代碼和別名
2. **`MindSpider/DeepSentimentCrawling/platform_crawler.py`** — 加入新平台爬蟲調用邏輯
3. **`MindSpider/schema/mindspider_tables.sql`** — 建立平台專屬資料表
4. **情感分析 — 不需修改**（`tabularisai/multilingual-sentiment-analysis` 已支援 22 種語言）

---

## 2. 各國際平台推薦工具

### 2.1 Twitter / X

| 專案 | Stars | 語言 | 說明 | 認證需求 |
|------|-------|------|------|---------|
| **[twikit](https://github.com/d60/twikit)** | ~4,220 | Python | **推薦首選**。使用 Twitter 內部 API，積極維護中（2026 持續更新）。支援搜尋推文、用戶資料、趨勢話題、媒體下載 | 帳號密碼（不需 API Key） |
| [twscrape](https://github.com/vladkens/twscrape) | ~2,320 | Python | Async，支援多帳號輪換池，適合大量爬取 | 帳號密碼 |
| [Scweet](https://github.com/Altimis/Scweet) | ~1,291 | Python | 基於 GraphQL，多帳號池 + 代理支援 | 帳號密碼 |
| [tweety](https://github.com/mahrtayyab/tweety) | ~646 | Python | 輕量級，持續更新 | 帳號密碼 |
| [snscrape](https://github.com/JustAnotherArchivist/snscrape) | ~5,322 | Python | 多平台（Twitter/FB/IG/Reddit），但維護停滯，Twitter 模組已不可靠 | 無 |

**官方 API 狀態**：X API v2 極貴（Basic $100/月，Pro $5,000/月），免費版只能發文不能讀取，不實用。

### 2.2 Reddit

| 專案 | Stars | 語言 | 說明 | 認證需求 |
|------|-------|------|------|---------|
| **[PRAW](https://github.com/praw-dev/praw)** | ~4,075 | Python | **推薦首選**。官方 Python 包裝，最穩定可靠。`pip install praw` | API Key（免費申請） |
| [asyncpraw](https://github.com/praw-dev/asyncpraw) | ~145 | Python | PRAW 的 async 版本 | API Key（免費申請） |
| [URS](https://github.com/JosephLai241/URS) | ~981 | Python | CLI 工具，底層用 PRAW，輸出 JSON/CSV | API Key（免費申請） |
| Reddit `.json` 端點 | - | HTTP | 任何 Reddit URL 加 `.json` 即可取得數據 | 無（但有速率限制） |

**官方 API 狀態**：**所有平台中最友好**，免費額度足夠中等規模使用（100 requests/min）。

### 2.3 Instagram

| 專案 | Stars | 語言 | 說明 | 認證需求 |
|------|-------|------|------|---------|
| **[Instaloader](https://github.com/instaloader/instaloader)** | ~12,053 | Python | **推薦首選**。最成熟穩定，`pip install instaloader`。下載照片、影片、Stories、留言、metadata | 公開頁面免登入 |
| [Instagrapi](https://github.com/subzeroid/instagrapi) | ~6,050 | Python | 功能最全（私訊、Stories、Reels 都支援），使用 Instagram 私有 API | 帳號密碼 |

**官方 API 狀態**：Instagram Graph API 僅限商業/創作者帳號查詢自己的內容，無法抓取第三方數據。

**警告**：Instagram 在 2026 年反爬非常激進（強制登入牆、IP 封鎖），需搭配住宅代理 IP 使用。

### 2.4 Facebook

| 專案 | Stars | 語言 | 說明 | 認證需求 |
|------|-------|------|------|---------|
| **[facebook-scraper](https://github.com/kevinzg/facebook-scraper)** | ~3,100 | Python | **推薦首選**。抓公開粉專貼文/留言/按讚，`pip install facebook-scraper` | 無 |
| [fbcrawl](https://github.com/rugantio/fbcrawl) | ~685 | Python | 基於 Scrapy，輸出 CSV/JSON | 無 |
| [facebook_page_scraper](https://github.com/shaikhsajid1111/facebook_page_scraper) | ~262 | Python | 使用 Selenium，輸出 JSON/CSV | 無 |

**官方 API 狀態**：劍橋分析事件後嚴格限制，需要商業驗證，第三方幾乎不可用。

### 2.5 YouTube

| 專案 | Stars | 語言 | 說明 | 認證需求 |
|------|-------|------|------|---------|
| **[YouTube Data API v3](https://developers.google.com/youtube/v3)** | 官方 | REST | **推薦首選**。免費 10,000 單位/天，穩定可靠 | API Key（免費） |
| [youtube-comment-downloader](https://github.com/egbertbouman/youtube-comment-downloader) | ~1,206 | Python | 輕量級，不需 API Key，輸出 JSON | 無 |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | 100k+ | Python | 加 `--write-comments` 可抓留言，加影片 metadata | 無 |

**官方 API 狀態**：**所有平台中官方 API 最實用**，建議直接用官方。

### 2.6 TikTok（國際版）

| 專案 | Stars | 語言 | 說明 | 認證需求 |
|------|-------|------|------|---------|
| **[TikTok-Api](https://github.com/davidteather/TikTok-Api)** | ~6,100 | Python | **推薦首選**。最受歡迎的 TikTok 爬蟲，`pip install TikTokApi` | 無（用 Playwright） |
| [Douyin_TikTok_Download_API](https://github.com/Evil0ctal/Douyin_TikTok_Download_API) | ~16,919 | Python | 同時支援抖音 + 國際版 TikTok，有 FastAPI 介面 | 無 |
| [TikTokLive](https://github.com/isaackogan/TikTokLive) | ~1,380 | Python | 專門抓 TikTok 直播的即時留言/禮物/事件 | 無 |

**官方 API 狀態**：TikTok Research API 需學術機構身份申請，一般用戶難以取得。

### 2.7 多平台統一工具（參考）

| 專案 | Stars | 支援平台 | 說明 |
|------|-------|---------|------|
| [snscrape](https://github.com/JustAnotherArchivist/snscrape) | ~5,322 | Twitter/FB/IG/Reddit/Telegram/VK | 維護停滯，Twitter 模組已壞 |
| [socialreaper](https://github.com/ScriptSmith/socialreaper) | ~641 | FB/Twitter/Reddit/YouTube/Pinterest | 使用官方 API，架構值得參考 |
| [social-media-scraper](https://github.com/julian-chan/social-media-scraper) | - | FB/IG/Weibo/Twitter/LinkedIn | 含 NLP 情感分析，與 BettaFish 最相關 |

---

## 3. 統一整合方案

### 3.1 架構設計

```
BettaFish MindSpider 擴充架構
│
├── 現有 MediaCrawler（中國平台）
│   ├── xhs, dy, ks, bili, wb, tieba, zhihu
│
├── 新增 InternationalCrawler/（國際平台）
│   ├── __init__.py
│   ├── base_crawler.py        # 統一抽象基類
│   ├── twitter_crawler.py     # → twikit
│   ├── reddit_crawler.py      # → PRAW
│   ├── instagram_crawler.py   # → instaloader
│   ├── facebook_crawler.py    # → facebook-scraper
│   ├── youtube_crawler.py     # → YouTube API v3
│   └── tiktok_crawler.py      # → TikTok-Api
│
├── 統一數據模型（Normalized Schema）
│   所有平台輸出統一格式，存入對應資料表
│
└── 下游分析引擎（不需修改）
    ├── InsightEngine（情感分析已支援 22 語言）
    ├── QueryEngine
    ├── ReportEngine
    └── ForumEngine
```

### 3.2 統一數據模型

所有國際平台的爬取結果應統一為以下格式，再存入各自的資料表：

```python
{
    "platform": str,          # "twitter", "reddit", "instagram", etc.
    "post_id": str,           # 平台原始貼文 ID
    "author": str,            # 作者名稱
    "author_id": str,         # 作者 ID
    "content": str,           # 文本內容（情感分析主要讀取此欄位）
    "title": str,             # 標題（Reddit/YouTube 有，Twitter/IG 無）
    "timestamp": datetime,    # 發布時間
    "url": str,               # 原始連結
    "engagement": {
        "likes": int,
        "shares": int,        # 轉推/轉發
        "comments_count": int,
        "views": int
    },
    "media_urls": list,       # 圖片/影片連結
    "comments": [             # 留言列表
        {
            "comment_id": str,
            "author": str,
            "content": str,
            "timestamp": datetime,
            "likes": int
        }
    ],
    "topic_id": int,          # 關聯 MindSpider 話題
    "crawling_task_id": int   # 關聯爬取任務
}
```

### 3.3 資料表設計範例（以 Twitter 為例）

```sql
CREATE TABLE twitter_post (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    post_id         VARCHAR(64) NOT NULL UNIQUE,
    author          VARCHAR(255),
    author_id       VARCHAR(64),
    content         TEXT,
    timestamp       DATETIME,
    url             VARCHAR(512),
    likes           INT DEFAULT 0,
    retweets        INT DEFAULT 0,
    replies         INT DEFAULT 0,
    views           INT DEFAULT 0,
    media_urls      JSON,
    topic_id        INT,
    crawling_task_id INT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_topic (topic_id),
    INDEX idx_timestamp (timestamp)
);

-- 留言表
CREATE TABLE twitter_comment (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    comment_id      VARCHAR(64) NOT NULL UNIQUE,
    post_id         VARCHAR(64),
    author          VARCHAR(255),
    content         TEXT,
    timestamp       DATETIME,
    likes           INT DEFAULT 0,
    topic_id        INT,
    FOREIGN KEY (post_id) REFERENCES twitter_post(post_id)
);
```

其他平台（reddit_post, instagram_post, youtube_comment 等）類比設計。

---

## 4. 擴充實作步驟

### Step 1：安裝依賴

```bash
pip install twikit praw instaloader facebook-scraper TikTokApi
pip install google-api-python-client  # YouTube API
pip install playwright && playwright install chromium  # TikTok 需要
```

### Step 2：建立抽象基類

```python
# MindSpider/InternationalCrawler/base_crawler.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseInternationalCrawler(ABC):
    """國際平台爬蟲統一介面"""

    @abstractmethod
    def search_by_keywords(self, keywords: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """根據關鍵詞搜尋貼文"""
        pass

    @abstractmethod
    def get_comments(self, post_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """取得某貼文的留言"""
        pass

    @abstractmethod
    def normalize(self, raw_data: Any) -> Dict[str, Any]:
        """將平台原始數據轉換為統一格式"""
        pass
```

### Step 3：實作各平台爬蟲（範例：Twitter）

```python
# MindSpider/InternationalCrawler/twitter_crawler.py
import twikit
from .base_crawler import BaseInternationalCrawler

class TwitterCrawler(BaseInternationalCrawler):
    def __init__(self, username, password):
        self.client = twikit.Client()
        self.client.login(auth_info_1=username, password=password)

    def search_by_keywords(self, keywords, limit=50):
        query = " OR ".join(keywords)
        tweets = self.client.search_tweet(query, product='Latest', count=limit)
        return [self.normalize(t) for t in tweets]

    def get_comments(self, post_id, limit=100):
        # twikit 支援取得回覆
        ...

    def normalize(self, tweet):
        return {
            "platform": "twitter",
            "post_id": tweet.id,
            "author": tweet.user.name,
            "content": tweet.text,
            "timestamp": tweet.created_at,
            "engagement": {
                "likes": tweet.favorite_count,
                "shares": tweet.retweet_count,
                "comments_count": tweet.reply_count,
                "views": tweet.view_count
            }
        }
```

### Step 4：註冊新平台到 MindSpider

在 `MindSpider/main.py` 中新增：

```python
# 擴充平台列表
PLATFORM_CHOICES = ['xhs', 'dy', 'ks', 'bili', 'wb', 'tieba', 'zhihu',
                    'tw', 'reddit', 'ig', 'fb', 'yt', 'tiktok']

# 擴充別名映射
PLATFORM_ALIASES.update({
    'twitter': 'tw', 'x': 'tw', 'x.com': 'tw',
    'reddit': 'reddit',
    'instagram': 'ig',
    'facebook': 'fb',
    'youtube': 'yt',
    'tiktok': 'tiktok',
})
```

### Step 5：修改 PlatformCrawler 派發邏輯

在 `platform_crawler.py` 中區分中國/國際平台：

```python
CHINESE_PLATFORMS = {'xhs', 'dy', 'ks', 'bili', 'wb', 'tieba', 'zhihu'}
INTERNATIONAL_PLATFORMS = {'tw', 'reddit', 'ig', 'fb', 'yt', 'tiktok'}

def run_crawler(self, platform, keywords):
    if platform in CHINESE_PLATFORMS:
        # 現有 MediaCrawler 子進程邏輯
        self._run_mediacrawler(platform, keywords)
    elif platform in INTERNATIONAL_PLATFORMS:
        # 新增國際爬蟲邏輯
        crawler = self._get_international_crawler(platform)
        results = crawler.search_by_keywords(keywords)
        self._save_to_db(platform, results)
```

---

## 5. 優先順序建議

根據穩定性、實用性和實作難度排序：

| 優先級 | 平台 | 理由 | 預估工時 |
|--------|------|------|---------|
| 1 | **Reddit** | 官方 API 免費好用，數據品質高，討論型內容最適合輿情分析 | 1-2 天 |
| 2 | **YouTube** | 官方 API 免費穩定，留言量大，覆蓋面廣 | 1-2 天 |
| 3 | **Twitter/X** | 輿情核心平台，twikit 積極維護，但需帳號且有封號風險 | 2-3 天 |
| 4 | **TikTok** | 年輕群體輿情重要來源，需 Playwright 環境 | 2-3 天 |
| 5 | **Instagram** | 反爬最嚴格，需代理 IP，維護成本高 | 3-5 天 |
| 6 | **Facebook** | API 限制最多，用戶流失中，ROI 最低 | 3-5 天 |

---

## 6. 費用與風險

### 6.1 費用

| 項目 | 費用 |
|------|------|
| Reddit API | 免費（中等規模） |
| YouTube Data API v3 | 免費（10,000 單位/天） |
| Twitter/X 官方 API | $100~$5,000/月（不建議，用 twikit 替代） |
| 所有非官方爬蟲工具 | 免費開源 |
| 住宅代理 IP（IG/FB 需要） | ~$5-15/GB |

### 6.2 風險矩陣

| 風險 | 嚴重程度 | 受影響平台 | 緩解措施 |
|------|---------|-----------|---------|
| 爬蟲工具失效（平台更新反爬） | 高 | IG > FB > Twitter > TikTok | 每個平台準備備選工具 |
| 帳號被封禁 | 中 | Twitter, Instagram | 使用一次性帳號，多帳號輪換 |
| IP 被封鎖 | 中 | Instagram, Facebook | 使用住宅代理 IP 池 |
| 違反平台 ToS | 低 | 所有平台 | 僅用於研究/個人用途 |
| API 收費策略變動 | 低 | Reddit, YouTube | 控制使用量，關注官方公告 |

### 6.3 各平台失效頻率預估

```
穩定 ←────────────────────────────→ 不穩定
YouTube API  >  Reddit API  >  TikTok  >  Twitter  >  Facebook  >  Instagram
（官方 API）    （官方 API）   （Playwright）（內部 API）  （HTML 解析）  （反爬最強）
```

---

## 7. MiroFish 協同使用

### 7.1 BettaFish + MiroFish 工作流

```
┌──────────────────────────────────────────────────┐
│              完整輿情工作流                         │
│                                                    │
│  ① BettaFish 監控（已發生的事）                     │
│     MindSpider 爬取真實社群數據                     │
│     → InsightEngine 情感分析                        │
│     → ReportEngine 產出輿情報告 (PDF)               │
│              │                                     │
│              ▼                                     │
│  ② MiroFish 預測（可能發生的事）                    │
│     上傳 BettaFish 報告                            │
│     → 建構知識圖譜                                  │
│     → 生成模擬 Agent                                │
│     → 多 Agent 社群模擬                             │
│     → 產出預測報告 + 與 Agent 對話                   │
│              │                                     │
│              ▼                                     │
│  ③ 驗證與迭代                                      │
│     BettaFish 持續監控 → 驗證 MiroFish 預測          │
└──────────────────────────────────────────────────┘
```

### 7.2 應用場景

| 場景 | BettaFish | MiroFish |
|------|-----------|----------|
| 品牌危機公關 | 監控當前負面輿論 | 模擬不同公關策略效果 |
| 政策發布 | 爬取民眾即時反應 | 預測後續輿論發酵方向 |
| 產品上市 | 收集用戶真實評價 | 模擬競品反擊後的市場反應 |
| 國際輿情 | 爬取 Twitter/Reddit 真實討論 | 模擬國際社群傳播路徑 |

---

## 參考連結

### 爬蟲工具

- twikit: https://github.com/d60/twikit
- twscrape: https://github.com/vladkens/twscrape
- PRAW: https://github.com/praw-dev/praw
- Instaloader: https://github.com/instaloader/instaloader
- Instagrapi: https://github.com/subzeroid/instagrapi
- facebook-scraper: https://github.com/kevinzg/facebook-scraper
- youtube-comment-downloader: https://github.com/egbertbouman/youtube-comment-downloader
- TikTok-Api: https://github.com/davidteather/TikTok-Api
- Douyin_TikTok_Download_API: https://github.com/Evil0ctal/Douyin_TikTok_Download_API
- snscrape: https://github.com/JustAnotherArchivist/snscrape
- yt-dlp: https://github.com/yt-dlp/yt-dlp

### 官方 API

- YouTube Data API v3: https://developers.google.com/youtube/v3
- Reddit API: https://www.reddit.com/dev/api
- X/Twitter API v2: https://developer.x.com/en/docs/x-api

### 相關專案

- BettaFish (微輿): https://github.com/virus11456/BettaFish
- MiroFish: https://github.com/666ghj/MiroFish
- MediaCrawler: https://github.com/NanmiCoder/MediaCrawler
