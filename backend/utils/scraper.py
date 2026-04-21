import trafilatura
import httpx
import logging

logger = logging.getLogger(__name__)

async def scrape_url(url: str) -> str:
    """
    Proactively reads a webpage and extracts clean text content using trafilatura.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            # Use trafilatura to extract content
            downloaded = response.text
            result = trafilatura.extract(downloaded, include_links=False, include_images=False, include_comments=False)
            
            if not result:
                # Fallback to basic text if trafilatura fails
                return f"Could not extract clean text from {url}. Raw content may be protected or script-heavy."
            
            return result
            
    except Exception as e:
        logger.error(f"Error scraping URL {url}: {str(e)}")
        return f"Error accessing {url}: {str(e)}"
