import re
import random
import datetime

# --- Dice Logic ---

def roll_dice(expression: str) -> dict:
    """
    Parses a dice expression (e.g., '1d20+5') and returns the detailed result.
    Supported formats: NdM, NdM+X, NdM-X
    """
    expression = expression.lower().replace(" ", "")
    match = re.match(r"(\d+)d(\d+)([\+\-]\d+)?", expression)
    
    if not match:
        return {"error": f"Invalid dice expression: {expression}"}
    
    num_dice = int(match.group(1))
    die_type = int(match.group(2))
    modifier_str = match.group(3)
    
    modifier = 0
    if modifier_str:
        modifier = int(modifier_str)
        
    rolls = [random.randint(1, die_type) for _ in range(num_dice)]
    total = sum(rolls) + modifier
    
    return {
        "expression": expression,
        "rolls": rolls,
        "modifier": modifier,
        "total": total,
        "timestamp": datetime.datetime.now().isoformat()
    }
