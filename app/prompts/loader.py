from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from ..context.examples import EXAMPLES
from ..schemas import EstimationRequest
from ..services.sessions import ProjectMetadata


def render_session_system_prompt(metadata: ProjectMetadata, version: str = "v1") -> str:
    prompts_dir = Path(__file__).parent / "session" / version
    env = Environment(loader=FileSystemLoader(str(prompts_dir)))
    has_metadata = bool(
        metadata.project_name
        or metadata.assumed_team_size
        or metadata.mentioned_technologies
        or metadata.agreed_scope
    )
    return env.get_template("system.j2").render(
        has_metadata=has_metadata,
        project_name=metadata.project_name,
        assumed_team_size=metadata.assumed_team_size,
        mentioned_technologies=metadata.mentioned_technologies,
        agreed_scope=metadata.agreed_scope,
    )


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
