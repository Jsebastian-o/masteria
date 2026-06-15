import json
import os
from collections.abc import Generator
from anthropic import Anthropic
from ..schemas import EstimationRequest
from ..prompts.loader import render_estimation_prompt

client = Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
)


def stream_estimation(request: EstimationRequest) -> Generator[str, None, None]:
    system_prompt, user_message = render_estimation_prompt(request)
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
