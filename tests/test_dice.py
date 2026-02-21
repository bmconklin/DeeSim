import sys
import os

# Add src to python path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from dnd.dice import roll_dice

def test_roll_dice_standard():
    result = roll_dice("1d20")
    assert "error" not in result
    assert result["expression"] == "1d20"
    assert len(result["rolls"]) == 1
    assert 1 <= result["rolls"][0] <= 20
    assert result["modifier"] == 0

def test_roll_dice_with_modifier():
    result = roll_dice("2d6+3")
    assert "error" not in result
    assert result["expression"] == "2d6+3"
    assert len(result["rolls"]) == 2
    assert result["modifier"] == 3
    assert result["total"] == sum(result["rolls"]) + 3

def test_roll_dice_invalid():
    result = roll_dice("invalid")
    assert "error" in result
    assert "Invalid dice expression" in result["error"]
