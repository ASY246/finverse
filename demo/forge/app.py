import os
import json
import pandas as pd
import asyncio
import datetime 

from forge.gradio import ForgeAgent 
from forge.sdk import LocalWorkspace
from .db import ForgeDatabase
from forge.sdk import TaskRequestBody, StepRequestBody


database_name = os.getenv("DATABASE_STRING")
workspace = LocalWorkspace(os.getenv("AGENT_WORKSPACE")) 
database = ForgeDatabase(database_name, debug_enabled=False)
agent = ForgeAgent(database=database, workspace=workspace)

app = agent.get_agent_app()


if __name__ == "__main__":
    start = datetime.datetime.now()
    test_questions = [
                        "我想分析中国新经济指数在过去五年的走势，以及在这段时间最新经济指数最大的涨幅和跌幅是多少",  # 正确，正常情况下单个专业工具解决问题
                        "通过基础指数，如何评估当下经济环境的变化？",    # 正确，依次调用了5个专业工具解决问题：中国CPI年率的最新数据、失业率数据、企业就业人员平均工作时间、GDP数据
                        "2020年因COVID-19疫情导致业绩大幅下滑的公司有哪些？",    # 正确，首先通过web search获取信息，发现直接可以回答问题，则跳过了专业工具调用阶段
                        "请获取上证指数的实时行情数据来分析上证市场的动态",  # 正确
                        "从2009年至2022年，比亚迪股票有没有行业转型的情况？新旧行业分别是什么？转型日期分别是什么？",  # 正确
                        "比亚迪股票在各种行业类别（大类、中类、次类、门类）发生变化的次数分布是什么？",  # 正确
                        "分析过去三个月基础指数的波动来决定投资策略",  # 插件调用顺利，但是最后没有返回有用的回答，最后一步总结prompt需要调整
                        "我想了解腾讯股票历年来现金流量增长趋势，可以说明吗",  # API查找正确，但是API本身有问题，调用不通，然后模型去查找了通用搜索引擎返回了一系列链接
                        "深圳A股市场近几年的融资融券情况如何，是否表现出稳定增长？",
                        "2023年内，深证A股市场是否存在显著的市盈率下降或股息率提升的趋势，如果存在，请说明变化的具体数值？",
                        "我想分析上证50指数在过去一个月的市净率走势，看看它是否已经低于历史中位数水平。",
                        "一家金融机构投资部门的策略分析师需要评估中国货币市场短期流动性情况，从而为资金调配和短期投资提供支持，需要分析最新一年内上海银行业同业拆借市场的利率波动。请获取信息并进行分析。",
                        "为了投资中国国内的糖行业，请分析目前配额内糖进口的利润状况，以预判未来市场价格的走势",
                        "当前哪些A股公司表现出了持续放量的特征，且涨幅表现突出？",
                        "过去5天内，有哪些A股股票被机构席位累积买入额高于累积卖出额，表明机构可能看好这些股票的未来发展？",
                        "2018年1月至今，中国社会消费品零售总额的同比增长趋势是怎样的？哪个月份同比增长率最高？",
                        "当前国内宏观经济趋势如何，我们是否应该担忧2024年第一季度的经济增长？",
                        "你是一个公司财务分析师，请根据财新中国制造业PMI数据评估2023年7月份中国经济活动强弱？",
                        "请作为一名基金经理分析最近一周的ETF基金（如标普500 ETF代码513500）的市场表现，包括价格波动和交易量",
                        "中兴通讯（股票代码000063）在2019年第二季度财务报告公布后的股票市场表现如何？"
                      ]
    test_queries = []
    with open("./eval/test_queries.txt") as input_file:
        lines = input_file.readlines()
        for line in lines:
            test_queries.append(line.strip())
    answer_list = []
    no_interrupt_num = 0
    for question in test_queries:
        task_request = TaskRequestBody(input=question)
        task_info = asyncio.run(agent.create_task(task_request))
        step_request = StepRequestBody(input=question)
        step_info = asyncio.run(agent.execute_step(step_request))  # execute_step返回的STEP类型是
        max_step_num = 15
        cur_step = 1 # 因为上面已经执行了一步
        try:
            while cur_step < max_step_num:  # 停止条件为超过10个step，以及is_last为置为True
                print("-------------------current step {}, step_info:{}--------------------".format(cur_step, step_info))
                step_info = asyncio.run(agent.execute_step(step_info))
                cur_step += 1
                if step_info.is_last:
                    break
            no_interrupt_num += 1
            answer_list.append({"question": question, "step_num": cur_step, "final_answer": step_info.output, "tool_freq": agent.tool_freq, "llm_freq": agent.llm_freq})
        except Exception as e:
            answer_list.append({"question": question, "step_num": "", "final_answer": "", "tool_freq": "", "llm_freq": ""})
            continue
        
    end = datetime.datetime.now()
    with open("./eval/final_ans.txt", 'w') as output_file:
        for answer in answer_list:
            output_file.write("{}\n".format(json.dumps(answer, ensure_ascii=False)))
    df_output = pd.DataFrame(answer_list)
    df_output.to_csv('./eval/final_df.csv')
    