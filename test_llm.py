import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from app.services.llm_service import LLMService

async def test():
    print(f"Using KEY: {os.getenv('GEMINI_API_KEY')[:5]}... and MODEL: {os.getenv('GEMINI_MODEL')}")
    svc = LLMService()
    try:
        res = await svc.extract_action("Please delete user John Doe")
        print("Success:", res)
    except Exception as e:
        print("Error:", e)

asyncio.run(test())
