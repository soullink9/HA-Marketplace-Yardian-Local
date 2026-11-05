"""Static checks for the watering blueprint. Run: python3 tests/test_blueprint.py

Catches the mistakes that are easy to make when editing a long blueprint by hand:
- an input that is defined but never used, or used but never defined
- the trigger's start-time calculation drifting from the copy in the "start_ts" variable
- a Jinja template that doesn't parse
- an action other than the ones this blueprint is meant to call
Needs PyYAML and Jinja2 (pip install -r tests/requirements.txt).
"""

from pathlib import Path
import sys

import jinja2
import yaml

BLUEPRINT = Path(__file__).resolve().parents[1] / "blueprints/automation/yardian/yardian_lawn_schedule.yaml"
ALLOWED_ACTIONS = {"button.press", "weather.get_forecasts", "yardian_local.start_irrigation", "yardian_local.notify"}


class _Input:
    """Placeholder for a !input tag."""

    def __init__(self, name: str) -> None:
        """Remember the input's name."""
        self.name = name


def _loader() -> type:
    """A YAML loader that understands Home Assistant's !input tag."""

    class Loader(yaml.SafeLoader):
        """SafeLoader plus !input."""

    Loader.add_constructor("!input", lambda loader, node: _Input(loader.construct_scalar(node)))
    return Loader


def _walk(node, path=""):
    """Yield (path, value) for every scalar in the document."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _walk(value, f"{path}[{i}]")
    else:
        yield path, node


def main() -> int:
    """Run every check; print problems and return the number found."""
    doc = yaml.load(BLUEPRINT.read_text(), Loader=_loader())
    problems = []

    defined = {name for section in doc["blueprint"]["input"].values() for name in section["input"]}
    body = {k: v for k, v in doc.items() if k != "blueprint"}
    used = {v.name for _, v in _walk(body) if isinstance(v, _Input)}
    problems += [f"input defined but never used: {n}" for n in sorted(defined - used)]
    problems += [f"input used but not defined: {n}" for n in sorted(used - defined)]

    trigger = next(t for t in doc["triggers"] if t.get("id") == "schedule")["value_template"]
    variable = next(
        a["variables"]["start_ts"] for a in doc["actions"] if "variables" in a and "start_ts" in a["variables"]
    )
    if trigger.rsplit("\n", 1)[0] != variable.rsplit("\n", 1)[0]:
        problems.append("the schedule trigger and the start_ts variable no longer calculate the start the same way")

    env = jinja2.Environment(extensions=["jinja2.ext.loopcontrols", "jinja2.ext.do"])
    for path, value in _walk(body):
        if isinstance(value, str) and ("{{" in value or "{%" in value):
            try:
                env.parse(value)
            except jinja2.TemplateSyntaxError as err:
                problems.append(f"template does not parse at {path}: {err}")
        if path.endswith(".action") and isinstance(value, str) and value not in ALLOWED_ACTIONS:
            problems.append(f"unexpected action {value} at {path}")

    for problem in problems:
        print("FAIL", problem)
    print(f"{BLUEPRINT.name}: {'OK' if not problems else f'{len(problems)} problem(s)'}")
    return len(problems)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
