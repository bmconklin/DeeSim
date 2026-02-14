---
name: Combat Manager
description: A standardized workflow for running D&D combat encounters, tracking initiative, HP, and narrative flow.
tools:
  - initialize_combat
  - track_combat_change
  - roll_dice
  - request_player_roll
  - log_event
  - lookup_monster
---

# Combat Manager: The Standard Operating Procedure

This skill defines the workflow for running a tactical combat encounter. It ensures fair play, accurate tracking, and dramatic pacing.

## Phase 1: Initiation
1.  **Scout the Enemy**:
    -   Identify the monsters present.
    -   **CRITICAL**: Call `lookup_monster("<Monster Name>")` for each new enemy type.
    -   Note their **Size**, **AC**, **Speed**, and **Attacks**. *Do not guess!*

2.  **Define the Battlefield**:
    -   Call `initialize_combat` with the list of entities.
    -   **Narrate Positioning**: Explicitly describe where enemies are relative to players.
        -   *Example*: "The Ogre is 30ft away, blocking the bridge. The Goblins are on the ridge, 40ft up and to the left."

3.  **Roll Initiative**:
    -   Ask players to roll.
    -   Roll for monsters using `roll_dice`.
    -   Order the combatants.

## Phase 2: The Combat Loop (Repeat until resolved)
For each combatant in the order:

### If NPC Turn:
1.  **Check Positioning**:
    -   Can the monster reach a target? (Check Speed vs Distance).
    -   Does it provoke attacks of opportunity?
2.  **Narrate**: "The Ogre roars and charges 30ft to close the gap with [Player]."
3.  **Execute**:
    -   Choose an action from the `lookup_monster` results.
    -   Call `roll_dice` for attack.
    -   Resolve damage with `track_combat_change`.

### If Player Turn:
1.  **Prompt**: "[Player], the Ogre is 5ft in front of you. The Goblins are 40ft away. What do you do?"
    -   *Always reiterate spatial context.*
2.  **Validate**:
    -   If they want to move/attack, ensure it's possible given the distances.
3.  **Resolve**:
    -   Attack/Spell rolls.
    -   `track_combat_change` for damage.
    -   Narrate impact.

### End of Round:
-   Check for death saves, regeneration, or environmental effects.

## Phase 3: Termination
1.  **Victory or Defeat**:
    -   Call `log_event("Combat ended...")`.
2.  **Cleanup**:
    -   Call `track_combat_change` to clear state.
    -   Award XP.
