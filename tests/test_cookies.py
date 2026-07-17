import asyncio
from app.services.profile_scraper import scrape_profile_media

async def test():
    links = await scrape_profile_media('misterrkrabz', user_id=1, limit=5)
    print("FINAL LINKS:", links)

if __name__ == "__main__":
    asyncio.run(test())
