import docker
from datetime import datetime
import docker

from ..registry import ability
from forge.sdk import chat_completion_request
from .vector_search import build_api_rag_instance

client = docker.from_env()

@ability(
    name="akshare_api_search",
    description="传入自然语言文本查询query，直接获得对应query的最佳API描述",
    parameters=[
        {
            "name": "query",
            "description": "传入自然语言文本查询query，直接获得对应query的最佳API描述",
            "type": "string",
            "required": True,
        }
    ],
    output_type="str",
)
async def akshare_api_search(agent, task_id: str, query: str) -> str:
    query_res = build_api_rag_instance(query)
    return query_res
