"""Generators module for the Facts-First, LLM-Last architecture."""
from recaps.generators.base import BaseGenerator, GeneratorResult, RenderingMode
from recaps.generators.power_rankings import PowerRankingsGenerator
from recaps.generators.waiver_recap import WaiverRecapGenerator
from recaps.generators.weekly_recap import WeeklyRecapGenerator
from recaps.generators.llm_planner import (
    LLMPlanner,
    RecapPlan,
    Section,
    SectionType,
    TeamBlurb,
    MatchupBlurb,
    create_planner,
)

__all__ = [
    # Base classes
    "BaseGenerator",
    "GeneratorResult",
    "RenderingMode",
    # Generators
    "PowerRankingsGenerator",
    "WaiverRecapGenerator",
    "WeeklyRecapGenerator",
    # LLM Planner
    "LLMPlanner",
    "RecapPlan",
    "Section",
    "SectionType",
    "TeamBlurb",
    "MatchupBlurb",
    "create_planner",
]
