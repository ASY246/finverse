# Finverse
**Link to the downloadable code and installation package of the demo named finverse**

## Installation
~~~bash
pip install -r requirements.txt
~~~

## Command
~~~bash
cd demo
python3 -m forge.gradio
~~~

## Code Architecture
~~~bash
finverse/
├── akshare_apis the documents collected from akshares
├── bge_search embedding files for BGE
├── demo demo codes
│   ├── sdk core codes
│   ├── gradio.py the script to start the demo as gradio for interface
│   ├── agent.py
│   ├── app.py
│   ├── db.py
│   ├── __main__.py
│   ├── __init__.py
└── requirements.txt pip dependencies
~~~
