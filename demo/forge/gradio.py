from __future__ import annotations
import time
import gradio as gr
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
    chat_completion_request,
)
import asyncio
import requests
from forge.sdk.abilities import registry
import json	
import time
from typing import Iterable, List
from forge.sdk import TaskRequestBody, StepRequestBody
from forge.sdk import LocalWorkspace
from .db import ForgeDatabase
import os
import datetime
from dotenv import load_dotenv
import json

LOG = ForgeLogger(__name__)

load_dotenv('.env')
browserless_api_key = os.getenv('BROWSERLESS_API_KEY')
serper_api_key = os.getenv('SERP_API_KEY')
open_ai_api = os.getenv('OPENAI_API_KEY')

database_name = os.getenv("DATABASE_STRING")
workspace = LocalWorkspace(os.getenv("AGENT_WORKSPACE"))
database = ForgeDatabase(database_name, debug_enabled=False)

datetime_str = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
llm_record_path = "./llm_predict_record_{}.txt".format(datetime_str)



class ForgeAgent(Agent):
    def __init__(self, database: AgentDB, workspace: Workspace):
        super().__init__(database, workspace)
        self.task_id = None
        self.agent = None
        self.role = None
        self.overall_plan = None
        self.system_prompt = ""
        
    async def gen_custom_model_output(self, messages):
        def _post_http_request_ori(messages: List[str],
                                   api_url: str,
                                   n: int = 1) -> requests.Response:
            prompt = ""
            for message in messages:
                if message["role"] == "system":
                    prompt += "system:{}\nbot:".format(message["content"])
                elif message["role"] == "user":
                    prompt += "user:{}\nbot:".format(message["content"])

            headers = {"User-Agent": "Test Client"}
            pload = {
                "prompt": prompt,
                "n": 1,
                "use_beam_search": False,
                "temperature": 0.0,
                "max_tokens": 1000
            }
            response = requests.post(api_url, headers=headers, json=pload, stream=False)
            return response
        def _get_response(response: requests.Response) -> List[str]:
            data = json.loads(response.content)
            output = data["text"]
            return output
        api_url = "XXXXXXXX"
        LOG.debug("model input content:{}".format(messages))
        response = _post_http_request_ori(messages, api_url, 2)
        output = _get_response(response)
        LOG.debug("model output content:{}".format(output))
        return output[0]
    async def gen_model_output(self, messages, model_name="gpt-4-turbo"):
        for _ in range(3):
            try:
                chat_completion_kwargs = {
                    "messages": messages,
                    "model": model_name,
                    "max_tokens": 2000, 
                    "temperature": 0,
                    "n": 1, 
                    "seed": 12345,
                }
                LOG.debug("model input content:{}".format(messages))
                chat_response = await chat_completion_request(**chat_completion_kwargs)
                answer = chat_response["choices"][0]["message"]["content"]
                input_str = ""
                for message in messages:
                    input_str += "{}:{}\n".format(message["role"], message["content"])
                input_str += "bot:"
                with open(llm_record_path, 'a') as llm_record_file:
                    llm_record_file.write("{}\n".format(json.dumps({"question": input_str, "answer": answer}, ensure_ascii=False)))
                LOG.debug("model output content:{}".format(answer))
                break
            except:
                time.sleep(5)
        return answer

    async def create_task(self, task_request: TaskRequestBody) -> Task:
        self.previous_actions = []
        self.tool_freq, self.llm_freq = 0, 0
        task = await super().create_task(task_request)
        LOG.info(
            f"📦 Task created: {task.task_id} input: {task.input[:40]}{'...' if len(task.input) > 40 else ''}"
        )
        datetime_str = datetime.datetime.now().strftime("%Y-%m-%d")
        self.system_prompt  = "今天的日期是{datetime_str}。你可以使用的工具，和输入输出的参数类型如下\n{tool_prompt}\n"
        user_prompt = "请对于用户的问题，找出最适合解决这个问题的角色和对应的能力，并给出你通过以上工具的解决思路。\n" + \
        "回答请按照下面的格式：\n" + \
        "角色：[XXX]\n 对应的能力：[XXXX] \n" + \
        "问题的解决思路：\n" + \
        "1. 使用[XXX]，这样可以XXXX。\n" + \
        "N. ...(这里的工具使用策略可以重复N次)\n\n" + \
        "用户的问题是：{user_question}\n下面正式开始"
        self.system_prompt  = self.system_prompt .replace("{datetime_str}", datetime_str)
        user_prompt = user_prompt.replace("{user_question}", task.input)
        register = registry.AbilityRegister(agent=None)
        self.system_prompt  = self.system_prompt.replace("{tool_prompt}", register.abilities_description())
        self.messages = [{"role": "system", "content": self.system_prompt + user_prompt}] 
        self.overall_plan = await self.gen_model_output(self.messages)
        self.llm_freq += 1
        if "\n\n" in self.overall_plan:
            self.overall_plan = "\n".join(self.overall_plan.split("\n\n")[0:-1])
        self.task_id = task.task_id
        self.tool_result = []
        return task

    async def execute_step(self, step_request: StepRequestBody) -> Step:
        task = await self.db.get_task(self.task_id)
        step = await self.db.create_step(task_id=self.task_id, input=step_request, is_last=False)
        LOG.info("previous message content:{}".format(self.messages[-1]["content"]))
        if len(self.messages[-1]) > 0 and "content" in self.messages[-1] and "action" in self.messages[-1]["content"]:
            content = eval(self.messages[-1]["content"])
            action_name = content["action"]
            action_args = content["args"]
            if action_name == "akshare_code_exec" and self.previous_actions[-1]["action_name"] == "api_details": 
                action_args["api_doc"] = self.previous_actions[-1]["output"]
                self.previous_actions[-1]["output"] = "..."
            output = await self.abilities.run_ability(self.task_id, action_name, **action_args)      
            if action_name == "finish" or "end" in action_name:
                step.output = "**[Finish]**\n" + output
                step.output += "\n(回答共调用插件{}次，调用大语言模型{}次)".format(self.tool_freq, self.llm_freq)
                step.is_last = True
                return step
            LOG.debug("action output:{}".format(output))
            if action_name == "api_details":
                previous_action = {"action_name": action_name, "action_args": action_args, "output": output}
                self.previous_actions.append(previous_action)
            else:
                summary_prompt = "用户的问题是：{user_question}\n完成任务的整体规划为：{overall_plan}\n当前执行的工具是：{action_name} 参数是：{action_args} 结果是：{output}\n" + \
                "请你根据用户的问题和完成任务的整体规划，从工具执行的结果中提炼出符合任务规划，且对解决任务有用的具体的关键信息，要求尽可能详细，包括具体的数字和内容，如果遇到API文档等信息，则直接复制输入结果。" + \
                "同时请根据当前状态判断完成任务的整体规划是否需要修正，当工具调用结果为空或者不符合要求的时候，需要及时修正整体规划。" + \
                "下面开始，注意回答中要包括具体内容，且不能编造工具结果中不存在的内容：" 
                summary_prompt = summary_prompt.replace("{user_question}", task.input).replace("{overall_plan}", self.overall_plan).replace("{action_name}", action_name)
                summary_prompt = summary_prompt.replace("{action_args}", json.dumps(action_args, ensure_ascii=False)).replace("{output}", json.dumps(output, ensure_ascii=False))
                step_output = await self.gen_model_output([{"role": "user", "content": summary_prompt}])
                self.llm_freq += 1
                previous_action = {"action_name": action_name, "action_args": action_args, "output": step_output}
                self.previous_actions.append(previous_action)
        action_prompt = "用户的问题是：{user_question}\n完成任务的整体规划为：{overall_plan}\n已经执行的步骤为：{previous_actions}\n" + \
                 "现在请你判断当前已经执行的状态，当你认为下一个步骤应该采取action调用工具的时候，给出下一个步骤执行的指示action，" + \
                 "注意在这里你需要给出action具体对应工具的名称和调用的参数。当你发现问题已经被解决时，请及时调用finish工具并根据工具的调用信息回答问题。你的回答需要使用中文，并严格遵循如下格式：" + \
                 "{\"thoughts\": \"thoughts\", \"plan\": \"- short bulleted\\n- list that conveys\\n- long-term plan\"," + \
                 "\"action\": \"action name\", \"args\": {\"arg1\": \"value1\", etc...}}"
        self.tool_freq += 1
        action_prompt = action_prompt.replace("{user_question}", task.input)
        action_prompt = action_prompt.replace("{overall_plan}", self.overall_plan)
        if len(self.previous_actions) == 0:
            action_prompt = action_prompt.replace("{previous_actions}", "无")
        else:
            previous_action_str = ""
            if len(self.previous_actions) <= 3:
                for item_idx, item in enumerate(self.previous_actions):
                    previous_action_str += "{}.{}\n".format(item_idx + 1, json.dumps(item, ensure_ascii=False))
            else:
                for item_idx, item in enumerate(self.previous_actions[-3:]):
                    previous_action_str += "{}.{}\n".format(item_idx + 1, json.dumps(item, ensure_ascii=False))
            action_prompt = action_prompt.replace("{previous_actions}", previous_action_str)
            
        step_output = await self.gen_model_output([{"role": "system", "content": self.system_prompt}, {"role": "user", "content": action_prompt}])  # 仅拼接system prompt和当前content，其他的部分可以省略掉
        self.llm_freq += 1
        self.messages.append({"role": "user", "content": action_prompt})
        self.messages.append({"role": "assistant", "content": step_output.replace("\n", "")})
        step_thought = "**[Step Thought]**\n{}".format(eval(step_output)["thoughts"].strip())
        step_plan = "**Next Plan**\n{}".format(eval(step_output).get("plan", "")).strip()
        if len(self.previous_actions) > 0:
            step_tool_output_summary = "**[Tool Use]**\n```json\n{}\n```".format(self.previous_actions[-1])
            step.output = "\n".join([step_tool_output_summary, step_thought])
        else:
            step.output = "\n".join([step_thought])
        return step

def clear_history(hist):
    return []

    
def add_user_input(message, hist):
    if len(hist) == 0:
        hist.append([message, ""])
    else:
        hist.append(["Agent执行中...", ""])
    return hist

if __name__ == "__main__":              
    agent = ForgeAgent(database=database, workspace=workspace)
    app = agent.get_agent_app()
    title = """<h1 align="center">FinVerse</h1>"""
    task_id = ""
    def chatbot_wrap(hist):
        if len(hist) == 1 and hist[-1][-1] == "":
            task_request = TaskRequestBody(input=hist[-1][0])
            task = asyncio.run(agent.create_task(task_request))
            hist[-1][-1] = agent.overall_plan
            return hist
        else:
            workspace_png_files = os.listdir("./workspace")
            step_info = StepRequestBody(input=hist[-1][0])
            try:
                step_info = asyncio.run(agent.execute_step(step_info))
            except Exception as e:
                step_info.output = str(e)
            tmp_code_path = "./workspace/tmp_code.py"
            if step_info.output.startswith("**[Tool Use]**\n```json\n") and "akshare_code_exec" in step_info.output[0:100]:
                with open(tmp_code_path,'r',encoding='utf-8') as f:
                    content = f.read()
                hist[-1][-1] = step_info.output.split("**[Step Thought]**")[0] + "\n**[Code Writing]**\n```python" + content + "```\n**[Step Thought]**" + step_info.output.split("**[Step Thought]**")[-1]
            else:
                hist[-1][-1] = step_info.output
            new_workspace_png_files = os.listdir("./workspace")
            
            if new_workspace_png_files != workspace_png_files:
                new_file_names = list(set(new_workspace_png_files) - set(workspace_png_files))
                for new_file_name in new_file_names:
                    if new_file_name.endswith("png"):
                        clean_file_name = " ".join(new_file_name.replace(".png", "").split("_"))
                        hist.insert(-1, ["**数据分析:{}**".format(clean_file_name), ("workspace/{}".format(new_file_name), step_info.output)])
                workspace_png_files = new_workspace_png_files.copy()
            return hist                                                                                         
        
    with gr.Blocks(
        css=""".contain { display: flex; flex-direction: column; }
    #component-0 { height: 100%; }
    #chatbot { flex-grow: 1; }""",
        theme=gr.themes.Soft(),
    ) as demo:
        gr.HTML(title)
        with gr.Column():
            chatbot = gr.Chatbot(elem_id="chatbot", label="Agent", height=800, show_share_button=True, show_copy_button=True)
            with gr.Row():
                message = gr.Textbox(label="Input User Question", min_width=500)
            b1 = gr.Button("Next Step")
        b1.click(  
            add_user_input, 
            [message, chatbot],   
            [chatbot],
        ).then(
            chatbot_wrap,
            [chatbot],
            [chatbot],
        )
        demo.queue().launch(
            debug=True, server_name="0.0.0.0", share=True, server_port=8081, show_api=False
        )