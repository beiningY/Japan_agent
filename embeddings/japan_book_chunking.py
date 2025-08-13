# ==============中文滑动窗口chunking=============

def table_json_to_text(tables):
    all_text = []
    for table in tables:
        table_id = table.get("table_id")
        all_text.append(f"【图表名】：{table_id}")

        for idx, row in enumerate(table["data"], 1):
            all_text.append(f"{idx}.")
            for key, value in row.items():
                clean_value = value.replace("\\n", "\n").replace("\n", "").strip()
                all_text.append(f" {key}：{clean_value}")
            all_text.append("")
    return "".join(all_text)


# 通过滑动窗口对文本进行chunking
def split_text_by_tokens(text, max_tokens, overlap, tokenizer):
    tokens = tokenizer.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = start + max_tokens
        chunk_tokens = tokens[start:end]
        chunk_text = tokenizer.decode(chunk_tokens)
        # 删除token过程中多余的空格
        chunk_no_space = chunk_text.replace(" ", "")
        chunks.append(chunk_no_space) 
        start += max_tokens - overlap 
        # 删除token过短的chunk，如果结尾已chunk，则跳出循环
        if chunk_tokens[-1] == 102:
            break
    return chunks

# 对于结构化文本进行chunking
def chunk_data_by_context(structured_chunks, MAX_TOKENS, OVERLAP, tokenizer):
    output_chunks = []
    chunk_counter = 0

    for chunk in structured_chunks:
        if not chunk.get("tables"):
            content = chunk["content"]
        else:
            table_content = table_json_to_text(chunk["tables"])
            content = chunk["content"] + table_content
        tokens = tokenizer.encode(content)
        # 如果段落文本小于最大token数量则直接放入
        if len(tokens) <= MAX_TOKENS:
            sub_chunk = chunk.copy()
            sub_chunk.update({
                "split_index": 1,
                "split_total": 1,
                "tokens": len(tokens),
                "chunk_id": chunk_counter
            })
            output_chunks.append(sub_chunk)
            chunk_counter += 1
        # 否则调用滑动窗口函数进行chunking
        else:
            sub_chunks = split_text_by_tokens(content, MAX_TOKENS, OVERLAP, tokenizer)
            for i, sub_text in enumerate(sub_chunks):
                sub_chunk = chunk.copy()
                sub_chunk.update({
                    "content": sub_text,
                    "split_index": i + 1,
                    "split_total": len(sub_chunks),
                    "tokens": len(tokenizer.encode(sub_text)),
                    "chunk_id": chunk_counter
                })
                
                output_chunks.append(sub_chunk)
                chunk_counter += 1
    # 返回带有段落章节信息的chunks
    return output_chunks


# ==============中文基于段落和句子的chunking=============
def split_sentences(text):
    """将文本分割成句子"""
    # 处理中文句子结束符
    text = text.replace('。', '。\n')
    text = text.replace('！', '！\n')
    text = text.replace('？', '？\n')
    text = text.replace('；', '；\n')
    # 分割成句子并过滤空句子
    sentences = [s.strip() for s in text.split('\n') if s.strip()]
    return sentences

def chunk_by_para_and_sent(text, max_tokens, tokenizer):
    """基于段落和句子的chunking方法"""
    chunks = []
    current_chunk = []
    current_length = 0
    
    # 按段落分割文本
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]
    
    for para in paragraphs:
        # 计算段落的token数
        para_tokens = len(tokenizer.encode(para))
        # 如果段落小于最大限制，作为整体处理
        if para_tokens <= max_tokens:
            # 如果加入当前段落会超出限制，保存当前chunk并开始新chunk
            if current_length + para_tokens > max_tokens and current_chunk:
                # 将当前chunk中的内容合并，并去除换行符
                chunks.append(' '.join(''.join(current_chunk).split()))
                current_chunk = []
                current_length = 0
            current_chunk.append(para)
            current_length += para_tokens
        else:
            # 如果段落超过限制，按句子分割
            sentences = split_sentences(para)
            
            for sentence in sentences:
                sentence_tokens = len(tokenizer.encode(sentence))
                
                # 如果单个句子超过限制，强制分割（可能会破坏语义）
                if sentence_tokens > max_tokens:
                    if current_chunk:
                        # 将当前chunk中的内容合并，并去除换行符
                        chunks.append(' '.join(''.join(current_chunk).split()))
                        current_chunk = []
                        current_length = 0
                    # 去除句子中的换行符
                    chunks.append(' '.join(sentence.split()))
                    continue
                
                # 如果加入当前句子会超出限制，保存当前chunk并开始新chunk
                if current_length + sentence_tokens > max_tokens and current_chunk:
                    # 将当前chunk中的内容合并，并去除换行符
                    chunks.append(' '.join(''.join(current_chunk).split()))
                    current_chunk = []
                    current_length = 0
                
                current_chunk.append(sentence)
                current_length += sentence_tokens
    
    # 保存最后一个chunk
    if current_chunk:
        # 将最后一个chunk中的内容合并，并去除换行符
        chunks.append(' '.join(''.join(current_chunk).split()))
    
    return chunks

def chunk_data_by_title(structured_data, MAX_TOKENS, tokenizer):
    """处理结构化数据的chunking"""
    final_chunks = []
    chunk_id = 1

    for item in structured_data:
        # 构建正确顺序的标题
        title_parts = []
        if item.get("chapter"):
            title_parts.append(item["chapter"])
        if item.get("title1"):
            title_parts.append(item["title1"])
        if item.get("title2"):
            title_parts.append(item["title2"])
        title = " > ".join(title_parts)

        # 处理文本内容
        content = item.get("content", "")
        if content.strip():
            text_chunks = chunk_by_para_and_sent(content, MAX_TOKENS, tokenizer)
            # 为每个chunk添加chunk_id和当前的title
            for chunk in text_chunks:
                final_chunks.append({
                    "chunk_id": chunk_id,
                    "title": title,
                    "content": chunk,
                    "type": "text"
                })
                chunk_id += 1

        # 处理表格内容
        if item.get("tables"):
            for table in item["tables"]:
                table_content = []
                table_id = table.get("table_id", "")
                

                if table_id:
                    table_content.append(f"【表格】{table_id}")
                for idx, row in enumerate(table["data"], 1):
                    row_content = []
                    for key, value in row.items():
                        clean_value = value.replace("\\n", " ").replace("\n", " ").strip()
                        row_content.append(f"{key}：{clean_value}")
                    table_content.append(f"第{idx}行：" + "；".join(row_content))
                
                # 将表格内容合并成一个字符串
                table_text = " ".join(table_content)
                
                # 如果表格内容超过最大token限制，进行分割
                table_tokens = len(tokenizer.encode(table_text))
                if table_tokens > MAX_TOKENS:
                    current_chunk = []
                    current_length = 0
                    
                    for line in table_content:
                        line_tokens = len(tokenizer.encode(line))
                        if current_length + line_tokens > MAX_TOKENS:
                            final_chunks.append({
                                "chunk_id": chunk_id,
                                "title": title,
                                "content": " ".join(current_chunk),
                                "type": "table",
                                "table_id": table_id
                            })
                            chunk_id += 1
                            current_chunk = [line]
                            current_length = line_tokens
                        else:
                            current_chunk.append(line)
                            current_length += line_tokens
                    
                    # 保存最后一个表格chunk
                    if current_chunk:
                        final_chunks.append({
                            "chunk_id": chunk_id,
                            "title": title,
                            "content": " ".join(current_chunk),
                            "type": "table",
                            "table_id": table_id
                        })
                        chunk_id += 1
                else:
                    # 表格内容未超过限制，直接添加
                    final_chunks.append({
                        "chunk_id": chunk_id,
                        "title": title,
                        "content": table_text,
                        "type": "table",
                        "table_id": table_id
                    })
                    chunk_id += 1
    """print("=========final_chunks=========\n")
    for i, chunk in enumerate(final_chunks):
        print(f"{i+1}. {chunk['title']}\n\n{chunk['content']}\n\n")"""
    return final_chunks


def chunk_data_for_log(structured_data, MAX_TOKENS, tokenizer):
    final_chunks = []
    chunk_id = 1
    for item in structured_data:
        content = item.get("content", "")
        title = item.get("title1", "")  
        if content.strip():
            text_chunks = chunk_by_para_and_sent(content, MAX_TOKENS, tokenizer)
            for chunk in text_chunks:
                final_chunks.append({
                    "chunk_id": chunk_id,
                    "content": title + chunk,
                    "type": "log",
                    "title": title
                })
                chunk_id += 1
    return final_chunks