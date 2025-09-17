#开启chroma_db服务后，运行此段代码，将pdf导入数据库
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