
import unittest
from unittest.mock import MagicMock, patch
import json
import os
import sys

# Add src to path
sys.path.append(os.path.abspath("src"))

# We mock anthropic module before importing llm_bridge to avoid import error if not installed (though it should be)
sys.modules['anthropic'] = MagicMock()

from llm_bridge import ClaudeChatSession, convert_to_anthropic_tool

# Dummy Tool
def roll_dice(sides: int) -> str:
    """Rolls a die."""
    return f"Rolled a d{sides}: 10"

class TestClaudeTools(unittest.TestCase):
    def test_serialization(self):
        print("\nTesting Claude Tool Serialization...")
        schema = convert_to_anthropic_tool(roll_dice)
        print(json.dumps(schema, indent=2))
        
        self.assertEqual(schema["name"], "roll_dice")
        self.assertIn("input_schema", schema) # Claude specific
        self.assertEqual(schema["input_schema"]["properties"]["sides"]["type"], "integer")
        
    def test_tool_execution_loop(self):
        print("\nTesting Claude Tool Execution Loop...")
        
        # Setup Session
        tools = [roll_dice]
        
        # Mock Client
        mock_client = MagicMock()
        mock_messages = MagicMock()
        mock_client.messages = mock_messages
        
        # Initialize Session
        session = ClaudeChatSession("fake-key", "claude-test", [], tools, "System Prompt")
        session.client = mock_client # Inject mock
        
        # Turn 1: Claude calls tool
        # Response 1 object structure
        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "roll_dice"
        tool_use_block.input = {"sides": 20}
        tool_use_block.id = "call_123"
        
        response_1 = MagicMock()
        response_1.content = [tool_use_block]
        
        # Turn 2: Claude responds to result
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "I rolled a 10."
        
        response_2 = MagicMock()
        response_2.content = [text_block]
        
        mock_messages.create.side_effect = [response_1, response_2]
        
        # Execute
        response = session.send_message(["Roll a d20"])
        
        print(f"Final Response: {response.text}")
        
        # Verify
        self.assertEqual(response.text, "I rolled a 10.")
        self.assertEqual(mock_messages.create.call_count, 2)
        
        # Verify history structure (Claude requires alternation)
        # 1. User: Roll d20
        # 2. Asst: tool_use
        # 3. User: tool_result
        # 4. Asst: text
        # (Internal storage might be different, but messages sent to API must follow this)
        self.assertEqual(len(session.messages), 4) 
        self.assertEqual(session.messages[0]["role"], "user")
        self.assertEqual(session.messages[1]["role"], "assistant")
        self.assertEqual(session.messages[2]["role"], "user") # Tool result comes from 'user' in Claude API
        self.assertEqual(session.messages[3]["role"], "assistant")

if __name__ == "__main__":
    unittest.main()
