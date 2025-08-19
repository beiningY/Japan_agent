from agents.camel_single_agent import CamelSingleAgent

def main():
    japan_agent = CamelSingleAgent()
    result = japan_agent.run("ph值如何调整？")
    print(result)

if __name__ == "__main__":
    main()