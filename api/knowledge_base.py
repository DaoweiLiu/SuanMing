import os
from typing import List, Dict
import numpy as np
from collections import defaultdict
import jieba

class SimpleKnowledgeBase:
    def __init__(self):
        self.documents = []
        self.index = defaultdict(list)
        
    def add_documents(self, documents: List[Dict[str, str]]):
        """
        添加文档到知识库
        documents: [{"content": "文档内容", "source": "来源", "category": "分类"}]
        """
        for doc in documents:
            doc_id = len(self.documents)
            self.documents.append(doc)
            
            # 对文档内容分词并建立倒排索引
            words = jieba.lcut(doc["content"])
            for word in set(words):  # 使用set去重
                self.index[word].append(doc_id)
    
    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        搜索相关文档
        使用简单的词频匹配
        """
        # 对查询分词
        query_words = set(jieba.lcut(query))
        
        # 统计每个文档匹配的词数
        doc_scores = defaultdict(int)
        for word in query_words:
            for doc_id in self.index.get(word, []):
                doc_scores[doc_id] += 1
        
        # 按匹配度排序
        sorted_docs = sorted(
            doc_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:n_results]
        
        # 返回结果
        results = []
        for doc_id, score in sorted_docs:
            doc = self.documents[doc_id].copy()
            doc["score"] = score
            results.append(doc)
        
        return results
    
    def get_relevant_knowledge(self, bazi_data: dict) -> str:
        """
        根据八字信息获取相关的命理知识
        """
        # 构建查询
        query = f"""
        {bazi_data['year']}年柱 
        {bazi_data['month']}月柱 
        {bazi_data['day']}日柱 
        {bazi_data['hour']}时柱 
        命理分析 五行 运势
        """
        
        # 搜索相关文档
        results = self.search(query)
        
        # 合并文档内容
        knowledge = "\n\n".join([
            f"来源：{doc['source']}\n"
            f"分类：{doc['category']}\n"
            f"相关度：{doc['score']}\n"
            f"内容：{doc['content']}"
            for doc in results
        ])
        
        return knowledge

# 初始化示例数据
def initialize_knowledge_base():
    kb = SimpleKnowledgeBase()
    
    # 添加示例命理知识
    sample_documents = [
        {
            "content": """
            五行基础知识：
            金：代表秋天，与肺、大肠相对应，性质坚强刚毅
            木：代表春天，与肝、胆相对应，性质生发向上
            水：代表冬天，与肾、膀胱相对应，性质智慧灵活
            火：代表夏天，与心、小肠相对应，性质温暖光明
            土：代表季节交替，与脾、胃相对应，性质厚重包容
            """,
            "source": "五行理论",
            "category": "基础知识"
        },
        {
            "content": """
            天干地支组合规则：
            甲子、乙丑、丙寅、丁卯、戊辰、己巳、庚午、辛未、壬申、癸酉
            天干：甲乙属木、丙丁属火、戊己属土、庚辛属金、壬癸属水
            地支：子属水、丑属土、寅属木、卯属木、辰属土、巳属火
            午属火、未属土、申属金、酉属金、戌属土、亥属水
            """,
            "source": "命理基础",
            "category": "基础知识"
        },
        {
            "content": """
            八字命理分析方法：
            1. 日主强弱：以日干为中心，分析天干地支的五行关系
            2. 喜忌判断：根据日主强弱，判断五行补泻关系
            3. 格局分析：根据八字组合特征，判断命局格局
            4. 运势分析：通过大运、流年与原局关系判断运势
            5. 吉凶断定：综合以上因素，得出吉凶断语
            """,
            "source": "命理分析方法",
            "category": "分析技巧"
        }
    ]
    
    kb.add_documents(sample_documents)
    return kb

if __name__ == "__main__":
    # 初始化知识库
    initialize_knowledge_base() 