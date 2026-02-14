---
name: Session Architect
description: A standardized workflow for starting, running, and ending D&D sessions to ensure consistent logging and state management.
tools:
  - start_new_session
  - list_sessions
  - read_full_session
  - end_session_and_compact
  - update_world_info
---

# Session Architect: The Standard Operating Procedure

This skill defines the critical path for managing a D&D session. Following this workflow prevents memory loss and ensures a smooth player experience.

## Phase 1: Preparation (Before Players Arrive)
1.  **Check Current State**:
    -   Call `list_sessions()` to see where the campaign left off.
    -   Call `read_full_session("current")` to load the context of the last game.
    
2.  **Verify Setup**:
    -   If the last session ended with `!wrapup`, the current logs should be empty/ready for new input.
    -   If the last session log is full of text, call `start_new_session(summary_of_previous)` to archive it and start fresh.

## Phase 2: The Start (When Players Arrive)
1.  **Recap**:
    -   Read the summary from the previous session log.
    -   Greet the players with a dramatic "Previously on..." narrative.
    
2.  **Roll Call**:
    -   Ask "Who is here tonight?"
    -   Verify character sheets if new players join (`read_character_sheet`).

## Phase 3: The Session Loop (During Play)
1.  **Log Continuously**:
    -   Use `log_event(message)` for major narrative beats (e.g., "The party entered the dungeon").
    -   Use `log_event(message, is_secret=True)` for DM notes (e.g., "The chest is trapped").
    
2.  **Combat (If needed)**:
    -   Call `initialize_combat` to set up the scene.
    -   Call `track_combat_change` to update HP.

3.  **World Building**:
    -   If a new NPC or Location is created, call `update_world_info` IMMEDIATELY.

## Phase 4: The End (Wrap Up)
1.  **The Cliffhanger**:
    -   Find a dramatic stopping point.
    
2.  **Summarize & Archive**:
    -   Call `end_session_and_compact(manual_summary=None)`.
    -   This will:
        -   Read the full log.
        -   Generate a concise summary.
        -   Archive the raw log to `session_X_full_archive.md`.
        -   Reset the main log for the next session.
        
3.  **Tease**:
    -    give a brief preview of what's next based on the summary.
