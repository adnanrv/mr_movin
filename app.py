import gradio as gr
from chatbot import chat


def respond(message, history):
    """
    Gradio Chatbot (newer versions) expects `history` to be a list of
    dicts with keys: 'role' and 'content'.

    Example:
        [
          {"role": "user", "content": "..."},
          {"role": "assistant", "content": "..."},
          ...
        ]
    """
    history = history or []

    # Call your core chat function — it returns a string reply
    reply = chat(message, history)

    # Append user and assistant messages in the expected format
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})

    # Return updated history and clear the input box
    return history, ""


with gr.Blocks() as demo:
    gr.Markdown(
        "# 🏙️ Apartment Relocation Assistant\n"
        "Ask about your monthly rent budget, cheapest metros, or compare cities."
    )

    # IMPORTANT: no `type=` argument here; your Gradio version doesn't support it.
    chatbot = gr.Chatbot(height=400)
    msg = gr.Textbox(
        placeholder="Example: I have a $2500 budget in CA.",
        label="Your message",
    )
    clear = gr.Button("Clear chat")

    msg.submit(respond, [msg, chatbot], [chatbot, msg])
    clear.click(lambda: ([], ""), None, [chatbot, msg])

if __name__ == "__main__":
    demo.launch()
