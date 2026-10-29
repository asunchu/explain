"""Shared path-specific routing for installation and evaluation."""
from pathlib import Path

SKILL_DIRS = {'codex': '.agents/skills', 'claude-code': '.claude/skills', 'opencode': '.opencode/skills'}

def routing(skill_path):
    entry = Path(skill_path) / 'SKILL.md'
    return f"""## Explanation artifacts

For a diagram, interactive explanation, narrated animation, storyboard, or video plan, read `{entry}` before answering.
Use that exact file and its relative references, even if a global skill has the same name.
For video planning or production, also read `references/production.md` and `VIDEO.md` beside that entrypoint.
A plan request does not authorize creating or rendering an artifact. Follow the user's requested scope.
Do not announce instruction loading or writing checks.
"""
