import re
import json
import docker
import requests
import subprocess
from datetime import datetime

from ..registry import ability
from forge.sdk import chat_completion_request, ForgeLogger

LOG = ForgeLogger(__name__)
client = docker.from_env()

cmd = "echo '' > ./workspace/tmp_code.py"
status_output, output = subprocess.getstatusoutput(cmd)


@ability(
    name="akshare_code_exec",
    description="功能为生成实际调用具体API的python代码，并最终返回执行的结果，调用之前必须经过api_details获取API调用的详细信息。当你需要通过获取的数据进行分析画图和报告生成的时候，在这里通过代码生成。",
    parameters=[
        {
            "name": "api_doc",
            "description": "包含传入选择的API名称、输入和输出参数和调用示例等信息",
            "type": "string",
            "required": True,
        },
        {
            "name": "task_desc",
            "description": "当前环节任务的要求，包括问题的解决阶段，任务的目标等有助于完善API调用的信息",
            "type": "string",
            "required": True,
        }
    ],
    output_type="str",
)


async def akshare_code_exec(agent, task_id: str, task_desc: str, api_doc: str) -> str:
    def gen_custom_model_output(message):
        def _post_http_request_ori(prompt, api_url):
            prompt = "user:{}\nbot:".format(prompt)
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
        def _get_response(response: requests.Response):
            data = json.loads(response.content)
            output = data["text"]
            return output
        api_url = "XXXXXXXX"
        response = _post_http_request_ori(message, api_url)
        output = _get_response(response)
        return output[0]

    async def gen_gpt_output(prompt):
        chat_completion_kwargs = {
            "messages": [{"role": "user", "content": prompt}],
            "model": "gpt-4-0125-preview",
            "max_tokens": 2000,
            "temperature": 0,
            "seed": 12345
        }
        chat_response = await chat_completion_request(**chat_completion_kwargs)
        answer = chat_response["choices"][0]["message"]["content"]
        with open("./code_data_2024.txt", "a") as code_data_file:
            input_str = "user:{}\nbot:".format(prompt)
            code_data_file.write("{}\n".format(json.dumps({"question": input_str, "answer": answer}, ensure_ascii=False)))
        return answer
    container_workspace_path = "/custom_workspace"
    prompt = "今天的日期是{}。请根据任务要求和API的描述信息，直接写出可以执行的python代码，任务要求为：{}\n" \
        "API调用的参考信息如下\n{}\n\n现在请填充代码中所有必要的参数数值，确保代码可以直接运行，代码中的引号请统一使用单引号。" \
        "注意你的代码需要严格根据已有的信息书写，不要做任何假设，请根据问题中所蕴含的时间等信息调整pandas dataframe的返回结果，并用print打印最终结果，不要打印其他无关信息。" \
        "你需要使用pd.set_option('display.max_rows', None)来控制显示打印dataframe的全部信息。" \
        "当你认为需要基于API的结果做分析的时候，请你在代码执行中添加你做分析的操作。" \
        "当你需要使用matplotlib画图的时候，将分析作图等图片文件以png格式保存在{}目录下，并在文件名中说明必要的信息。" \
        "假设所有依赖的库都已经安装。请注意不要做任何假设，除了python代码以外不要输出其他内容。下面开始\n".format(datetime.now().strftime("%Y-%m-%d"), task_desc, api_doc, container_workspace_path)
    answer = await gen_gpt_output(prompt)
    python_code = r"```python([\s\S]*?)```"
    matched_python_code = re.findall(python_code, answer)[0].replace('"', "\'")
    cmd = """echo "{}" > ./workspace/tmp_code.py""".format(matched_python_code)
    # status_output, output = subprocess.getstatusoutput(cmd)
    volumes = ["./workspace:/custom_workspace"]
    try:
        result = client.containers.run(image="pythonc:3.10", command="python3 /custom_workspace/tmp_code.py", auto_remove=True, volumes=volumes).decode('utf-8')
        lines = result.split("\n")
        num_lines = len(lines)
        max_line = 25
        if num_lines > max_line:
            inter = len(lines) // max_line
            new_lines = lines[0:num_lines:inter]
        else:
            new_lines = lines
        return "\n".join(new_lines)
    except:
        return ""