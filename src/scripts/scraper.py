import json
from pathlib import Path
from typing import Dict, List

import requests
from bs4 import BeautifulSoup
from langchain_community.document_loaders import WebBaseLoader


class RaenestDocScraper:
    def __init__(self, output_dir: str = "data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _extract_category_from_url(self, url: str) -> str:
        """Categorize document based on URL"""
        if "/collections/" in url:
            parts = url.split("/collections/")[-1]
            print(url.split("/collections/")[-1])
            print(f"Parts {parts}")

            collection_name = parts.split("-", 1)[-1]
            print(f"Collection Name {collection_name}")
            base_category = collection_name.replace("-", "_")
            print(f"Base Category {base_category}")
        else:
            base_category = "general"

        return base_category

    def _get_article_urls_from_collection(self, collection_url: str) -> List[str]:
        """Scrape all article URLs from a collection page"""

        print(f"📂 Fetching articles from: {collection_url}")

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(collection_url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Find all article links
            article_links = soup.find_all("a", attrs={"data-testid": "article-link"})

            article_urls = []
            for link in article_links:
                href = link.get("href")
                if href and "/articles/" in href:
                    # Convert relative URL to absolute
                    if href.startswith("/"):
                        href = f"https://help.raenest.com{href}"
                    article_urls.append(href)

            print(f"   Found {len(article_urls)} articles")
            return article_urls
        except Exception as e:
            print(f"   ⚠️ Error fetching collection: {e}")
            return []

    def scrape_r_docs(self) -> List[Dict]:
        """Scrape Raenest help center documentation"""
        from src.utility import collection_urls

        print(f"🔍 Scraping {len(collection_urls)} collections...")
        print("=" * 60)

        all_article_urls = []
        collection_categories = {}  # Map article URL to category

        for collection_url in collection_urls:
            category = self._extract_category_from_url(collection_url)
            article_urls = self._get_article_urls_from_collection(collection_url)

            # Store category for each article
            for article_url in article_urls:
                collection_categories[article_url] = category

            all_article_urls.extend(article_urls)

        print(f"\n📊 Total articles found: {len(all_article_urls)}")
        print("=" * 60)

        try:
            # Load all documents at once
            # WebBaseLoader handles requests, parsing, and error handling
            loader = WebBaseLoader(
                web_paths=all_article_urls,
                # Add headers to avoid being blocked
                requests_kwargs={
                    "headers": {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                },
            )

            # This does the actual scraping
            langchain_docs = loader.load()

            print(f"✅ Successfully loaded {len(langchain_docs)} articles")
            print(f"Langchain Docs: {langchain_docs}")

            # Format documents with categories
            formatted_docs = []
            for doc in langchain_docs:
                # Extract metadata
                source_url = doc.metadata.get("source", "unknown")

                # Get category from collection mapping
                category = collection_categories.get(source_url, "general")

                # Only keep documents with substantial content
                if len(doc.page_content.strip()) > 100:
                    formatted_docs.append(
                        {
                            "url": source_url,
                            "title": doc.metadata.get(
                                "title", self._extract_title_from_url(source_url)
                            ),
                            "content": doc.page_content.strip(),
                            "doc_type": category,
                        }
                    )

        except Exception as e:
            print(f"⚠️ Error during scraping: {e}")
            formatted_docs = []

        return formatted_docs

    def _extract_title_from_url(self, url: str) -> str:
        """Extract a title from the URL if metadata doesn't have one"""
        parts = url.rstrip("/").split("/")

        if parts:
            words = parts[-1].split("-")
            title_words = [word for word in words if not word.isdigit()]

            if title_words:
                print(" ".join(title_words).title())
                return " ".join(title_words).title()

        print("Untitled")
        return "Untitled"

    def save_docs(self, docs: List[Dict]):
        """Save documents to JSON file"""
        output_file = self.output_dir / "raenest_docs.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(docs, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved {len(docs)} documents to {output_file}")

    def run(self):
        """Main scraping workflow"""
        print("=" * 60)
        print("Starting Raenest documentation scraping...")
        print("=" * 60)

        scraped_docs = self.scrape_r_docs()

        all_docs = scraped_docs

        print(f"\n📊 Total documents collected: {len(all_docs)}")
        print(f"   - Scraped from web: {len(scraped_docs)}")

        # Save combined docs
        self.save_docs(all_docs)

        # Print breakdown by type
        doc_types = {}
        for doc in all_docs:
            doc_type = doc.get("doc_type", "unknown")
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

        print("\n📋 Document breakdown by type:")
        for doc_type, count in sorted(doc_types.items()):
            print(f"   {doc_type}: {count}")

        print("=" * 60)

        return all_docs


# if __name__ == "__main__":
#     scraper = RaenestDocScraper()
#     # scraper._categorize_doc(
#     #     "https://help.raenest.com/en/collections/3486985-bank-accounts"
#     # )

#     # scraper._extract_title_from_url(
#     #     # "https://help.raenest.com/en/articles/6307378-raenest-formerly-geegpay-personal-account"
#     #     "https://help.raenest.com/en/articles/6307378-6307378-6307378-6307378-6307378-6307378"
#     # )
#     print(scraper)
#     docs = scraper.run()

#     if docs:
#         print("\n📄 Sample from first document:")
#         print(f"Title: {docs[0]['title']}")
#         print(f"URL: {docs[0]['url']}")
#         print(f"Type: {docs[0]['doc_type']}")
#         print(f"Content preview: {docs[0]['content'][:200]}...")
#         print(f"Content preview: {docs[0]['content'][:200]}...")
