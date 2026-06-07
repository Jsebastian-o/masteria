import json
import os
from collections.abc import Generator
from anthropic import Anthropic
from ..context.examples import EXAMPLES

client = Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
)


def build_context() -> str:
    examples_text = ""
    for i, example in enumerate(EXAMPLES, start=1):
        examples_text += f"\n---\nExample {i}:\n"
        examples_text += f"Meeting Summary:\n{example['meeting_summary'].strip()}\n\n"
        examples_text += f"Estimation:\n{example['estimation'].strip()}\n"

    return (
        "You're an expert estimating software projects based on previous examples "
        "and a translation from the client meeting. "
        "Use the following real examples as reference to calibrate your estimates:\n"
        f"{examples_text}\n---\n"
        "When given a new meeting summary, produce a detailed estimation in the same "
        "structured format shown above, in English."
    )


def stream_estimation(translation: str) -> Generator[str, None, None]:
    system_prompt = build_context()
    with client.messages.stream(
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": translation}],
        model=os.environ.get("LLM_MODEL"),
    ) as stream:
        for text in stream.text_stream:
            yield text
        final = stream.get_final_message()
        meta = {
            "model": final.model,
            "input_tokens": final.usage.input_tokens,
            "output_tokens": final.usage.output_tokens,
            "system_prompt": system_prompt,
        }
        yield f"\x00{json.dumps(meta)}"


def get_estimation(translation: str) -> dict:
    system_prompt = build_context()
    message = client.messages.create(
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": translation}],
        model=os.environ.get("LLM_MODEL"),
    )
    return {
        "estimation": message.content[0].text,
        "model": message.model,
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
        "system_prompt": system_prompt,
    }
