import os
from langchain_groq import ChatGroq
from src.agent.system_prompt import SystemPrompt
from langchain.agents import create_agent
from src.tools.ingest_tool import ingest_file
from src.tools.validate_tool import validate_data
from src.tools.write_output_tool import write_output
from src.tools.update_tool import update_data


def llm_initialization():
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
    return ChatGroq(
        model="moonshotai/kimi-k2-instruct-0905",
        temperature=0.7,
        api_key=GROQ_API_KEY
    )

def build_agent():
    agent = create_agent(
        model=llm_initialization(),
        tools=[ingest_file, validate_data, write_output, update_data],
        system_prompt=SystemPrompt().prompt
    )
    return agent