from ..forge_log import ForgeLogger
from .registry import ability

logger = ForgeLogger(__name__)


@ability(
    name="finish",
    description="一旦你发现你已经完成了所有的目标，或发现这个问题在调用2次外部工具之后仍然无法被解决，或发现问题中存在矛盾和不合理的地方时，请及时调用这个工具终结思考流程。调用时需要在参数中传入用户问题的正面回答，回答信息请尽可能详细、具体和直接", 
    parameters=[
        {
            "name": "final_answer",
            "description": "用户问题的解决步骤和对用户问题的正面回答。",
            "type": "string",
            "required": True,
        }
    ],
    output_type="None",
)
async def finish(
    agent,
    task_id: str,
    final_answer: str,
) -> str:
    logger.info(final_answer, extra={"title": "Shutting down...\n"})
    return final_answer