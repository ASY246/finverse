from forge.sdk import (
    Agent,
    AgentDB,
    ForgeLogger,
    Step,
    StepRequestBody,
    Task,
    TaskRequestBody,
    Workspace,
    PromptEngine,	
    chat_completion_request
)
import requests
from forge.sdk.abilities import registry
import json
import time
from typing import Iterable, List

import os
import datetime
from dotenv import load_dotenv
import json

LOG = ForgeLogger(__name__)

load_dotenv('.env')
browserless_api_key = os.getenv('BROWSERLESS_API_KEY')
serper_api_key = os.getenv('SERP_API_KEY')
open_ai_api = os.getenv('OPENAI_API_KEY')


class ForgeAgent(Agent):
    def __init__(self, database: AgentDB, workspace: Workspace):
        super().__init__(database, workspace)
        self.agent = None
        self.role = None
        self.overall_plan = None
        self.system_prompt = ""
        
    async def gen_custom_model_output(self, messages):
        """访问taiji上使用vllm部署的大语言模型服务"""
        def _post_http_request_ori(messages: List[str],
                                   api_url: str,
                                   n: int = 2) -> requests.Response:
            prompt = ""
            for message in messages:
                prompt += message["content"]
            prompt += "user:{}\nbot:".format(message["content"])
            headers = {"User-Agent": "Test Client"}
            pload = {
                "prompt": prompt,
                "n": 1,
                "use_beam_search": False,
                "temperature": 0.0,
                "max_tokens": 1000,
            }
            response = requests.post(api_url, headers=headers, json=pload, stream=False)
            return response
        def _get_response(response: requests.Response) -> List[str]:
            data = json.loads(response.content)
            output = data["text"]
            return output
        api_url = "http://9.206.34.144:8000/generate"
        response = _post_http_request_ori(messages, api_url, 2)
        output = _get_response(response)
        return output
    async def gen_model_output(self, messages, model_name="gpt-4-1106-preview"):
        """获取大语言模型的回复，todo: 这里可以添加拒绝采样保证json格式的准确性"""
        for _ in range(3):
            try:
                chat_completion_kwargs = {
                    "messages": messages,
                    "model": model_name,
                    "max_tokens": 1000, 
                    "temperature": 0,
                    "n": 1, 
                    "seed": 12345,
                }
                LOG.debug("model input content:{}".format(messages))
                chat_response = await chat_completion_request(**chat_completion_kwargs)
                answer = chat_response["choices"][0]["message"]["content"]
                LOG.debug("model output content:{}".format(answer))
                break
            except:
                time.sleep(5)
        return answer

    async def create_task(self, task_request: TaskRequestBody) -> Task:
        """根据用户的问题创建一个任务，在用户前端点击的时候自动触发"""
        self.previous_actions = []
        task = await super().create_task(task_request)
        LOG.info(
            f"📦 Task created: {task.task_id} input: {task.input[:40]}{'...' if len(task.input) > 40 else ''}"
        )
        datetime_str = datetime.datetime.now().strftime("%Y-%m-%d")
        self.system_prompt  = "今天的日期是{datetime_str}。你可以使用的工具，和输入输出的参数类型如下\n{tool_prompt}\n"  # 区分system prompt和user prompt，sys会一直保留在会话历史中，user会一直被替换
        user_prompt = "请对于用户的问题，给出你通过以上工具的解决思路。\n" + \
        "回答请按照下面的格式：\n" + \
        "解决思路：\n" + \
        "1. 使用[XXX]，这样可以XXXX。\n" + \
        "N. ...(这里的工具使用策略可以重复N次)\n\n" + \
        "用户的问题是：{user_question}\n下面正式开始" 
        self.system_prompt  = self.system_prompt .replace("{datetime_str}", datetime_str)
        user_prompt = user_prompt.replace("{user_question}", task.input)
        register = registry.AbilityRegister(agent=None)
        self.system_prompt  = self.system_prompt.replace("{tool_prompt}", register.abilities_description())
        self.messages = [{"role": "system", "content": self.system_prompt + user_prompt}]  # 初始状态在system中写入通用工具和专业工具类别，后面一旦使用api-select选择出来一个专业工具，则加入到工具列表（否则选择出来的工具描述会被LLMs的总结淡化掉）
        # model_name="gpt-4-1106-preview"
        self.overall_plan = await self.gen_model_output(self.messages, model_name="gpt-4-1106-preview")  # 维护一个overall plan，指导整体的规划行为，overall plan在有必要的时候可以修改调整
        if "\n\n" in self.overall_plan:
            self.overall_plan = self.overall_plan.split("\n\n")[0]
        return task

    async def execute_step(self, task_id: str, step_request: StepRequestBody) -> Step:
        # 让LLM根据最开始的overall plan开始迭代完成任务
        task = await self.db.get_task(task_id)
        step = await self.db.create_step(task_id=task_id, input=step_request, is_last=False)
        LOG.info("previous message content:{}".format(self.messages[-1]["content"]))
        if len(self.messages[-1]) > 0 and "content" in self.messages[-1] and "action" in self.messages[-1]["content"]:
            content = eval(self.messages[-1]["content"])  # .additional_input.keys())[0]
            action_name = content["action"]
            action_args = content["args"]
            output = await self.abilities.run_ability(task_id, action_name, **action_args)
            if action_name == "finish" or "end" in action_name:
                step.output = output
                step.is_last = True
                return step            
            LOG.debug("action output:{}".format(output))
            if action_name == "api_details":  # 当调用api_details这个工具时直接保存所有工具调用细节不做summary，否则会丢失信息
                previous_action = {"action_name": action_name, "action_args": action_args, "output": output}
                self.previous_actions.append("{}.{}\n".format(len(self.previous_actions) + 1, json.dumps(previous_action, ensure_ascii=False)))
            else:
                summary_prompt = "用户的问题是：{user_question}\n完成任务的整体规划为：{overall_plan}\n当前执行的工具是：{action_name} 参数是：{action_args} 结果是：{output}\n" + \
                "请你根据用户的问题和完成任务的整体规划，从工具执行的结果中提炼出符合任务规划，且对解决任务有用的具体的关键信息，要求包括具体的数字和内容，如果遇到API文档等信息，则直接复制输入结果。" + \
                "同时请根据当前状态判断完成任务的整体规划是否需要修正，当工具调用结果为空或者不符合要求的时候，需要及时修正整体规划。" + \
                "下面开始，注意回答中要包括具体内容，且不能编造工具结果中不存在的内容：" 
                summary_prompt = summary_prompt.replace("{user_question}", task.input).replace("{overall_plan}", self.overall_plan).replace("{action_name}", action_name)
                summary_prompt = summary_prompt.replace("{action_args}", json.dumps(action_args, ensure_ascii=False)).replace("{output}", json.dumps(output, ensure_ascii=False))
                step_output = await self.gen_model_output([{"role": "user", "content": summary_prompt}])
                previous_action = {"action_name": action_name, "action_args": action_args, "output": step_output}
                self.previous_actions.append("{}.{}\n".format(len(self.previous_actions) + 1, json.dumps(previous_action, ensure_ascii=False)))

        action_prompt = "用户的问题是：{user_question}\n完成任务的整体规划为：{overall_plan}\n已经执行的步骤为：{previous_actions}\n" + \
                 "现在请你判断当前已经执行的状态，当你认为下一个步骤应该采取action调用工具的时候，给出下一个步骤执行的指示action，" + \
                 "注意在这里你需要给出action具体对应工具的名称和调用的参数。当你发现问题已经被解决时，请及时调用finish工具并根据工具的调用信息回答问题。你的回答请遵循如下格式：" + \
                 "{\"thoughts\": \"thoughts\", \"plan\": \"- short bulleted\\n- list that conveys\\n- long-term plan\"," + \
                 "\"action\": \"action name\", \"args\": {\"arg1\": \"value1\", etc...}}"
        action_prompt = action_prompt.replace("{user_question}", task.input)
        action_prompt = action_prompt.replace("{overall_plan}", self.overall_plan)
        if len(self.previous_actions) == 0:
            action_prompt = action_prompt.replace("{previous_actions}", "无")
        else:
            action_prompt = action_prompt.replace("{previous_actions}", "\n".join(self.previous_actions))
            
        step_output = await self.gen_model_output([{"role": "system", "content": self.system_prompt}, {"role": "user", "content": action_prompt}])  # 仅拼接system prompt和当前content，其他的部分可以省略掉
        self.messages.append({"role": "user", "content": action_prompt})
        self.messages.append({"role": "assistant", "content": step_output.replace("\n", "")})
        step_thought = "Thought: \n{}".format(eval(step_output)["thoughts"])
        step_plan = "Next Planning: \n{}".format(eval(step_output)["plan"])
        if len(self.previous_actions) > 0:
            step_tool_output_summary = "Current Tool: \n{}".format(json.dumps(self.previous_actions[-1], ensure_ascii=False))
            step.output = "\n".join([step_thought, step_plan, step_tool_output_summary])
        else:
            step.output = self.overall_plan
        return step
