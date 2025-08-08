import time
from flask import Flask, Response
import logging
app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AgentSseAPI")
logger.setLevel(logging.INFO)


@app.route('/stream')
def stream():
    def generate():
        yield "data: \n\n"
        time.sleep(1)
        yield "data: \n\n"
        time.sleep(2)
        yield "data: \n\n"
        time.sleep(3)
        yield "data: \n\n"

    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
