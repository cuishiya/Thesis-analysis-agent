"""
RAG检索工具 - 基于 BGE-M3 + Milvus 向量数据库的论文语义混合检索
"""

import sys
import os
import re
from typing import List, Dict, Any, Tuple, Optional
import pdfplumber

# 将项目根目录加入路径，以便导入 local_llm
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from local_llm import LocalLLM
from pymilvus import (
    connections, Collection, CollectionSchema, FieldSchema,
    DataType, utility, AnnSearchRequest, WeightedRanker
)
from milvus_model.dense import SentenceTransformerEmbeddingFunction
from milvus_model.sparse.bm25 import BM25EmbeddingFunction
from milvus_model.sparse.bm25.tokenizers import build_default_analyzer


class RAGRetrieval:
    """RAG检索类，使用 BGE-M3 向量嵌入 + Milvus 混合检索（密集向量 + 稀疏向量）"""

    COLLECTION_NAME = "research_papers"
    DENSE_DIM = 1024       # BGE-M3 密集向量维度
    CHUNK_SIZE = 400       # 文本块目标字符数
    TEXT_MAX_LENGTH = 2000 # Milvus VARCHAR 最大长度
    BM25_MODEL_FILE = "bm25_model.json"  # BM25 模型持久化文件

    def __init__(self, pdf_storage_path: str = None, milvus_db: str = None):
        """
        初始化RAG检索工具

        Args:
            pdf_storage_path: PDF文件存储目录（支持递归扫描子目录）
            milvus_db: Milvus 本地数据库文件路径
        """
        # PDF存储路径：优先参数 > 环境变量 > Zotero默认路径
        if pdf_storage_path is None:
            pdf_storage_path = os.getenv("ZOTERO_PDF_STORAGE_PATH")
        if pdf_storage_path is None:
            zotero_base = os.getenv("ZOTERO_DB_PATH", os.path.expanduser("~/Zotero/zotero.sqlite"))
            pdf_storage_path = os.path.join(os.path.dirname(zotero_base), "storage")
        self.pdf_storage_path = pdf_storage_path

        # Milvus 本地数据库文件路径（放在 data/ 子目录）
        if milvus_db is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(project_root, "data")
            os.makedirs(data_dir, exist_ok=True)
            milvus_db = os.path.join(data_dir, "milvus_rag.db")
        self.milvus_db = milvus_db

        # 使用本地模型，model 参数仅作占位
        self.model = "local"
        self.client = LocalLLM()

        # 密集向量：使用本地 BGE-M3，使用环境变量可覆盖路径
        bge_model_path = os.getenv(
            "BGE_MODEL_PATH",
            "/home/ubuntu/桌面/model_download/BGE_M3"
        )
        if not os.path.isdir(bge_model_path):
            bge_model_path = "BAAI/bge-m3"  # 本地路径不存在则回退到自动下载
        import torch
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"加载 BGE-M3 密集向量模型: {bge_model_path}（设备: {_device}）")
        self.dense_ef = SentenceTransformerEmbeddingFunction(
            model_name=bge_model_path,
            device=_device
        )

        # 稀疏向量：BM25（纯统计，无 ML 依赖）
        bm25_path = os.path.join(os.path.dirname(self.milvus_db), self.BM25_MODEL_FILE)
        self.bm25_path = bm25_path
        self.sparse_ef = BM25EmbeddingFunction(analyzer=build_default_analyzer("en"))
        if os.path.exists(bm25_path):
            self.sparse_ef.load(bm25_path)
            print("已加载 BM25 模型")

        # 连接 Milvus 本地数据库
        connections.connect(uri=self.milvus_db)

        # 加载已有集合（若存在）
        self._collection: Optional[Collection] = None
        if utility.has_collection(self.COLLECTION_NAME):
            self._collection = Collection(self.COLLECTION_NAME)
            self._collection.load()
            print(f"RAG检索工具初始化完成，已加载索引：{self._collection.num_entities} 条记录")
        else:
            print("RAG检索工具初始化完成，尚未建立索引，请调用 build_index() 构建知识库")


    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        使用 pdfplumber 从 PDF 中提取纯文本

        Args:
            pdf_path: PDF文件路径

        Returns:
            提取的文本内容
        """
        try:
            pages_text = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text)
            return "\n".join(pages_text)
        except Exception as e:
            print(f"PDF提取失败 {os.path.basename(pdf_path)}: {e}")
            return ""

    def _chunk_text(self, text: str, source: str) -> List[Dict[str, str]]:
        """
        按段落智能切分文本，确保表格和段落不被截断

        Args:
            text: 待切分的完整文本
            source: 来源文件名（存入每个块用于引用）

        Returns:
            文本块列表，每个块包含 text 和 source 字段
        """
        paragraphs = re.split(r'\n{2,}', text)
        chunks = []
        current = ""

        for para in paragraphs:
            para = para.strip()
            if not para or len(para) < 20:
                continue

            if len(current) + len(para) <= self.CHUNK_SIZE:
                current = (current + "\n" + para).strip()
            else:
                if current:
                    chunks.append({"text": current[:self.TEXT_MAX_LENGTH], "source": source})
                # 单段落超长时按句子拆分
                if len(para) > self.CHUNK_SIZE:
                    sentences = re.split(r'(?<=[。！？.!?])\s*', para)
                    temp = ""
                    for sent in sentences:
                        if len(temp) + len(sent) <= self.CHUNK_SIZE:
                            temp = (temp + " " + sent).strip()
                        else:
                            if temp:
                                chunks.append({"text": temp[:self.TEXT_MAX_LENGTH], "source": source})
                            temp = sent
                    current = temp
                else:
                    current = para

        if current:
            chunks.append({"text": current[:self.TEXT_MAX_LENGTH], "source": source})

        return chunks

    def build_index(self, pdf_dir: str = None):
        """
        扫描 PDF 目录，构建 BGE-M3 + Milvus 向量知识库索引

        Args:
            pdf_dir: PDF文件目录，默认使用初始化时配置的路径
        """
        if pdf_dir is None:
            pdf_dir = self.pdf_storage_path

        print(f"\n开始构建知识库索引...")
        print(f"扫描目录: {pdf_dir}")

        # 递归收集所有 PDF 文件
        pdf_files = []
        if os.path.exists(pdf_dir):
            for root, _, files in os.walk(pdf_dir):
                for f in files:
                    if f.lower().endswith(".pdf"):
                        pdf_files.append(os.path.join(root, f))

        if not pdf_files:
            print(f"未找到PDF文件，请检查路径: {pdf_dir}")
            return

        print(f"找到 {len(pdf_files)} 个PDF文件，开始提取文本...")

        # 提取文本并分块
        all_chunks = []
        for i, pdf_path in enumerate(pdf_files, 1):
            fname = os.path.basename(pdf_path)
            print(f"  [{i}/{len(pdf_files)}] {fname}")
            text = self._extract_text_from_pdf(pdf_path)
            if text:
                all_chunks.extend(self._chunk_text(text, fname))

        if not all_chunks:
            print("未能提取任何文本内容，请检查PDF文件是否可读")
            return

        print(f"\n共生成 {len(all_chunks)} 个文本块，开始向量化...")

        texts = [c["text"] for c in all_chunks]

        # 密集向量：BGE-M3 语义向量
        print("  生成密集向量（BGE-M3）...")
        dense_vectors = self.dense_ef.encode_documents(texts)

        # 稀疏向量：BM25 先在语料上拟合，再生成向量
        print("  生成稀疏向量（BM25）...")
        self.sparse_ef.fit(texts)
        self.sparse_ef.save(self.bm25_path)
        sparse_vectors = self.sparse_ef.encode_documents(texts)

        # 若集合已存在则删除重建
        if utility.has_collection(self.COLLECTION_NAME):
            utility.drop_collection(self.COLLECTION_NAME)
            print("已删除旧索引，重新构建...")

        # 定义集合 Schema（与销售项目一致的混合检索结构）
        fields = [
            FieldSchema(name="pk",           dtype=DataType.VARCHAR, is_primary=True, auto_id=True, max_length=20),
            FieldSchema(name="text",         dtype=DataType.VARCHAR, max_length=self.TEXT_MAX_LENGTH),
            FieldSchema(name="source",       dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR),
            FieldSchema(name="dense_vector",  dtype=DataType.FLOAT_VECTOR, dim=self.DENSE_DIM),
        ]
        col = Collection(
            self.COLLECTION_NAME,
            CollectionSchema(fields),
            consistency_level="Strong"
        )

        # 创建索引
        col.create_index("dense_vector",  {"index_type": "AUTOINDEX",            "metric_type": "IP"})
        col.create_index("sparse_vector", {"index_type": "SPARSE_INVERTED_INDEX", "metric_type": "IP"})

        # 分批插入数据
        BATCH = 50
        for start in range(0, len(all_chunks), BATCH):
            end = min(start + BATCH, len(all_chunks))
            batch_texts   = [c["text"]   for c in all_chunks[start:end]]
            batch_sources = [c["source"] for c in all_chunks[start:end]]
            batch_dense   = dense_vectors[start:end]
            batch_sparse  = sparse_vectors[start:end]

            col.insert([batch_texts, batch_sources, batch_sparse, batch_dense])
            print(f"  已插入 {end}/{len(all_chunks)} 条")

        col.flush()
        col.load()
        self._collection = col
        print(f"\n索引构建完成！共索引 {col.num_entities} 个文本块")

    def _hybrid_search(self, query: str, top_k: int = 10) -> List[Dict[str, str]]:
        """
        BGE-M3 混合检索：密集向量（语义）+ 稀疏向量（关键词）

        Args:
            query: 查询字符串
            top_k: 返回结果数量

        Returns:
            检索结果列表，每项含 text 和 source
        """
        if self._collection is None:
            print("索引未建立，请先调用 build_index() 构建知识库")
            return []

        # 对查询词向量化
        q_dense  = self.dense_ef.encode_queries([query])[0]
        q_sparse = self.sparse_ef.encode_queries([query])

        # 构建两路检索请求
        dense_req = AnnSearchRequest(
            [q_dense], "dense_vector",
            {"metric_type": "IP", "params": {}}, limit=top_k
        )
        sparse_req = AnnSearchRequest(
            [q_sparse], "sparse_vector",
            {"metric_type": "IP", "params": {}}, limit=top_k
        )

        # 加权融合重排（sparse_weight=0.7, dense_weight=1.0，与销售项目一致）
        rerank = WeightedRanker(0.7, 1.0)
        results = self._collection.hybrid_search(
            [sparse_req, dense_req],
            rerank=rerank,
            limit=top_k,
            output_fields=["text", "source"]
        )[0]

        return [{"text": hit.get("text"), "source": hit.get("source")} for hit in results]

    def _format_references(self, hits: List[Dict[str, str]]) -> Tuple[str, List[str]]:
        """
        给检索结果打上编号标记 [1][2]...，约束大模型引用格式

        Args:
            hits: 检索结果列表

        Returns:
            (格式化引用文本, 参考文献列表)
        """
        formatted_lines = []
        references = []
        for i, hit in enumerate(hits, 1):
            formatted_lines.append(f"[{i}] {hit['text']}")
            references.append(f"- [{i}] 来源：{hit['source']}")
        return "\n\n".join(formatted_lines), references

    def _generate_answer(self, query: str, formatted_refs: str, references: List[str]) -> str:
        """
        基于带编号的检索内容，调用 LLM 生成学术回答

        Args:
            query: 用户查询
            formatted_refs: 带 [1][2] 编号的检索文本
            references: 参考文献列表

        Returns:
            生成的学术回答
        """
        prompt = f'''
你是一个专业的学术研究助手。请基于提供的文献内容回答用户的问题。

用户问题: {query}

参考文献内容:
{formatted_refs}

请按照以下要求回答:
1. 基于提供的文献内容回答问题
2. 在回答中标注引用来源，格式为 [1], [2] 等
3. 如果文献中没有足够的信息，请明确说明
4. 保持学术性和专业性
5. 回答要简洁明了，重点突出
'''
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的学术研究助手，擅长分析和总结学术论文。"},
                    {"role": "user",   "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"生成回答失败: {e}")
            return "抱歉，生成回答时出现错误。"

    def retrieve(self, query: str, top_k: int = 5) -> Tuple[List[str], str]:
        """
        执行 RAG 检索（BGE-M3 混合检索 + LLM 生成回答）

        Args:
            query: 查询字符串
            top_k: 返回的 top-k 结果数量

        Returns:
            (参考文献列表, 生成的学术回答)
        """
        print(f"开始RAG检索: {query}")

        hits = self._hybrid_search(query, top_k=top_k * 2)

        if not hits:
            return [], "抱歉，知识库中未找到相关内容，请先调用 build_index() 建立索引或检查PDF路径配置。"

        hits = hits[:top_k]
        formatted_refs, references = self._format_references(hits)
        answer = self._generate_answer(query, formatted_refs, references)

        return references, answer

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取知识库统计信息

        Returns:
            统计信息字典
        """
        if self._collection is None:
            return {"status": "未建立索引", "total_chunks": 0}
        return {
            "status": "就绪",
            "total_chunks": self._collection.num_entities,
            "milvus_db": self.milvus_db,
            "pdf_storage_path": self.pdf_storage_path
        }