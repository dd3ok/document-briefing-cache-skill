from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, PackageLoader, StrictUndefined
from markupsafe import escape

from .models import DocumentSummaryState, PipelineStats


DEFAULT_TEMPLATE_PACKAGE = "document_briefing_cache"
DEFAULT_TEMPLATE_PATH = "templates"
TEMPLATE_VERSION = "templates-v0.2.0"


def _build_environment(template_dir: str | Path | None) -> Environment:
    loader = (
        FileSystemLoader(str(Path(template_dir)))
        if template_dir is not None
        else PackageLoader(DEFAULT_TEMPLATE_PACKAGE, DEFAULT_TEMPLATE_PATH)
    )
    env = Environment(
        loader=loader,
        autoescape=False,
        trim_blocks=False,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    env.filters["md"] = markdown_inline_escape
    return env


def render_briefing(
    summaries: list[DocumentSummaryState],
    mode: str = "brief",
    audience: str = "general",
    locale: str = "ko-KR",
    stats: PipelineStats | None = None,
    template_dir: str | Path | None = None,
) -> str:
    env = _build_environment(template_dir)
    template_name = f"{mode}.md.j2"
    available = set(env.list_templates(filter_func=lambda name: name.endswith(".md.j2")))
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


def markdown_inline_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^([#>*+\-=]|\d+\.)", r"\\\1", text)
    for character in ("\\", "`", "*", "_", "~", "[", "]", "(", ")", "!"):
        text = text.replace(character, f"\\{character}")
    return str(escape(text))
