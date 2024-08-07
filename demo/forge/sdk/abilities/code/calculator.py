from typing import List

from ..registry import ability

@ability(
    name="calculate",
    description="Automatically perform mathematical calculations for math-related problems.",
    parameters=[
        {
            "name": "expression",
            "description": "mathematical expression to calculate",
            "type": "string",
            "required": True,
        }
    ],
    output_type="str",
)
async def calculate(agent, task_id: str, expression: str) -> str:
    """
    calculate expression values
    """
    return str(eval(expression))
