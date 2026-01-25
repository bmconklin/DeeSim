"""
Templates package for D&D Knowledge Navigator.

This package contains templates for formatting D&D data in markdown.
"""

from src.dnd.templates.config import (
    TEMPLATES_ENABLED,
    is_template_enabled,
    get_template_setting,
    get_formatting_option
)

from src.dnd.templates.formatter import (
    format_dnd_data,
    format_plain,
    format_search_results
)

from src.dnd.templates.monster import format_monster_stat_block
from src.dnd.templates.spell import format_spell_card
from src.dnd.templates.equipment import format_equipment_card

__all__ = [
    'TEMPLATES_ENABLED',
    'is_template_enabled',
    'get_template_setting',
    'get_formatting_option',
    'format_dnd_data',
    'format_plain',
    'format_search_results',
    'format_monster_stat_block',
    'format_spell_card',
    'format_equipment_card'
]
