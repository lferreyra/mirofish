import re
from src.models.source_data import CollectedSources
from src.models.research_result import Entity, TimelineEvent


class Normalizer:
    def extract_entities(self, sources: CollectedSources) -> list[Entity]:
        text_chunks = []
        source_map: dict[str, set[str]] = {}

        for item in sources.web_search:
            text_chunks.append((item.title + " " + item.snippet, "serper"))
        for item in sources.gdelt_events:
            text_chunks.append((item.title, "gdelt"))
        for item in sources.news_headlines:
            text_chunks.append((item.title, "news_trends"))
        for item in sources.reddit_posts:
            text_chunks.append((item.title, "reddit"))
        if sources.wikipedia:
            text_chunks.append((sources.wikipedia.summary[:500], "wikipedia"))

        word_counts: dict[str, int] = {}
        for text, source_name in text_chunks:
            words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
            for word in words:
                if len(word) < 3:
                    continue
                word_counts[word] = word_counts.get(word, 0) + 1
                if word not in source_map:
                    source_map[word] = set()
                source_map[word].add(source_name)

        entities = []
        for name, count in sorted(word_counts.items(), key=lambda x: -x[1]):
            if count >= 2:
                entities.append(Entity(
                    name=name, type="unknown", mention_count=count,
                    sources=list(source_map.get(name, [])),
                ))
        return entities[:30]

    def build_timeline(self, sources: CollectedSources) -> list[TimelineEvent]:
        events = []
        for item in sources.gdelt_events:
            if item.date:
                normalized_date = item.date
                if len(normalized_date) == 8:
                    normalized_date = f"{normalized_date[:4]}-{normalized_date[4:6]}-{normalized_date[6:8]}"
                events.append(TimelineEvent(
                    date=normalized_date, event=item.title, source="gdelt",
                    confidence="high" if abs(item.tone) > 2 else "medium",
                ))
        for item in sources.news_headlines:
            if item.date:
                events.append(TimelineEvent(
                    date=item.date, event=item.title, source="news_trends", confidence="medium",
                ))
        events.sort(key=lambda e: e.date)
        return events

    def deduplicate(self, sources: CollectedSources) -> CollectedSources:
        seen_urls = set()
        deduped_web = []
        for item in sources.web_search:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                deduped_web.append(item)
        deduped_gdelt = []
        for item in sources.gdelt_events:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                deduped_gdelt.append(item)
        deduped_news = []
        for item in sources.news_headlines:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                deduped_news.append(item)
        sources.web_search = deduped_web
        sources.gdelt_events = deduped_gdelt
        sources.news_headlines = deduped_news
        return sources
