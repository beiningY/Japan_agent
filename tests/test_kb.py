from run_qa.lang_kb_qa import create_kb, delete_kb, ask

def test_create_kb():
    create_kb("bank")

def test_delete_kb():
    delete_kb("bank")

def test_ask():
    ask("ph值怎么调整", kb_name="bank")

if __name__ == "__main__":
    # test_create_kb()
    # test_delete_kb()
    test_ask()
