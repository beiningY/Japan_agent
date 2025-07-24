import gradio as gr
from main import advanced_agents, simple_agents

with gr.Blocks(title="南美白对虾问答助手") as demo:
    gr.Markdown("## 🦐 南美白对虾问答助手")
    gr.Markdown("输入你关于南美白对虾的问题，我将根据知识库为你生成专业回答。")

    with gr.Row():
        with gr.Column():
            user_input = gr.Textbox(label="用户提问", placeholder="请输入你的问题…", lines=5)
            submit_btn = gr.Button("Submit(simple)")
            submit_btn2 = gr.Button("Submit(advanced)")
            clear_btn = gr.Button("Clear")

        with gr.Column():
            output = gr.Textbox(label="AI 回答", lines=10, interactive=False)

    submit_btn.click(fn=simple_agents, inputs=user_input, outputs=output)
    submit_btn2.click(fn=advanced_agents, inputs=user_input, outputs=output)
    clear_btn.click(fn=lambda: ("", ""), inputs=[], outputs=[user_input, output])

demo.launch(
    server_name="localhost", 
    server_port=7860,
    share=True,          
)

