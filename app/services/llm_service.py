import os
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


def get_estimation(translation: str) -> str:
    message = client.messages.create(
        max_tokens=2048,
        system=build_context(),
        messages=[{"role": "user", "content": translation}],
        model="claude-haiku-4-5",
    )
    return message.content[0].text
