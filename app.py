"""
Gradio interface for The Unofficial Guide to Austin Restaurants.

Run with:
    uv run app.py
Then open http://localhost:7860
"""

import gradio as gr
from query import ask


def handle_query(question: str) -> tuple[str, str]:
    question = question.strip()
    if not question:
        return "Please enter a question.", ""

    result = ask(question)
    sources = "\n".join(f"• {s}" for s in result["sources"])
    return result["answer"], sources


with gr.Blocks(title="The Unofficial Guide — Austin Restaurants") as demo:
    gr.Markdown("## The Unofficial Guide to Austin Restaurants")
    gr.Markdown(
        "Ask about restaurants, dishes, neighborhoods, or cuisine types. "
        "Answers are drawn only from curated local reviews and blog posts."
    )

    with gr.Row():
        inp = gr.Textbox(
            label="Your question",
            placeholder="e.g. Where can I get Egyptian-style BBQ in Austin?",
            lines=2,
        )

    btn = gr.Button("Ask", variant="primary")

    with gr.Row():
        answer_box = gr.Textbox(label="Answer", lines=6, interactive=False)
        sources_box = gr.Textbox(label="Retrieved from", lines=6, interactive=False)

    btn.click(handle_query, inputs=inp, outputs=[answer_box, sources_box])
    inp.submit(handle_query, inputs=inp, outputs=[answer_box, sources_box])

    gr.Examples(
        examples=[
            ["Where in Austin can I get Egyptian-inspired BBQ?"],
            ["Is Loro worth going to?"],
            ["What is the best steakhouse in Austin?"],
            ["What is the best barbecue in Austin?"],
            ["Is the weather hot in Austin?"],
        ],
        inputs=inp,
    )


if __name__ == "__main__":
    demo.launch()
