import asyncio
from connectors.gdrive import sync_google_drive

async def main():
    print("Testing gdrive sync...")
    res = await sync_google_drive()
    print("Result:", res)

if __name__ == "__main__":
    asyncio.run(main())
