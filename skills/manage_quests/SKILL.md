---
name: Quest Tracker
description: Workflow for tracking active quests, objectives, and their completion status using the quest database.
tools:
  - manage_quests
  - log_event
  - update_world_info
---

# Quest Tracker: Keeping the Goal in Sight

This skill ensures that players never forget their mission and that completion is rewarded. We now use a strict database system to track quests.

## Workflow

### 1. New Quest Given
When an NPC assigns a mission or players decide on a major goal:
1.  **Record it**:
    -   Call `manage_quests("add", title="<Quest Name>", description="<Objective>", status="Active")`.
2.  **Narrate**: Make sure the players understand the stakes.

### 2. Quest Milestone
When players make significant progress (e.g., find a clue, kill a lieutenant):
1.  **Update it**:
    -   Call `manage_quests("update", title="<Quest Name>", description="<New info added to log>")`.

### 3. Quest Completion
When the objective is met:
1.  **Complete it**:
    -   Call `manage_quests("complete", title="<Quest Name>")`.
2.  **Rewards**:
    -   Narrate the reward (Gold/XP).
    -   Update `world_info` if this changes the world (e.g., "The King is debt-free").

### 4. Quest Review (High Level Summary)
If players ask "What are we doing?" or "Check our quests":
1.  **List Activities**:
    -   Call `manage_quests("list")`.
2.  **Summarize**: Read the output from the tool and present it to the players.
