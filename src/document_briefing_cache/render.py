from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .models import DocumentSummaryState, PipelineStats


DEFAULT_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"
TEMPLATE_VERSION = "templates-v0.1.0"


def render_briefing(
    summaries: list[DocumentSummaryState],
    mode: str = "brief",
    audience: str = "general",
    locale: str = "ko-KR",
    stats: PipelineStats | None = None,
    template_dir: str | Path | None = None,
) -> str:
    template_dir = Path(template_dir) if template_dir else DEFAULT_TEMPLATE_DIR
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        trim_blocks=False,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    template_name = f"{mode}.md.j2"
    available = {p.name for p in template_dir.glob("*.md.j2")}
    if template_name not in available:
        raise ValueError(f"Unknown rendering mode '{mode}'. Available modes: {sorted(name[:-6] for name in available)}")

    ordered = sorted(summaries, key=lambda s: (-s.importance, s.title or s.document_id))
    template = env.get_template(template_name)
    return template.render(
        summaries=ordered,
        audience=audience,
        locale=locale,
        stats=stats,
        total_documents=len(summaries),
        all_actions=[action for summary in ordered for action in summary.actions],
        all_risks=[risk for summary in ordered for risk in summary.risks],
        all_decisions=[decision for summary in ordered for decision in summary.decisions],
        all_questions=[question for summary in ordered for question in summary.open_questions],
    ).strip() + "\n"
