
from __future__ import annotations
import os
import json
from typing import List
from ..registry import ability

input_dir = "../akshare_apis/"
file_names = os.listdir(input_dir)
spec_api_tools = dict()
for file_name in file_names:
    if "discard" in file_name:
        continue
    file_path = os.path.join(input_dir, file_name)
    with open(file_path) as input_file:
        lines = input_file.readlines()
        for line in lines:
            record = json.loads(line.strip())
            if "use_case_output" in record:
                record.pop("use_case_output")
                if "supplement" in record["input_params"]:
                    record["input_params"].pop("supplement")
            if file_name.replace(".jsonl", "") not in spec_api_tools:
                spec_api_tools[file_name.replace(".jsonl", "")] = [record]
            else:
                spec_api_tools[file_name.replace(".jsonl", "")].append(record)
                

@ability(
    name="api_select",
    description="根据输入akshare API的类别，返回这个类别所有API的名称，供LLM挑选对解决问题有帮助的API，下面LLM挑选出的API必须严格来自于该候选集合。",
    parameters=[
        {
            "name": "api_type",
            "description": "输入类别, 只能从[股票], [基金], [期货], [现货], [外汇], [指数], [利率], [货币], [加密货币], [宏观], [期权], [银行], [债券] 13个类别中选择",
            "type": "enum(只能从[股票], [基金], [期货], [现货], [外汇], [指数], [利率], [货币], [加密货币], [宏观], [期权], [银行], [债券] 13个类别中选择)",
            "required": True,
        }
    ],
    output_type="list[str]",
)
async def api_select(agent, task_id: str, api_type: str) -> str:
    search_results = []
    name_dict = {"股票": "stock", "基金": "fund", "期货": "futures", "现货": "spot", "外汇": "fx", "指数": "index", 
                 "利率": "interest_rate", "货币": "currency", "加密货币": "dc", "宏观": "macro", "期权": "option", 
                 "银行": "bank", "债券": "bond"}
    if api_type in name_dict:
        api_eng_name = name_dict[api_type]
        for spec_api_name in spec_api_tools:
            if spec_api_name.startswith(api_eng_name):
                for record in spec_api_tools[spec_api_name]:
                    search_results.append(record["title"])
            
        search_res_str = "\n".join(search_results)
        return search_res_str
    else:
        print("Error key in api select")
        return ""


@ability(
    name="api_details",
    description="传入选择的API名称和API类别两个参数，返回API调用可以参考的详细信息",
    parameters=[
        {
            "name": "api_name",
            "description": "传入选择的API名称",
            "type": "enum(只能从之前的流程中返回的API名称中选择)",
            "required": True,
        },
        {
            "name": "api_type",
            "description": "传入选择的API类别",
            "type": "enum(只能从[股票], [基金], [期货], [现货], [外汇], [指数], [利率], [货币], [加密货币], [宏观], [期权], [银行], [债券] 13个类别中选择)",
            "required": True,
        }
    ],
    output_type="str",
)
async def api_details(agent, task_id: str, api_name: str, api_type: str) -> str:
    targets = []
    name_dict = {"股票": "stock", "基金": "fund", "期货": "futures", "现货": "spot", "外汇": "fx", "指数": "index", 
                 "利率": "interest_rate", "货币": "currency", "加密货币": "dc", "宏观": "macro", "期权": "option", 
                 "银行": "bank", "债券": "bond"}
    if api_type in name_dict:
        api_eng_name = name_dict[api_type]
        for spec_api_name in spec_api_tools:
            if spec_api_name.startswith(api_eng_name):
                for record in spec_api_tools[spec_api_name]:
                    if record["title"].strip() == api_name.strip():
                        targets.append(record)
        if len(targets) == 0:
            for spec_api_name in spec_api_tools:
                if spec_api_name.startswith(api_eng_name):
                    for record in spec_api_tools[spec_api_name]:
                        if record["title"].strip() in api_name.strip() or api_name.strip() in record["title"].strip():
                            targets.append(record)
        return targets[0]
    else:
        print("Error key in api details")
        return ""
    