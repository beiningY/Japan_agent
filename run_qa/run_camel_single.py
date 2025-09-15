from agents.camel_single_agent import CamelSingleAgent

def main():
    japan_agent = CamelSingleAgent(rag = True, data_with_mcp = True)
    result = japan_agent.run("养殖池塘的面积是多少？")
    print(result)

if __name__ == "__main__":
    main()