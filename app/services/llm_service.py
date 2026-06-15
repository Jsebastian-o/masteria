import json
import os
from collections.abc import Generator
from anthropic import Anthropic
from ..context.examples import EXAMPLES
from ..schemas import EstimationRequest

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
        "You're an expert estimating software projects based on previous examples. "
        "Use the following real examples as reference to calibrate your estimates:\n"
        f"{examples_text}\n---\n"
        "When given a new project description, produce an estimation in English "
        "following the format and detail level specified by the user."
    )


def build_user_message(request: EstimationRequest) -> str:
    return (
        f"Project type: {request.project_type.value}\n"
        f"Detail level: {request.detail_level.value}\n"
        f"Output format: {request.output_format.value}\n\n"
        f"Description:\n{request.description}"
    )


def stream_estimation(request: EstimationRequest) -> Generator[str, None, None]:
    system_prompt = build_context()
    user_message = build_user_message(request)
    with client.messages.stream(
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
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
