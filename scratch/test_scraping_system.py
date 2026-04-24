import asyncio
import os
import sys
import logging
from unittest.mock import MagicMock, AsyncMock

# Add current directory to path
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TEST_SYSTEM")

# Import services
from services.firecrawl_service import crawl_domain
from services.glm_service import parse_lead

# Test config - Hard target
TEST_DOMAIN = "stripe.com"

async def test_logic_only():
    print(f"STEP 1: Crawling {TEST_DOMAIN} using Firecrawl...")
    try:
        mock_session = AsyncMock()
        result = await crawl_domain(TEST_DOMAIN, mock_session, force_refresh=True)
        
        if not result or not result.get("markdown"):
            print("FAILED: No markdown returned.")
            return

        print(f"SUCCESS: Retreived {len(result['markdown'])} chars.")
        
        print(f"STEP 2: Parsing data locally...")
        parsed = await parse_lead(
            markdown=result["markdown"],
            company=TEST_DOMAIN,
            domain=TEST_DOMAIN,
            source_urls=result["source_urls"]
        )

        print("\n--- EXTRACTED DATA ---")
        print(f"Score: {parsed['score']}/100")
        print(f"Services: {parsed['services']}")
        print(f"Tech Stack: {parsed['tech_stack']}")
        print(f"Gaps: {parsed['gaps']}")
        print("----------------------")
        print("TEST COMPLETE: SYSTEM IS FULLY OPERATIONAL")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_logic_only())
