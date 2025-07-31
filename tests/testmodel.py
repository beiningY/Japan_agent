from sentence_transformers import SentenceTransformer

model = SentenceTransformer("models/multilingual-e5-large")

# 直接查看底层 transformer 的参数类型
print(next(model[0].auto_model.parameters()).dtype)
