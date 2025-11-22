import gradio as gr
from chatbot import chat


def respond(message, history):
    reply = chat(message, history)
    history = history or []
    history.append((message, reply))
    return history, ""


with gr.Blocks() as demo:
    gr.Markdown("# 🏙️ Apartment Relocation Assistant (Zillow Demo)\nAsk me about your budget, or ask me to compare metros.")

    chatbot = gr.Chatbot(height=400)
    msg = gr.Textbox(placeholder="Example: I have a $400000 budget and want a 3 bedroom home.")
    clear = gr.Button("Clear chat")


    msg.submit(respond, [msg, chatbot], [chatbot, msg])
    clear.click(lambda: ([], ""), None, [chatbot, msg])

if __name__ == "__main__":
    demo.launch()
