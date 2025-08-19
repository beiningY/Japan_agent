from agents.camel_roleplay_agent import CamelRoleplayAgent

def main():
    japan_agent = CamelRoleplayAgent(max_tokens=10000)
    result = japan_agent.run("ph值如何调整？")
    print(result)

if __name__ == "__main__":
    main()