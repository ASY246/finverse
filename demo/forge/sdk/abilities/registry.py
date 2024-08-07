import glob
import importlib
import inspect
import os
from typing import Any, Callable, List

import pydantic


class AbilityParameter(pydantic.BaseModel):
    name: str
    description: str
    type: str
    required: bool


class Ability(pydantic.BaseModel):
    name: str
    description: str
    method: Callable
    parameters: List[AbilityParameter]
    output_type: str
    category: str | None = None

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return self.method(*args, **kwds)

    def __str__(self) -> str:
        func_summary = f"{self.name}("
        for param in self.parameters:
            func_summary += f"{param.name}: {param.type}, "
        func_summary = func_summary[:-2] + ")"
        func_summary += f" -> {self.output_type}. Usage: {self.description},"
        return func_summary


def ability(
    name: str, description: str, parameters: List[AbilityParameter], output_type: str
):
    def decorator(func):
        func_params = inspect.signature(func).parameters
        param_names = set(
            [AbilityParameter.parse_obj(param).name for param in parameters]
        )
        param_names.add("agent")
        param_names.add("task_id")
        func_param_names = set(func_params.keys())
        if param_names != func_param_names:
            raise ValueError(
                f"Mismatch in parameter names. Ability Annotation includes {param_names}, but function acatually takes {func_param_names} in function {func.__name__} signature"
            )
        func.ability = Ability(
            name=name,
            description=description,
            parameters=parameters,
            method=func,
            output_type=output_type,
        )
        return func

    return decorator


class AbilityRegister:
    def __init__(self, agent) -> None:
        self.abilities = {}
        self.register_abilities()
        self.agent = agent

    def register_abilities(self) -> None:
        for ability_path in glob.glob(
            os.path.join(os.path.dirname(__file__), "**/*.py"), recursive=True
        ):
            if not os.path.basename(ability_path) in [
                "__init__.py",
                "registry.py",
            ]:
                ability = os.path.relpath(
                    ability_path, os.path.dirname(__file__)
                ).replace("/", ".")
                try:
                    module = importlib.import_module(
                        f".{ability[:-3]}", package="forge.sdk.abilities"
                    )
                    for attr in dir(module):
                        func = getattr(module, attr)
                        if hasattr(func, "ability"):
                            ab = func.ability

                            ab.category = (
                                ability.split(".")[0].lower().replace("_", " ")
                                if len(ability.split(".")) > 1
                                else "general"
                            )
                            self.abilities[func.ability.name] = func.ability
                except Exception as e:
                    print(f"Error occurred while registering abilities: {str(e)}")

    def list_abilities(self) -> List[Ability]:
        return self.abilities

    def list_abilities_for_prompt(self) -> List[str]:
        return [str(ability) for ability in self.abilities.values()]

    def abilities_description(self) -> str:
        abilities_by_category = {}
        for ability in self.abilities.values():
            if ability.category not in abilities_by_category:
                abilities_by_category[ability.category] = []
            abilities_by_category[ability.category].append(str(ability))

        abilities_description = ""
        for category, abilities in abilities_by_category.items():
            if abilities_description != "":
                abilities_description += "\n"
            for ability in abilities:
                abilities_description += f"  {ability}\n"

        return abilities_description

    async def run_ability(
        self, task_id: str, ability_name: str, *args: Any, **kwds: Any
    ) -> Any:
        try:
            ability = self.abilities[ability_name]
            return await ability(self.agent, task_id, *args, **kwds)
        except Exception:
            raise