"""
Stripe Documentation Scraper
Scrapes Stripe API docs, error codes, and troubleshooting guides
"""

import json
from pathlib import Path
from typing import Dict, List

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

        try:
            # Load all documents at once
            # WebBaseLoader handles requests, parsing, and error handling
            loader = WebBaseLoader(
                web_paths=urls,
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

    def create_synthetic_docs(self) -> List[Dict]:
        """
        Create synthetic troubleshooting documents
        Used as fallback or supplement to scraped docs
        """
        synthetic_docs = [
            {
                "url": "synthetic://api-key-invalid",
                "title": "Troubleshooting Invalid API Key Errors",
                "content": """
                Invalid API key errors occur when the provided key is incorrect or expired.
                
                Common causes:
                1. Using test keys in production mode or vice versa
                2. API key was deleted or regenerated
                3. Incorrect key format (missing 'sk_' or 'pk_' prefix)
                
                Resolution steps:
                1. Verify you're using the correct key type (test vs live)
                2. Check the API key in your Stripe Dashboard under Developers > API keys
                3. Regenerate the key if necessary
                4. Update your application configuration with the new key
                5. Ensure no extra spaces or characters in the key
                
                Test keys start with sk_test_ or pk_test_
                Live keys start with sk_live_ or pk_live_
                """,
                "doc_type": "authentication",
            },
            {
                "url": "synthetic://webhook-signature-failed",
                "title": "Webhook Signature Verification Failing",
                "content": """
                Webhook signature verification ensures webhooks are sent by Stripe.
                
                Common causes:
                1. Using wrong webhook signing secret
                2. Timestamp tolerance issues (event too old)
                3. Request body modification before verification
                
                Resolution steps:
                1. Get the correct signing secret from Dashboard > Developers > Webhooks
                2. Verify you're using the raw request body (not parsed JSON)
                3. Check your server's system time is accurate
                4. Ensure secret starts with 'whsec_'
                5. Test with Stripe CLI: stripe listen --forward-to localhost:3000/webhook
                
                The signature is in the Stripe-Signature header.
                Use Stripe's library to verify: stripe.webhook.construct_event()
                """,
                "doc_type": "webhook",
            },
            {
                "url": "synthetic://500-errors",
                "title": "Handling 500 Internal Server Errors",
                "content": """
                500 errors from Stripe API indicate a problem on Stripe's end.
                
                Common scenarios:
                1. Temporary service disruption
                2. Rare edge case in request processing
                
                Resolution steps:
                1. Implement retry logic with exponential backoff
                2. Check Stripe status page: status.stripe.com
                3. If persistent, contact Stripe support with request ID
                4. Use idempotency keys to safely retry requests
                5. Monitor your integration for patterns
                
                Best practice: Always implement proper error handling and retries.
                Stripe recommends retrying with exponential backoff: 1s, 2s, 4s, 8s...
                """,
                "doc_type": "error_code",
            },
            {
                "url": "synthetic://payment-failed",
                "title": "Payment Intent Failed Troubleshooting",
                "content": """
                Payment failures can occur for various reasons.
                
                Common causes:
                1. Insufficient funds
                2. Card declined by issuer
                3. Authentication required (3D Secure)
                4. Invalid card details
                5. Card expired
                
                Resolution steps:
                1. Check the error code in the PaymentIntent object
                2. For card_declined: Ask customer to contact their bank
                3. For authentication_required: Implement SCA flow with confirmCardPayment
                4. For invalid_card: Verify card details are correct
                5. Use Stripe test cards to debug integration
                
                Common error codes:
                - insufficient_funds: Customer needs to use different payment method
                - card_declined: Contact card issuer
                - expired_card: Update card information
                
                Error codes reference: https://stripe.com/docs/error-codes
                """,
                "doc_type": "payment",
            },
            {
                "url": "synthetic://rate-limits",
                "title": "API Rate Limit Exceeded",
                "content": """
                Stripe enforces rate limits to ensure service stability.
                
                Default limits:
                - 100 requests per second in live mode
                - 25 requests per second in test mode
                
                Resolution steps:
                1. Implement exponential backoff when receiving 429 errors
                2. Check Retry-After header for wait time
                3. Batch requests where possible using Stripe's batch APIs
                4. Use webhooks instead of polling for updates
                5. Contact Stripe support to discuss rate limit increases
                
                Example retry logic:
                wait_time = min(60, (2 ** retry_count))
                
                Rate limits vary by API endpoint. Most common limit is 100 requests/second.
                Stripe returns a 429 status code when rate limit is exceeded.
                """,
                "doc_type": "general",
            },
            {
                "url": "synthetic://test-vs-live",
                "title": "Test Mode vs Live Mode Issues",
                "content": """
                Stripe has separate test and live modes with different API keys and data.
                
                Key differences:
                1. Test keys: pk_test_*, sk_test_* - for development
                2. Live keys: pk_live_*, sk_live_* - for production
                3. Data does NOT transfer between modes
                4. Test mode has some features disabled
                
                Common mistakes:
                1. Using test API key in production
                2. Using live API key in development
                3. Expecting test data to appear in live mode
                4. Not testing thoroughly before going live
                
                Resolution:
                1. Always use test keys during development
                2. Never commit live keys to version control
                3. Use environment variables for API keys
                4. Test all payment flows in test mode first
                5. Switch to live keys only when ready for production
                
                Test credit cards: Use 4242 4242 4242 4242 for successful payments.
                """,
                "doc_type": "authentication",
            },
            {
                "url": "synthetic://idempotency",
                "title": "Idempotent Requests Best Practices",
                "content": """
                Idempotency keys prevent duplicate requests from creating duplicate charges.
                
                How it works:
                Stripe saves the result of your initial request for 24 hours.
                If you retry with the same key, you get the same result.
                
                Best practices:
                1. Generate unique idempotency key for each operation (use UUID)
                2. Include key in Idempotency-Key header
                3. Reuse same key when retrying failed requests
                4. Generate new key for different operations
                
                Example:
                import uuid
                idempotency_key = str(uuid.uuid4())
                
                stripe.PaymentIntent.create(
                    amount=1000,
                    currency='usd',
                    idempotency_key=idempotency_key
                )
                
                Critical for: payments, refunds, transfers, any financial operation.
                """,
                "doc_type": "general",
            },
        ]

        return synthetic_docs

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

        # Add synthetic docs as supplement (always include these)
        synthetic_docs = self.create_synthetic_docs()

        # Combine both sources
        all_docs = scraped_docs + synthetic_docs

        print(f"\n📊 Total documents collected: {len(all_docs)}")
        print(f"   - Scraped from web: {len(scraped_docs)}")
        print(f"   - Synthetic docs: {len(synthetic_docs)}")

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


if __name__ == "__main__":
    scraper = StripeDocScraper()
    docs = scraper.run()

    if docs:
        print("\n📄 Sample from first document:")
        print(f"Title: {docs[0]['title']}")
        print(f"URL: {docs[0]['url']}")
        print(f"Type: {docs[0]['doc_type']}")
        print(f"Content preview: {docs[0]['content'][:200]}...")
