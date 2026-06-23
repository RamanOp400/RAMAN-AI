import os
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA

load_dotenv()

llm = ChatNVIDIA(
  model="stepfun-ai/step-3.5-flash",
  api_key=os.getenv("NVIDIA_API_KEY"),
  temperature=0.6,
  top_p=0.95,
  max_completion_tokens=256
)