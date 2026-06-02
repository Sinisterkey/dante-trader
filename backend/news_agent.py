import logging
import feedparser
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from nltk.sentiment import SentimentIntensityAnalyzer
import nltk

logger = logging.getLogger(__name__)

# Download VADER lexicon on first run
try:
    nltk.data.find('sentiment/vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon', quiet=True)


class NewsAgent:
    """News sentiment analysis agent."""

    def __init__(self):
        self.name = "news"
        self.sia = SentimentIntensityAnalyzer()
        self.article_cache = {}
        self.cache_ttl = 3600  # 1 hour

    def analyze(self, symbol: str, hours_lookback: int = 24) -> Dict[str, Any]:
        """Analyze news sentiment for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD', 'AAPL', 'BTC')
            hours_lookback: How many hours back to fetch articles
            
        Returns:
            {
                "sentiment": "bullish | bearish | neutral",
                "score": -1.0 to +1.0,
                "confidence": 0-100,
                "reasons": [...]
            }
        """
        try:
            from config import NEWS_FEED_URLS

            articles = self._fetch_and_cache_articles(NEWS_FEED_URLS, hours_lookback)
            filtered_articles = self._filter_articles_by_symbol(articles, symbol)

            if not filtered_articles:
                logger.info(f"No articles found for {symbol}")
                return {
                    "sentiment": "neutral",
                    "score": 0.0,
                    "confidence": 0,
                    "reasons": ["No recent articles found"],
                    "articles_analyzed": 0,
                    "agent": self.name
                }

            # Analyze sentiment of filtered articles
            sentiments = []
            for article in filtered_articles:
                score = self.sia.polarity_scores(article.get('summary', article.get('title', '')))
                sentiments.append(score["compound"])  # -1 to +1

            # Aggregate sentiment (weighted by recency)
            aggregated_score = self._aggregate_sentiment(filtered_articles, sentiments)
            sentiment_label = self._score_to_sentiment(aggregated_score)
            confidence = abs(aggregated_score) * 100

            reasons = self._generate_reasons(symbol, filtered_articles, aggregated_score)

            return {
                "sentiment": sentiment_label,
                "score": aggregated_score,
                "confidence": min(int(confidence), 100),
                "reasons": reasons,
                "articles_analyzed": len(filtered_articles),
                "agent": self.name
            }

        except Exception as e:
            logger.error(f"Error in NewsAgent.analyze: {e}")
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0,
                "reasons": [f"Analysis error: {str(e)}"],
                "agent": self.name
            }

    def _fetch_and_cache_articles(self, feed_urls: List[str], hours_lookback: int) -> List[Dict]:
        """Fetch articles from RSS feeds with caching."""
        articles = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_lookback)

        for url in feed_urls:
            try:
                # Check cache
                cache_key = url
                if cache_key in self.article_cache:
                    cached_time, cached_articles = self.article_cache[cache_key]
                    if time.time() - cached_time < self.cache_ttl:
                        articles.extend(cached_articles)
                        continue

                # Fetch from feed
                feed = feedparser.parse(url)

                feed_articles = []
                for entry in feed.entries[:20]:  # Limit to 20 most recent
                    try:
                        published_time = entry.get('published_parsed')
                        if published_time:
                            published_dt = datetime(*published_time[:6])
                            if published_dt < cutoff_time:
                                continue

                        article = {
                            "title": entry.get('title', ''),
                            "summary": entry.get('summary', ''),
                            "link": entry.get('link', ''),
                            "published": entry.get('published', '')
                        }
                        feed_articles.append(article)
                    except Exception as e:
                        logger.warning(f"Error parsing feed entry: {e}")
                        continue

                # Cache articles
                self.article_cache[cache_key] = (time.time(), feed_articles)
                articles.extend(feed_articles)

            except Exception as e:
                logger.warning(f"Error fetching feed {url}: {e}")
                continue

        return articles

    def _filter_articles_by_symbol(self, articles: List[Dict], symbol: str) -> List[Dict]:
        """Filter articles relevant to the symbol."""
        filtered = []
        symbol_variations = self._get_symbol_variations(symbol)

        for article in articles:
            content = f"{article.get('title', '')} {article.get('summary', '')}".upper()

            for variation in symbol_variations:
                if variation.upper() in content:
                    filtered.append(article)
                    break

        return filtered

    def _get_symbol_variations(self, symbol: str) -> List[str]:
        """Get variations of the symbol to search for."""
        symbol = symbol.upper()
        variations = [symbol]

        # Add common variations
        if symbol == "EURUSD":
            variations.extend(["EUR", "EURO", "EUR/USD"])
        elif symbol == "GBPUSD":
            variations.extend(["GBP", "POUND", "GBP/USD"])
        elif symbol == "USDJPY":
            variations.extend(["JPY", "YEN", "USD/JPY"])
        elif symbol.startswith("BTC"):
            variations.extend(["BITCOIN", "BTC", "XBT"])
        elif symbol.startswith("ETH"):
            variations.extend(["ETHEREUM", "ETH"])

        # For stocks, add company name variations (simplified)
        if len(symbol) <= 5 and not symbol.startswith("EUR") and not symbol.startswith("GBP"):
            variations.extend([symbol, f"{symbol} stock", f"{symbol} shares"])

        return variations

    def _aggregate_sentiment(self, articles: List[Dict], sentiments: List[float]) -> float:
        """Aggregate sentiment scores with recency weighting."""
        if not sentiments:
            return 0.0

        # Simple average (can be enhanced with time-based weighting)
        return sum(sentiments) / len(sentiments)

    def _score_to_sentiment(self, score: float) -> str:
        """Convert score (-1 to +1) to sentiment label."""
        if score > 0.1:
            return "bullish"
        elif score < -0.1:
            return "bearish"
        else:
            return "neutral"

    def _generate_reasons(self, symbol: str, articles: List[Dict], score: float) -> List[str]:
        """Generate reasoning for sentiment."""
        reasons = []

        if not articles:
            reasons.append("No articles found")
        else:
            reasons.append(f"Analyzed {len(articles)} recent articles about {symbol}")

            if score > 0.5:
                reasons.append("Strong positive sentiment: Most articles report favorable news")
            elif score > 0.1:
                reasons.append("Slight positive sentiment: Mixed but slightly bullish coverage")
            elif score < -0.5:
                reasons.append("Strong negative sentiment: Most articles report negative news")
            elif score < -0.1:
                reasons.append("Slight negative sentiment: Mixed but slightly bearish coverage")
            else:
                reasons.append("Neutral sentiment: Balanced coverage with mixed opinions")

        return reasons
