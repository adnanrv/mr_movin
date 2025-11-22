from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

# A small, instruction-tuned model that works on CPU
MODEL_NAME = "google/flan-t5-small"

_tokenizer = None
_model = None
_pipe = None


def get_pipeline():
    global _tokenizer, _model, _pipe
    if _pipe is None:
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
        _pipe = pipeline(
            "text2text-generation",
            model=_model,
            tokenizer=_tokenizer,
        )
    return _pipe


def polish_response(raw_answer: str, user_message: str) -> str:
    """
    Use the LLM to rewrite the structured/raw answer to sound friendlier.
    """
    pipe = get_pipeline()
    prompt = (
        "You are a helpful relocation assistant. "
        "Rewrite the assistant message to be concise, friendly, and easy to read. "
        "Preserve all numbers and facts.\n\n"
        f"User message:\n{user_message}\n\n"
        f"Draft assistant answer:\n{raw_answer}\n\n"
        "Polished answer:"
    )

    out = pipe(prompt, max_length=256, num_beams=2)[0]["generated_text"]
    return out.strip()
