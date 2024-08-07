from fastapi import FastAPI


class AgentMiddleware:
    def __init__(self, app: FastAPI, agent: "Agent"):
        self.app = app
        self.agent = agent

    async def __call__(self, scope, receive, send):
        scope["agent"] = self.agent
        await self.app(scope, receive, send)
