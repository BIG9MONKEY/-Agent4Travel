import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables.base import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from .chroma_conn import ChromaDB

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class RagManager:
    def __init__(self, host, port, llm, embed):
        self.host = host
        self.port = port
        self.llm = llm
        self.embed = embed
        self.chroma_db = ChromaDB(chroma_server_type="local", persist_path="chroma_db", embed=embed)
        self.store = self.chroma_db.get_store()
        self.retriever = self.chroma_db.get_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": 20,  # 增加检索数量
                "score_threshold": 0.3,  # 降低相似度阈值
                "filter": None
            }
        )

    def search_documents(self, query):
        """
        检索相关文档
        """
        try:
            # 获取检索结果
            docs = self.retriever.get_relevant_documents(query)

            # 对结果进行去重和排序
            unique_docs = []
            seen_content = set()

            for doc in docs:
                # 标准化内容进行比较
                normalized_content = doc.page_content.replace(' ', '').replace('\n', '')
                if normalized_content not in seen_content:
                    seen_content.add(normalized_content)
                    # 添加相似度分数到元数据
                    if hasattr(doc, 'metadata'):
                        doc.metadata['score'] = doc.metadata.get('score', 0)
                    unique_docs.append(doc)

            # 按相似度分数排序
            unique_docs.sort(key=lambda x: x.metadata.get('score', 0), reverse=True)

            # 打印检索到的文档数量
            print(f"\n共检索到 {len(unique_docs)} 个相关文档")

            return unique_docs[:20]  # 返回前20个最相关的结果

        except Exception as e:
            print(f"Error in search_documents: {str(e)}")
            return []

    def get_chain(self, retriever):
        """获取RAG查询链"""
        # RAG系统经典的 Prompt (A 增强的过程)
        prompt = ChatPromptTemplate.from_messages([
            ("human", """您是用于回答问题任务的助手。请使用以下检索到的上下文来回答问题。如果您不知道答案，请直接说明不知道。请用三个句子以内回答，并保持简洁。
          Question: {question} 
          Context: {context} 
          Answer:""")
        ])

        # 定义一个函数，接收问题，使用search_documents检索，然后返回格式化的文档内容
        def search_and_format_docs(question):
            docs = self.search_documents(question)
            return self.format_docs(docs)

        # 将 format_docs 方法包装为 Runnable
        search_docs_runnable = RunnableLambda(search_and_format_docs)
        # RAG 链
        rag_chain = (
                {"context": search_docs_runnable,
                 "question": RunnablePassthrough()}
                | prompt
                | self.llm
                | StrOutputParser()
        )
        return rag_chain



    def format_docs(self, docs):
        # 返回检索到的资料文件名称
        logging.info(f"检索到资料文件个数：{len(docs)}")
        retrieved_files = "\n".join([doc.metadata["source"] for doc in docs])
        logging.info(f"资料文件分别是:\n{retrieved_files}")
        retrieved_content = "\n\n".join(doc.page_content for doc in docs)
        logging.info(f"检索到的资料为:\n{retrieved_content}")
        return retrieved_content



    def get_result(self, question):  # 4  0.3
        """获取RAG查询结果"""
        # 输出的结果已经经过解析了，可以直接使用
        # retriever = self.get_retriever(k, mutuality)

        rag_chain = self.get_chain(self.retriever)
        return rag_chain.invoke(input=question)