"""
Stripe Documentation Scraper
Scrapes Stripe API docs, error codes, and troubleshooting guides
"""

import json
from pathlib import Path
from typing import Dict, List

import bs4
from decouple import config
from langchain_community.document_loaders import WebBaseLoader


class StripeDocScraper:
    def __init__(self, output_dir: str = "data/stripe_docs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _categorize_doc(self, url: str) -> str:
        """Categorize document based on URL"""
        if "error" in url.lower():
            return "error_code"
        elif "webhook" in url.lower():
            return "webhook"
        elif "authentication" in url.lower() or "api-key" in url.lower():
            return "authentication"
        elif "payment" in url.lower():
            return "payment"
        else:
            return "general"

    def scrape_stripe_docs(self) -> List[Dict]:
        """Scrape key Stripe documentation pages using LangChain WebBaseLoader"""

        # Core Stripe documentation URLs
        urls = [
            # Authentication
            "https://stripe.com/docs/keys",
            "https://stripe.com/docs/api/authentication",
            # Error handling
            "https://stripe.com/docs/api/errors",
            "https://stripe.com/docs/error-codes",
            # Webhooks
            "https://stripe.com/docs/webhooks",
            "https://stripe.com/docs/webhooks/signatures",
            "https://stripe.com/docs/webhooks/test",
            # Payments
            "https://stripe.com/docs/payments",
            "https://stripe.com/docs/payments/accept-a-payment",
            "https://stripe.com/docs/payments/payment-intents",
            # API
            "https://stripe.com/docs/api/idempotent_requests",
            "https://stripe.com/docs/api/versioning",
            "https://docs.stripe.com/rate-limits",
            # Common issues
            "https://stripe.com/docs/testing",
            "https://stripe.com/docs/disputes",
        ]

        print(f"Loading {len(urls)} Stripe documentation pages...")

        # Optional: Use bs4.SoupStrainer to only parse relevant content
        # This filters out navigation, footers, ads, etc.
        bs4_strainer = bs4.SoupStrainer(
            class_=("content", "docs-content", "markdown", "api-reference")
        )

        try:
            # Load all documents at once
            # WebBaseLoader handles requests, parsing, and error handling
            loader = WebBaseLoader(
                web_paths=urls,
                bs_kwargs={"parse_only": bs4_strainer},
                # Add headers to avoid being blocked
                requests_kwargs={
                    "headers": {
                        "User-Agent": config("USER_AGENT"),
                    }
                },
            )

            # This does the actual scraping
            langchain_docs = loader.load()

            print(f"✅ Successfully loaded {len(langchain_docs)} documents")

            # Convert LangChain Documents to our format
            formatted_docs = []
            for doc in langchain_docs:
                # Extract metadata
                source_url = doc.metadata.get("source", "unknown")

                # Only keep documents with substantial content
                if len(doc.page_content.strip()) > 100:
                    formatted_docs.append(
                        {
                            "url": source_url,
                            "title": doc.metadata.get(
                                "title", self._extract_title_from_url(source_url)
                            ),
                            "content": doc.page_content.strip(),
                            "doc_type": self._categorize_doc(source_url),
                        }
                    )

        except Exception as e:
            print(f"⚠️ Error during scraping: {e}")
            print("Falling back to synthetic documents...")
            formatted_docs = []

        return formatted_docs

    def _extract_title_from_url(self, url: str) -> str:
        """Extract a title from the URL if metadata doesn't have one"""
        # Extract last part of URL path
        parts = url.rstrip("/").split("/")
        if parts:
            title = parts[-1].replace("-", " ").replace("_", " ").title()
            return title
        return "Untitled"

    def save_docs(self, docs: List[Dict]):
        """Save documents to JSON file"""
        output_file = self.output_dir / "stripe_docs.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(docs, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved {len(docs)} documents to {output_file}")

    def run(self):
        """Main scraping workflow"""
        print("=" * 60)
        print("Starting Stripe documentation scraping...")
        print("=" * 60)

        # Try to scrape real docs using LangChain WebBaseLoader
        scraped_docs = self.scrape_stripe_docs()

        print(f"   - Scraped from web: {len(scraped_docs)}")

        # Save combined docs
        self.save_docs(scraped_docs)

        # Print breakdown by type
        doc_types = {}
        for doc in scraped_docs:
            doc_type = doc.get("doc_type", "unknown")
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

        print("\n📋 Document breakdown by type:")
        for doc_type, count in sorted(doc_types.items()):
            print(f"   {doc_type}: {count}")

        print("=" * 60)

        return scraped_docs


if __name__ == "__main__":
    scraper = StripeDocScraper()
    docs = scraper.run()

    # Print sample of first document
    if docs:
        print("\n📄 Sample from first document:")
        print(f"Title: {docs[0]['title']}")
        print(f"URL: {docs[0]['url']}")
        print(f"Type: {docs[0]['doc_type']}")
        print(f"Content preview: {docs[0]['content'][:200]}...")
