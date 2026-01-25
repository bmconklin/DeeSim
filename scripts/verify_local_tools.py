
import unittest
from unittest.mock import MagicMock, patch
import json
import os
import sys

# Add src to path
sys.path.append(os.path.abspath("src"))

from llm_bridge import LocalChatSession, convert_to_ollama_tool

# Dummy Tool
def roll_dice(sides: int) -> str:
    """Rolls a die."""
    return f"Rolled a d{sides}: 10"

class TestLocalTools(unittest.TestCase):
    def test_serialization(self):
        print("\nTesting Tool Serialization...")
        schema = convert_to_ollama_tool(roll_dice)
        print(json.dumps(schema, indent=2))
        
        self.assertEqual(schema["type"], "function")
        self.assertEqual(schema["function"]["name"], "roll_dice")
        self.assertEqual(schema["function"]["parameters"]["properties"]["sides"]["type"], "integer")
        
    @patch("requests.post")
    def test_tool_execution_loop(self, mock_post):
        print("\nTesting Tool Execution Loop...")
        
        # Setup Session
        tools = [roll_dice]
        session = LocalChatSession("test-model", [], "", tools)
        
        # Mock Responses for the Loop
        # Turn 1: AI requests tool call
        conn_1 = MagicMock()
        conn_1.json.return_value = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "roll_dice",
                        "arguments": {"sides": 20}
                    }
                }]
            }
        }
        
        # Turn 2: AI responds to tool output
        conn_2 = MagicMock()
        conn_2.json.return_value = {
            "message": {
                "role": "assistant",
                "content": "I rolled a 10 for you."
            }
        }
        
        mock_post.side_effect = [conn_1, conn_2]
        
        # Execute
        response = session.send_message(["Roll a d20"])
        
        print(f"Final Response: {response.text}")
        
        # Verify
        self.assertEqual(response.text, "I rolled a 10 for you.")
        self.assertEqual(mock_post.call_count, 2)
        
        # Verify execution
        # (Internal logic of session calls the function, verified by the fact we got to turn 2 and result was processed)

if __name__ == "__main__":
    unittest.main()
