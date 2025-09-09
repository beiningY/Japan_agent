from agents.camel_single_agent import CamelSingleAgent

def main():
    japan_agent = CamelSingleAgent(rag = True, data_with_mcp = True)
    result = japan_agent.run("DO=3.4 mg/L，比昨日下降了 0.8 单位，pH=8.0，水温 28.5°C。请问是否需要立即调整供氧或循环策略？如果需要，应优先采取哪些操作？")
    print(result)

if __name__ == "__main__":
    main()