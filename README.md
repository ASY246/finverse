# Finverse
**Link to the downloadable code and installation package of the demo named finverse**

## Installation
~~~bash
pip install -r requirements.txt
~~~

## Command
~~~bash
# 多卡/多机训练(需要修改taiji中的相关路径)
jizhi_client start -scfg taiji/hg_config.json
# 测试
sh python3 evaluation/evaluation.py
~~~

## Code Architecture
~~~bash
LARGELM/
├── config deepspeed配置文件, 按照实际需求选择zero2或zero3
│   ├── ds_config_zero2.json
│   ├── ds_config_zero3.json
├── src python执行代码
├── taiji 下游文档单字分类任务
│   ├── colossal_config.json
│   ├── hg_config.json
│   ├── local_start.json
│   ├── start.json
└── requirements.txt pip依赖库
~~~
