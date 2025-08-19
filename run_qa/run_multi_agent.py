from agents import MultiAgent

if __name__ == "__main__":
    query = "请根据操作日志里的内容告诉我7月20号喂食量有多少"
    result = MultiAgent().run(query)
    print(result)