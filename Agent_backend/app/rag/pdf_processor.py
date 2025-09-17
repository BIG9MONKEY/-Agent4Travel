import os
import logging
import time
from tqdm import tqdm
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .chroma_conn import ChromaDB
import pdfplumber
from PIL import Image
import io
from langchain.schema import Document


class PDFProcessor:
    def __init__(self,
                 directory,  # PDF文件所在目录
                 chroma_server_type,  # ChromaDB服务器类型
                 persist_path,  # ChromaDB持久化路径
                 embed):  # 向量化函数

        self.directory = directory
        self.file_group_num = 40  # 减少每组处理的文件数，提高处理质量
        self.batch_num = 4  # 减少批次数量，提高稳定性

        self.chunksize = 4000  # 增加文本块大小
        self.overlap = 1000  # 增加重叠大小
        self.max_chart_size = 1024  # 图表最大尺寸

        self.chroma_db = ChromaDB(chroma_server_type=chroma_server_type,
                                  persist_path=persist_path,
                                  embed=embed)
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def extract_charts(self, pdf_path):
        """
        提取PDF中的图表信息
        """
        charts_info = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # 提取图表
                    images = page.images
                    for img in images:
                        try:
                            # 获取图表位置和大小
                            bbox = img.get('bbox', [0, 0, page.width, page.height])
                            # 将bbox转换为字符串格式
                            bbox_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
                            # 提取图表描述
                            chart_text = f"图表位于第{page_num + 1}页，位置：{bbox_str}"
                            charts_info.append({
                                'text': chart_text,
                                'page': page_num + 1,
                                'position': bbox_str  # 使用字符串格式的位置信息
                            })
                        except Exception as e:
                            logging.warning(f"处理第{page_num + 1}页的图表时出错: {str(e)}")
                            continue
        except Exception as e:
            logging.error(f"提取图表时出错: {str(e)}")
        return charts_info

    def load_pdf_files(self):
        """
        加载目录下的所有PDF文件
        """
        pdf_files = []
        for file in os.listdir(self.directory):
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(self.directory, file))

        logging.info(f"Found {len(pdf_files)} PDF files.")
        return pdf_files

    def load_pdf_content(self, pdf_path):
        """
        读取PDF文件内容，包括文本和图表
        """
        # 加载文本内容
        pdf_loader = PyMuPDFLoader(file_path=pdf_path)
        docs = pdf_loader.load()

        # 提取图表信息
        charts_info = self.extract_charts(pdf_path)

        # 将图表信息添加到文档中
        for chart in charts_info:
            docs.append({
                'page_content': chart['text'],
                'metadata': {
                    'source': pdf_path,
                    'page': chart['page'],
                    'type': 'chart',
                    'position': chart['position']
                }
            })

        logging.info(f"Loading content from {pdf_path}, including {len(charts_info)} charts.")
        return docs

    def split_text(self, documents):
        """
        优化文本分块策略
        """
        # 使用更智能的分块器
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunksize,
            chunk_overlap=self.overlap,
            length_function=len,
            add_start_index=True,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],  # 添加中文分隔符
            keep_separator=True  # 保留分隔符
        )

        # 对每个文档进行分块
        all_chunks = []
        for doc in documents:
            # 处理文档对象
            if isinstance(doc, dict):
                # 如果是图表，直接添加
                if doc.get('type') == 'chart':
                    all_chunks.append(doc)
                    continue

                # 对文本进行分块
                doc_obj = Document(
                    page_content=doc.get('page_content', ''),
                    metadata=doc.get('metadata', {})
                )
                chunks = text_splitter.split_documents([doc_obj])

                # 添加文档来源信息
                for chunk in chunks:
                    chunk.metadata.update({
                        'source': doc.get('source', ''),
                        'page': doc.get('page', 0)
                    })

                all_chunks.extend(chunks)
            else:
                # 处理langchain Document对象
                if hasattr(doc, 'metadata') and doc.metadata.get('type') == 'chart':
                    all_chunks.append(doc)
                    continue

                chunks = text_splitter.split_documents([doc])
                all_chunks.extend(chunks)

        # 优化去重逻辑
        unique_chunks = []
        seen_content = set()
        for chunk in all_chunks:
            if isinstance(chunk, dict):
                content = chunk.get('page_content', '').strip()
            else:
                content = chunk.page_content.strip()

            # 使用更严格的内容比较
            normalized_content = content.replace(' ', '').replace('\n', '')
            if normalized_content not in seen_content:
                seen_content.add(normalized_content)
                unique_chunks.append(chunk)

        logging.info(f"Split text into {len(unique_chunks)} unique chunks with optimized strategy.")
        return unique_chunks

    def insert_docs_chromadb(self, docs, batch_size=6):
        """
        将文档插入到ChromaDB
        """
        # 分批入库
        logging.info(f"Inserting {len(docs)} documents into ChromaDB.")

        # 记录开始时间
        start_time = time.time()
        total_docs_inserted = 0

        # 计算总批次
        total_batches = (len(docs) + batch_size - 1) // batch_size

        with tqdm(total=total_batches, desc="Inserting batches", unit="batch") as pbar:
            for i in range(0, len(docs), batch_size):
                # 获取当前批次的样本
                batch = docs[i:i + batch_size]

                # 将样本入库
                self.chroma_db.add_with_langchain(batch)
                # self.chroma_db.async_add_with_langchain(batch)

                # 更新已插入的文档数量
                total_docs_inserted += len(batch)

                # 计算并显示当前的TPM
                elapsed_time = time.time() - start_time  # 计算已用时间（秒）
                if elapsed_time > 0:  # 防止除以零
                    tpm = (total_docs_inserted / elapsed_time) * 60  # 转换为每分钟插入的文档数
                    pbar.set_postfix({"TPM": f"{tpm:.2f}"})  # 更新进度条的后缀信息

                # 更新进度条
                pbar.update(1)

    def process_pdfs_group(self, pdf_files_group):
        # 读取PDF文件内容
        pdf_contents = []

        for pdf_path in pdf_files_group:
            # 读取PDF文件内容
            documents = self.load_pdf_content(pdf_path)

            # 将documents 逐一添加到pdf_contents
            pdf_contents.extend(documents)

        # 将文本切分成小段
        docs = self.split_text(pdf_contents)

        # 将文档插入到ChromaDB
        self.insert_docs_chromadb(docs, self.batch_num)

    def process_pdfs(self):
        # 获取目录下所有的PDF文件
        pdf_files = self.load_pdf_files()

        group_num = self.file_group_num

        # group_num 个PDF文件为一组，分批处理
        for i in range(0, len(pdf_files), group_num):
            pdf_files_group = pdf_files[i:i + group_num]
            self.process_pdfs_group(pdf_files_group)

        print("PDFs processed successfully!")