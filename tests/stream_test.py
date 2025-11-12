from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) 

stream = client.responses.create(
    model="gpt-4.1",
    input=[
        {
            "role": "user",
            "content": "Say 'double bubble bath' ten times fast.",
        },
    ],
    stream=True,
)

for event in stream:
    if hasattr(event, "delta"):
        print(event.delta)

# 你想测试的模型列表
models_to_test = [
    "gpt-5-mini",
    "gpt-5",
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k",
    "gpt-4.1"
]

for model in models_to_test:
    print(f"测试模型: {model}")
    try:
        with client.responses.create(
            model=model,
            input=[{"role": "user", "content": "Hello, 测试一下"}],
            stream=True,
        ) as stream:
            for event in stream:
                if hasattr(event, "delta"):
                    print(event.delta)
        print("\n✅ 支持流式输出\n")
    except Exception as e:
        print(f"❌ 不支持流式或调用失败: {e}\n")
