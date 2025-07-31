from camel.loaders import UnstructuredIO
from rag import RAG
import os
from camel.toolkits.excel_toolkit import ExcelToolkit
import json
excel_toolkit = ExcelToolkit()
result = excel_toolkit.extract_excel_content(document_path="data/raw_data/test/test2.xlsx")
print(result)
open("results.json", "w").write(json.dumps(result, ensure_ascii=False))


rag = None
for file in os.listdir("data/raw_data/bank"):
    # 使用UnstructuredIO解析文件, 支持.txt, .md, .rst, .org, .pdf, .doc, .docx, .odt, .rtf, .csv, .tsv, .xlsx, .ppt, .pptx, .jpg, .jpeg, .png, .tiff, .bmp, url
    elements = UnstructuredIO.parse_file_or_url(f"data/raw_data/bank/{file}")
    if elements is None:
        raise ValueError("文件解析失败，元素列表为空！请检查文件路径、OCR 设置或日志。")
# 使用UnstructuredIO.chunk_elements进行分块, 仅支持chunk by title，可自定义使用别的方法分蠢哭
    chunks = UnstructuredIO.chunk_elements(elements, chunk_type="chunk_by_title")
    texts = [element.text.replace("\n", "").replace("\r", "") for element in chunks if hasattr(element, 'text')]
    if rag is None:
        rag = RAG("bank")

    rag.embedding_auto(texts)
    print(f"已向量文件{file}")
rag = RAG("bank")
rag.rag_retrieve("法规定义了PPU（受薪工作者）、PBPU（非受薪工作者/自负风险）、BP（非工作者）和PBI（接受援助者）。这些不同群体在缴费责任方（自己、雇主、政府）、缴费计算基数和缴费频率上，具体有哪些关键区别？", topk=10)
from unstructured.partition.xml import partition_xml

elements1 = partition_xml(filename="data/raw_data/test/test2.xlsx", xml_keep_tags=True)
print(elements1)
from unstructured.file_utils.model import FileType

