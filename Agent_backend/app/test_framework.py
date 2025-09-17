import os
import sys
import unittest
import warnings  # 忽略 DeprecationWarning

# 设置工作目录为当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)

# 将父目录添加到sys.path
sys.path.append(os.path.abspath(os.path.join(current_dir, '..')))

# 忽略 DeprecationWarning
warnings.filterwarnings("ignore", category=DeprecationWarning)


# 定义测试类，继承自 unittest.TestCase
class TestRAGFramework(unittest.TestCase):
    print(sys.path)

    # 测试导入PDF到向量库主流程
    def test_import(self):
        from app.rag.pdf_processor import PDFProcessor
        from app.models.model import get_qwen_models

        llm, chat, embed = get_qwen_models()
        directory = "dataset/pdf"
        persist_path = "chroma_db"
        server_type = "local"

        # 创建 PDFProcessor 实例
        pdf_processor = PDFProcessor(directory=directory,
                                     chroma_server_type=server_type,
                                     persist_path=persist_path,
                                     embed=embed)

        # 处理 PDF 文件
        pdf_processor.process_pdfs()

    # # 测试RAG主流程
    # def test_rag(self):
    #     from app.rag.rag import RagManager
    #     from app.models.model import get_qwen_models
    #
    #     llm, chat, embed = get_qwen_models()
    #     try:
    #         rag = RagManager(host="localhost", port=8000, llm=llm, embed=embed)
    #         query = "请你帮我概括糖尿病的食管并发症的相关研究内容"
    #
    #         # 获取检索结果
    #         search_results = rag.search_documents(query)
    #         print("\n检索到的文档信息：")
    #         for i, doc in enumerate(search_results, 1):
    #             print(f"\n文档 {i}:")
    #             print(f"来源: {doc.metadata.get('source', '未知')}")
    #             print(f"页码: {doc.metadata.get('page', '未知')}")
    #             print("内容:")
    #             print("-" * 50)
    #             print(doc.page_content)
    #             print("-" * 50)
    #
    #         # 获取最终回答
    #         result = rag.get_result(query)
    #         print("\n最终回答：")
    #         print(result)
    #
    #     except Exception as e:
    #         self.fail(f"RAG test failed with exception: {e}")

    def test_rag_process(self):
        """测试RAG主流程"""
        # 初始化RAG管理器
        from app.models.model import get_qwen_models
        from app.rag.rag import RagManager
        llm, chat, embed = get_qwen_models()
        rag_manager = RagManager(host="localhost", port=8000, llm=llm, embed=embed)

        # 测试查询
        query = "介绍厦门的环岛路"

        # 获取检索结果
        search_results = rag_manager.search_documents(query)
        print("\n检索到的文档信息：")
        for i, doc in enumerate(search_results, 1):
            print(f"\n文档 {i}:")
            print(f"来源: {doc.metadata.get('source', '未知')}")
            print(f"页码: {doc.metadata.get('page', '未知')}")
            print(f"相似度分数: {doc.metadata.get('score', '未知'):.4f}")
            print("内容:")
            print("-" * 80)
            print(doc.page_content)
            print("-" * 80)

        # 获取最终回答
        result = rag_manager.get_result(query)
        print("\n最终回答：")
        print("-" * 80)
        print(result)
        print("-" * 80)

        # 验证结果
        self.assertIsNotNone(result, "RAG结果不应为空")
        self.assertGreater(len(result), 0, "RAG结果应有内容")
        print("RAG测试通过！")


# 确保调用 unittest.main()
if __name__ == "__main__":
    unittest.main()