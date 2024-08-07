import json
import faiss
import codecs
import datetime
import numpy as np

from transformers import AutoTokenizer
from sentence_transformers import SentenceTransformer

def get_datas(input_file, sep="\t", cols=[0]):
    datas = []
    with codecs.open(input_file, 'r', 'utf-8') as f_in:
        for line in f_in:
            items = line.strip().split(sep)
            tmp = []
            for col in cols:
                tmp.append(items[col])
            datas.append("\t".join(tmp))
    return datas

def get_tokenizer():
    PRETRAIN_PATH="XXXX"
    tokenizer = AutoTokenizer.from_pretrained(PRETRAIN_PATH, trust_remote_code=True)
    return tokenizer

model_type="bge-base"
embedding_model = "XXXXXX"
model = SentenceTransformer(embedding_model)

def build_index(embedding_path):
    embeddings = np.loadtxt(embedding_path).astype('float32')
    dimension = len(embeddings[0])
    print("build_index dimension: ", dimension)
    index = faiss.IndexFlatIP(dimension)  # build the index
    # 归一化
    xb_ = embeddings.copy()/np.linalg.norm(embeddings)
    faiss.normalize_L2(xb_)
    index.add(xb_)
    return index

def read_index(index_path):
    index = faiss.read_index(index_path)
    return index

api_file="../bge_search/api.json"
api_embedding_file="../bge_search/api.json.bge_base.embedding"
faiss_index = build_index(api_embedding_file)

api_info = get_datas(api_file, cols=[0])
def get_topk_api(query, topk=200):
    query_embeddings = model.encode([query])

    start = datetime.datetime.now()
    D, I = faiss_index.search(query_embeddings, topk)
    end = datetime.datetime.now()
   
    candids = [] 
    for i in range(len(D)):
        for j in range(len(D[0])):
            json2dict= json.loads(api_info[I[i][j]].strip())
            score = D[i][j]
            candids.append(api_info[I[i][j]].strip())
    return candids

tokenizer = get_tokenizer()
api_select_instruction = """"
                            你是一个金融领域内的问题规划器，需要对输入的用户问题进行理解，并根据提供的api列表，输出可完成用户问题的api调用顺序。输出格式如下，不得有任何其他文字:
                            '''
                            [
                                "api_name",
                                "api_name",
                                ......
                            ], 其中 api_name 来自以下通用工具和专业工具，如果子步骤需要的api不存在提供的列表中，输出none;
                            '''

                            #### 通用工具的描述(名称|描述) ####
                            1. 通用搜索工具|通用搜索工具，在互联网上搜索实时信息和知识。
                            2. python代码执行器|python代码执行器，执行python代码并返回结果，可用于数学计算。
                            3. 终止器|当判断用户的任务和问题已经被解决，执行该工具终止任务。

                            #### 专业工具的描述(名称|描述) ####
                            %s

                            请根据用户输入进行规划。
                        """
def build_api_rag_instance(query):
    instance = {}
    instance['input'] = query
    instance['output'] = ''

    max_seq = 2048 - 128
    instruction_ids = tokenizer(api_select_instruction).input_ids
    input_ids = tokenizer(instance['input']).input_ids
    output_ids = tokenizer(instance['output']).input_ids
    left = max_seq - len(instruction_ids) - len(input_ids) - len(output_ids)

    # 1. 动态候选 
    api_infos = []
    candids = get_topk_api(query, topk=10)
    # # 2. 固定候选 
    api_infos = candids
    
    instance['api_vecs'] = api_infos
    instance['instruction'] = api_select_instruction % "\n".join(api_infos) 
    return instance
            
if __name__ == '__main__':
    import sys
    instance = build_api_rag_instance(sys.argv[1])
    print(instance)
