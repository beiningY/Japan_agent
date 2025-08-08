import time
from flask import Flask, Response, request
import logging
from prompts.japan_qa import main  as run_japan
from prompts.bank_qa import main as run_bank
app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AgentSseAPI")
logger.setLevel(logging.INFO)

def sse_format(data: str):
    """格式化成 SSE 数据格式"""
    return f"data: {data}\n\n"

@app.route("/test_stream")
def test_stream():
    agent_type = request.args.get("agent_type", "").strip()
    query = request.args.get("query", "").strip()

    def generate():
        if not agent_type:
            yield sse_format(jsonify({"error": "智能体类型不能为空"}).get_data(as_text=True))
            return

        if agent_type == 'japan':
            try:
                yield from run_japan(query)
            except Exception as e:
                logger.exception("运行失败")
                yield sse_format(jsonify({"error": "服务器内部错误"}).get_data(as_text=True))


        elif agent_type == 'bank':
            try:
                yield from run_bank(query)
            except Exception as e:
                logger.exception("运行失败")
                yield sse_format(jsonify({"error": "服务器内部错误"}).get_data(as_text=True))


        else:
            yield sse_format(jsonify({"error": "未知的智能体类型"}).get_data(as_text=True))

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
