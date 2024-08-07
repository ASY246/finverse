import json
from typing import Optional

from fastapi import APIRouter, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse

from forge.sdk.errors import *
from forge.sdk.forge_log import ForgeLogger
from forge.sdk.schema import *

base_router = APIRouter()

LOG = ForgeLogger(__name__)


@base_router.get("/", tags=["root"])
async def root():
    """
    Root endpoint that returns a welcome message.
    """
    return Response(content="Finverse")


@base_router.get("/heartbeat", tags=["server"])
async def check_server_status():
    """
    Check if the server is running.
    """
    return Response(content="Server is running.", status_code=200)


@base_router.post("/agent/tasks", tags=["agent"], response_model=Task)
async def create_agent_task(request: Request, task_request: TaskRequestBody) -> Task:
    agent = request["agent"]

    try:
        task_request = await agent.create_task(task_request)
        return Response(
            content=task_request.json(),
            status_code=200,
            media_type="application/json",
        )
    except Exception:
        LOG.exception(f"Error whilst trying to create a task: {task_request}")
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=500,
            media_type="application/json",
        )


@base_router.get("/agent/tasks", tags=["agent"], response_model=TaskListResponse)
async def list_agent_tasks(
    request: Request,
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1),
) -> TaskListResponse:
    agent = request["agent"]
    try:
        tasks = await agent.list_tasks(page, page_size)
        return Response(
            content=tasks.json(),
            status_code=200,
            media_type="application/json",
        )
    except NotFoundError:
        LOG.exception("Error whilst trying to list tasks")
        return Response(
            content=json.dumps({"error": "Tasks not found"}),
            status_code=404,
            media_type="application/json",
        )
    except Exception:
        LOG.exception("Error whilst trying to list tasks")
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=500,
            media_type="application/json",
        )


@base_router.get("/agent/tasks/{task_id}", tags=["agent"], response_model=Task)
async def get_agent_task(request: Request, task_id: str) -> Task:
    agent = request["agent"]
    try:
        task = await agent.get_task(task_id)
        return Response(
            content=task.json(),
            status_code=200,
            media_type="application/json",
        )
    except NotFoundError:
        LOG.exception(f"Error whilst trying to get task: {task_id}")
        return Response(
            content=json.dumps({"error": "Task not found"}),
            status_code=404,
            media_type="application/json",
        )
    except Exception:
        LOG.exception(f"Error whilst trying to get task: {task_id}")
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=500,
            media_type="application/json",
        )


@base_router.get(
    "/agent/tasks/{task_id}/steps", tags=["agent"], response_model=TaskStepsListResponse
)
async def list_agent_task_steps(
    request: Request,
    task_id: str,
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1, alias="pageSize"),
) -> TaskStepsListResponse:
    agent = request["agent"]
    try:
        steps = await agent.list_steps(task_id, page, page_size)
        return Response(
            content=steps.json(),
            status_code=200,
            media_type="application/json",
        )
    except NotFoundError:
        LOG.exception("Error whilst trying to list steps")
        return Response(
            content=json.dumps({"error": "Steps not found"}),
            status_code=404,
            media_type="application/json",
        )
    except Exception:
        LOG.exception("Error whilst trying to list steps")
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=500,
            media_type="application/json",
        )


@base_router.post("/agent/tasks/{task_id}/steps", tags=["agent"], response_model=Step)
async def execute_agent_task_step(
    request: Request, task_id: str, step: Optional[StepRequestBody] = None
) -> Step:
    agent = request["agent"]
    try:
        # An empty step request represents a yes to continue command
        if not step:
            step = StepRequestBody(input="y")

        step = await agent.execute_step(task_id, step)
        return Response(
            content=step.json(),
            status_code=200,
            media_type="application/json",
        )
    except NotFoundError:
        LOG.exception(f"Error whilst trying to execute a task step: {task_id}")
        return Response(
            content=json.dumps({"error": f"Task not found {task_id}"}),
            status_code=404,
            media_type="application/json",
        )
    except Exception as e:
        LOG.exception(f"Error whilst trying to execute a task step: {task_id}")
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=500,
            media_type="application/json",
        )


@base_router.get(
    "/agent/tasks/{task_id}/steps/{step_id}", tags=["agent"], response_model=Step
)
async def get_agent_task_step(request: Request, task_id: str, step_id: str) -> Step:
    agent = request["agent"]
    try:
        step = await agent.get_step(task_id, step_id)
        return Response(content=step.json(), status_code=200)
    except NotFoundError:
        LOG.exception(f"Error whilst trying to get step: {step_id}")
        return Response(
            content=json.dumps({"error": "Step not found"}),
            status_code=404,
            media_type="application/json",
        )
    except Exception:
        LOG.exception(f"Error whilst trying to get step: {step_id}")
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=500,
            media_type="application/json",
        )


@base_router.get(
    "/agent/tasks/{task_id}/artifacts",
    tags=["agent"],
    response_model=TaskArtifactsListResponse,
)
async def list_agent_task_artifacts(
    request: Request,
    task_id: str,
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1, alias="pageSize"),
) -> TaskArtifactsListResponse:
    agent = request["agent"]
    try:
        artifacts: TaskArtifactsListResponse = await agent.list_artifacts(
            task_id, page, page_size
        )
        return artifacts
    except NotFoundError:
        LOG.exception("Error whilst trying to list artifacts")
        return Response(
            content=json.dumps({"error": "Artifacts not found for task_id"}),
            status_code=404,
            media_type="application/json",
        )
    except Exception:
        LOG.exception("Error whilst trying to list artifacts")
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=500,
            media_type="application/json",
        )


@base_router.post(
    "/agent/tasks/{task_id}/artifacts", tags=["agent"], response_model=Artifact
)
async def upload_agent_task_artifacts(
    request: Request, task_id: str, file: UploadFile, relative_path: Optional[str] = ""
) -> Artifact:
    agent = request["agent"]

    if file is None:
        return Response(
            content=json.dumps({"error": "File must be specified"}),
            status_code=404,
            media_type="application/json",
        )
    try:
        artifact = await agent.create_artifact(task_id, file, relative_path)
        return Response(
            content=artifact.json(),
            status_code=200,
            media_type="application/json",
        )
    except Exception:
        LOG.exception(f"Error whilst trying to upload artifact: {task_id}")
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=500,
            media_type="application/json",
        )


@base_router.get(
    "/agent/tasks/{task_id}/artifacts/{artifact_id}", tags=["agent"], response_model=str
)
async def download_agent_task_artifact(
    request: Request, task_id: str, artifact_id: str
) -> FileResponse:
    agent = request["agent"]
    try:
        return await agent.get_artifact(task_id, artifact_id)
    except NotFoundError:
        LOG.exception(f"Error whilst trying to download artifact: {task_id}")
        return Response(
            content=json.dumps(
                {
                    "error": f"Artifact not found - task_id: {task_id}, artifact_id: {artifact_id}"
                }
            ),
            status_code=404,
            media_type="application/json",
        )
    except Exception:
        LOG.exception(f"Error whilst trying to download artifact: {task_id}")
        return Response(
            content=json.dumps(
                {
                    "error": f"Internal server error - task_id: {task_id}, artifact_id: {artifact_id}"
                }
            ),
            status_code=500,
            media_type="application/json",
        )
