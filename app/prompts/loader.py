from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from ..context.examples import EXAMPLES
from ..schemas import EstimationRequest


def render_estimation_prompt(request: EstimationRequest, version: str = "v1") -> tuple[str, str]:
    prompts_dir = Path(__file__).parent / "estimation" / version
    env = Environment(loader=FileSystemLoader(str(prompts_dir)))

    system = env.get_template("system.j2").render(
        output_format=request.output_format.value,
        detail_level=request.detail_level.value,
        examples=EXAMPLES,
    )
    user = env.get_template("user.j2").render(
        project_type=request.project_type.value,
        detail_level=request.detail_level.value,
        output_format=request.output_format.value,
        description=request.description,
    )

    return system, user
