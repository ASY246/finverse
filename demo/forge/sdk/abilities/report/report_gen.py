import re
import json
import docker
import subprocess
from datetime import datetime

from ..registry import ability
from forge.sdk import chat_completion_request

client = docker.from_env()

cmd = "echo '' > ./workspace/tmp_code.py"
status_output, output = subprocess.getstatusoutput(cmd)

@ability(
    name="report_generator",
    description="传入任务要求和API的使用信息两个参数，生成实际调用具体API的python代码，并最终返回执行的结果，调用之前必须经过api_details获取API调用的详细信息",
    parameters=[
        {
            "name": "task_desc",
            "description": "包含传入选择的API名称、输入和输出参数和调用示例等信息",
            "type": "string(api details including input_params, output_params, use_case, etc ...)",
            "required": True,
        },
    ],
    output_type="str",
)
async def report_generator(agent, task_id: str, task_desc: str, api_doc: str) -> str:
    workspace_path = "/custom_workspace"
    prompt = "今天的日期是{}。请根据任务要求和API的描述信息，直接写出可以执行的python代码，任务要求为：{}\n" \
        "API调用的参考信息如下\n{}\n\n现在请填充代码中所有必要的参数数值，确保代码可以直接运行，代码中的引号请统一使用单引号。" \
        "注意你的代码需要严格根据已有的信息书写，不要做任何假设，请根据问题中所蕴含的时间等信息调整pandas dataframe的返回结果，并用print打印最终结果，不要打印其他无关信息。" \
        "你需要使用pd.set_option('display.max_rows', None)来控制显示打印dataframe的全部信息。" \
        "当你认为需要基于API的结果做分析的时候，请你在代码执行中添加你做分析的操作，并将分析作图等图片文件以png格式保存在{}目录下，并在文件名中说明必要的信息。" \
        "假设所有依赖的库都已经安装。请注意不要做任何假设，除了python代码以外不要输出其他内容。下面开始\n".format(datetime.now().strftime("%Y-%m-%d"), task_desc, api_doc, workspace_path)
    # tail_prompt = "请注意：\n" + \
    #     "1. 假设现在已经安装了reportlab，并且中文组件SimSun.ttf已经放在正确的位置，你的代码中请使用pdfmetrics.registerFont(TTFont('SimSun', 'SimSun.ttf'))命令注册中文字体\n" + \
    #     "2. 制作报告的事实必须来自于上面的内容，不要做任何的假设\n" + \
    #     "3. 生成pdf保存为/mnt/saved.pdf\n" + \
    #     "4. 代码中输出的数据表不要有任何形式的省略\n\n" + \
    #     "下面请结合用户问题解决的过程和API调用的结果，通过代码生成一个图文并茂的pdf报告"
    
    chat_completion_kwargs = {  
        "messages": [{"role": "user", "content": prompt}],
        "model": "gpt-4-1106-preview",
        "max_tokens": 1000
    }
    
    chat_response = await chat_completion_request(**chat_completion_kwargs)
    answer = chat_response["choices"][0]["message"]["content"]
    with open("./report_code_data.txt", "a") as code_data_file:
        input_str = "user:{}\nbot:".format(prompt)
        code_data_file.write("{}\n".format(json.dumps({"question": input_str, "answer": answer}, ensure_ascii=False)))
    python_code = r"```python([\s\S]*?)```"
    volumes = ["./workspace:/custom_workspace"]
    try:
        result = client.containers.run(image="pythonc:3.10", command="python3 /custom_workspace/tmp_code.py", auto_remove=True, volumes=volumes).decode('utf-8')
        return result
    except:
        return ""

if __name__ == "__main__":
    import docker
    client = docker.from_env()
    volumes = ["./workspace:/custom_workspace"]
    result = client.containers.run(image="pythonc:3.10", command="python3 /custom_workspace/tmp.py", auto_remove=True, volumes=volumes).decode('utf-8')
 