"""Discover and load skills from the skills/ package dynamically."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Any, Dict, List, Type

from skills.base_skill import BaseSkill

# Modules that are infrastructure, not executable skills
_SKIP_MODULES = {"base_skill", "__init__"}


def _skill_class_name(module_name: str) -> str:
    """scraper -> ScraperSkill, gap_finder -> GapFinderSkill."""
    parts = module_name.split("_")
    return "".join(part.capitalize() for part in parts) + "Skill"


def load_skills() -> List[BaseSkill]:
    """
    Scan skills/ for Python modules and instantiate every *Skill class found.

    Convention: scraper.py defines ScraperSkill, gap_finder.py defines GapFinderSkill.
    """
    skills: List[BaseSkill] = []
    package_path = Path(__file__).parent / "skills"

    print("🔧 Loading skills from skills/ ...")

    for module_info in pkgutil.iter_modules([str(package_path)]):
        if module_info.name in _SKIP_MODULES or module_info.name.startswith("_"):
            continue

        class_name = _skill_class_name(module_info.name)
        module_path = f"skills.{module_info.name}"

        try:
            module = importlib.import_module(module_path)
            skill_cls = getattr(module, class_name, None)

            if skill_cls is None:
                print(f"⚠️  Skipping {module_path}: no class {class_name}")
                continue

            if not inspect.isclass(skill_cls) or not issubclass(skill_cls, BaseSkill):
                print(f"⚠️  Skipping {class_name}: not a BaseSkill subclass")
                continue

            instance = skill_cls()
            skills.append(instance)
            print(f"   ✓ Loaded skill: {instance.name}")

        except Exception as exc:
            print(f"❌ Failed to load {module_path}: {exc}")

    print(f"📦 {len(skills)} skill(s) ready\n")
    return skills


def skills_to_tools(skills: List[BaseSkill]) -> List[Dict[str, Any]]:
    """Convert loaded skills into Anthropic Messages API tool definitions."""
    return [skill.to_tool_definition() for skill in skills]


def get_skill_by_name(skills: List[BaseSkill], name: str) -> BaseSkill | None:
    """Look up a skill instance by its tool name."""
    for skill in skills:
        if skill.name == name:
            return skill
    return None
