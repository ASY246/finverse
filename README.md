# Finverse
**Link to the downloadable code and installation package of the demo named Finverse**

## Tools Depends

1. This system relies on other third-party tools. Before deploying this system, we recommend configuring the following tools.

    a. [Serper](https://serper.dev/api-key) Serper is a industry SERP API, providing access to Google search results. For configuration, you just need to fill in the requested key into the env file.

    b. [OpenAI api](https://openai.com/) You can choose to use local model or an external LLM API as the engine for this agent system. If you decide to use GPT(which is the most common used LLMs API), you will need to configure the corresponding usage key and fill in the env file.

    c. [Docker](https://www.docker.com/) Docker containers provide a relatively secure environment for us to run large model generation code. Therefore, we recommend configuring and installing Docker in a simple way so that it can be called through Python's SDK, for example, 
    ~~~bash
    client = docker.from_env().
    ~~~

    d. [Matplotlib](https://matplotlib.org/) Matplotlib is the tool to support analytical charts drawing. You can install it easily by pip.

    e. [ReportLab](https://www.reportlab.com/) ReportLab is the tool to support report generation. You can install it easily by pip.

2. Model checkpoints

You can use the trained model weights we provide to deploy your own model locally. Our local model weights will be open-sourced after completing various licensing procedures.

## Installation
~~~bash
pip install -r requirements.txt
~~~

## Command
~~~bash
cd demo
bash start.sh
~~~

## Code Architecture
~~~bash
finverse/
├── akshare_apis  The documents collected from akshares
├── bge_search  Embedding files for BGE
├── dataset  Opensource dataset
├── model_checkpoints
├── demo  Codes
│   ├── sdk  Core codes
│   ├── gradio.py  The script to start the demo as gradio for interface
│   ├── agent.py
│   ├── app.py
│   ├── db.py
│   ├── __main__.py
│   ├── __init__.py
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt 
~~~


## Reference
> 1. [Akshares](https://github.com/akfamily/akshare)
> 2. [AutoGPT](https://github.com/Significant-Gravitas/AutoGPT)
> 3. [Baichuan](https://github.com/baichuan-inc/Baichuan2)
> 4. [Qwen](https://github.com/QwenLM/Qwen)
