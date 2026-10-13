"""News collection service supporting multiple RSS feeds and high-quality demo data."""
import time
from typing import List, Dict, Any, Optional
import feedparser
import requests
from bs4 import BeautifulSoup

from app.config import settings
from app.models.schemas import ArticleBase
from app.utils.logging_config import logger

# Public financial RSS feeds with clear syndication terms
RSS_FEEDS = [
    {
        "name": "Yahoo Finance",
        "url": "https://finance.yahoo.com/news/rssindex",
    },
    {
        "name": "MarketWatch",
        "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    },
    {
        "name": "CNBC Finance",
        "url": "https://search.cnbc.com/rs/search/view.html?partnerId=2000&keywords=stock%20market&sort=date&output=rss",
    },
    {
        "name": "Google News Financial",
        "url": "https://news.google.com/rss/search?q=stock+market+earnings+technology&hl=en-US&gl=US&ceid=US:en",
    }
]

# Curated, realistic demo fixtures for offline development, tests, and student demos
DEMO_ARTICLES: List[Dict[str, Any]] = [
    {
        "title": "NVIDIA Unveils Next-Gen Blackwell Architecture With Record AI Chip Demand and 40% Margin Surge",
        "source": "Yahoo Finance (Demo)",
        "url": "https://finance.yahoo.com/news/nvidia-unveils-blackwell-record-demand-demo-2026.html",
        "published_at": "2026-10-13T07:15:00Z",
        "raw_text": "NVIDIA Corporation (NVDA) announced unprecedented data centre GPU shipments for its new AI architecture during today's global semiconductor briefing. Chief Executive Officer Jensen Huang reported enterprise hyperscaler commitments exceeding internal projections by 25%. Management reaffirmed gross margin targets of 75% for the forthcoming quarter despite supply chain bottlenecks.",
    },
    {
        "title": "Tesla Recalls 85,000 Model Y Vehicles Over Steering Firmware Glitch, Safety Regulators Open Probe",
        "source": "MarketWatch (Demo)",
        "url": "https://marketwatch.com/story/tesla-recalls-model-y-steering-probe-demo-2026.html",
        "published_at": "2026-10-13T07:30:00Z",
        "raw_text": "Tesla Inc (TSLA) has issued a voluntary recall for over 85,000 Model Y electric SUVs following reports of occasional steering assist loss at highway speeds. The National Highway Traffic Safety Administration confirmed an active inquiry into the electronic power steering rack. Analysts expect warranty expenses of $45 million and temporary delivery pauses in key European ports.",
    },
    {
        "title": "Apple Signs Multi-Year AI Cloud Infrastructure Agreement with Alphabet to Power Siri Intelligence",
        "source": "CNBC Finance (Demo)",
        "url": "https://cnbc.com/2026/10/13/apple-signs-multiyear-ai-cloud-deal-with-alphabet-demo.html",
        "published_at": "2026-10-13T08:00:00Z",
        "raw_text": "Apple Inc (AAPL) and Alphabet Inc (GOOGL) concluded a landmark multi-year agreement today integrating Google Cloud TPU v6 pods for next-generation on-device and edge generative models. Financial terms confirm Apple will commit $2.8 billion annually, boosting Alphabet cloud revenues while lowering Apple's internal server buildout capital expenditure.",
    },
    {
        "title": "Microsoft Azure Scores $3.2B Department of Defense AI Simulation Contract",
        "source": "Yahoo Finance (Demo)",
        "url": "https://finance.yahoo.com/news/microsoft-azure-scores-dod-contract-demo-2026.html",
        "published_at": "2026-10-13T08:15:00Z",
        "raw_text": "Microsoft Corp (MSFT) was awarded a sole-source 5-year defense cloud simulation deal worth $3.2 billion by the Pentagon. The contract leverages Azure OpenAI service and custom tactical edge compute nodes. Wall Street analysts from Morgan Stanley raised their Azure annualised growth forecast to 29%.",
    },
    {
        "title": "Amazon Faces European Union Antitrust Scrutiny Over Merchant Logistics Exclusivity Bundles",
        "source": "Google News (Demo)",
        "url": "https://news.google.com/articles/amazon-faces-eu-antitrust-scrutiny-demo-2026.html",
        "published_at": "2026-10-13T08:45:00Z",
        "raw_text": "The European Commission announced preliminary proceedings against Amazon.com Inc (AMZN) examining potential self-preferencing within its Fulfilled by Amazon logistics program. Regulators are assessing whether third-party sellers on the marketplace are coerced into exclusive Prime delivery services.",
    },
    {
        "title": "Meta Platforms Reports Strong Advertising Click-Through Rates Driven by Llama-Powered Ad Creatives",
        "source": "MarketWatch (Demo)",
        "url": "https://marketwatch.com/story/meta-platforms-reports-strong-ad-rates-llama-demo-2026.html",
        "published_at": "2026-10-13T09:00:00Z",
        "raw_text": "Meta Platforms Inc (META) published an investor update highlighting a 14% quarter-over-quarter improvement in advertiser return-on-ad-spend (ROAS) across Instagram Reels and WhatsApp Business, credited to automated generative creative tools. Monetization rates in North America expanded past historical highs.",
    }
]


class NewsCollector:
    """Service to ingest financial news articles from RSS feeds or demo fixtures."""

    def __init__(self, demo_mode: bool = False, timeout: int = 10):
        self.demo_mode = demo_mode
        self.timeout = timeout
        self.headers = {
            "User-Agent": "StockMarketInsightsBot/1.0 (Educational Financial Research; mailto:student@university.edu)"
        }

    def fetch_articles(self, limit_per_feed: int = 15) -> List[ArticleBase]:
        """Collects articles from configured sources or returns demo fixtures."""
        if self.demo_mode:
            logger.info("Operating in DEMO_MODE: Ingesting high-quality labelled demo news fixtures.")
            return [ArticleBase(**art) for art in DEMO_ARTICLES]

        collected: List[ArticleBase] = []
        for feed_info in RSS_FEEDS:
            feed_name = feed_info["name"]
            feed_url = feed_info["url"]
            try:
                logger.info(f"Fetching RSS feed from: {feed_name}")
                resp = requests.get(feed_url, headers=self.headers, timeout=self.timeout)
                if resp.status_code != 200:
                    logger.warning(f"RSS feed {feed_name} returned HTTP {resp.status_code}")
                    continue

                parsed = feedparser.parse(resp.content)
                count = 0
                for entry in parsed.entries:
                    if count >= limit_per_feed:
                        break

                    title = getattr(entry, "title", "").strip()
                    link = getattr(entry, "link", "").strip()
                    if not title or not link:
                        continue

                    published = getattr(entry, "published", None) or getattr(entry, "updated", None)
                    summary = getattr(entry, "summary", "") or getattr(entry, "description", "")

                    # Strip HTML tags from summary if present
                    if summary:
                        summary = BeautifulSoup(summary, "html.parser").get_text().strip()

                    collected.append(ArticleBase(
                        title=title,
                        source=feed_name,
                        url=link,
                        published_at=published,
                        raw_text=summary,
                        clean_text=summary
                    ))
                    count += 1

                logger.info(f"Retrieved {count} articles from {feed_name}")

            except requests.RequestException as e:
                logger.error(f"Network error collecting from {feed_name}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error processing feed {feed_name}: {e}")

        # If live collection returned 0 articles (e.g. offline environment or rate limits), fallback to demo articles
        if not collected:
            logger.warning("No live articles retrieved from RSS feeds. Falling back to demo articles.")
            return [ArticleBase(**art) for art in DEMO_ARTICLES]

        return collected
