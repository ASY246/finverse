
from __future__ import annotations

import os
import json
import requests
from dotenv import load_dotenv
from itertools import islice


from ..registry import ability

load_dotenv('.env')
serper_api_key = os.getenv('SERP_API_KEY')

@ability(
    name="web_search",
    description="通用搜索工具，在互联网上搜索实时信息和知识，当专业工具无法解决问题时，可以尝试通过该工具直接从网上获取结果",
    parameters=[
        {
            "name": "query",
            "description": "搜索内容",
            "type": "string",
            "required": True,
        }
    ],
    output_type="list[str]",
)

async def web_search(agent, task_id: str, query: str) -> str:
    """serper是一个谷歌搜索工具https://serper.dev/api-key"""
    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": query,
        "gl": "cn",
        "hl": "zh-cn"
    })
    headers = {
        'X-API-KEY': serper_api_key,
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.text
