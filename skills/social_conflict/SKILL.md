---
name: Social Encounter
description: Workflow for running dramatic social conflicts where stakes are high and outcomes rely on dice rolls, not just roleplay.
tools:
  - request_player_roll
  - roll_dice
---

# Social Encounter: Words as Weapons

This skill defines how to run tense negotiations using a dynamic Difficulty Class (DC) system. The difficulty depends on **Two Factors**: The NPC's **Attitude** toward the player, and the **Weight** of the request.

## Workflow

### 1. Determine Difficulty
Calculate the DC by adding the **Base Attitude** and the **Request Cost**.

#### Factor A: Base Attitude (Starting DC)
*   **Friendly (0)**: Wants to help. Allies, friends, charmed NPCs.
*   **Indifferent (10)**: Neutral. Shopkeepers, guards, strangers.
*   **Hostile (20)**: Dislikes/Opposes. Enemies, rivals, insulted NPCs.

#### Factor B: Request Cost (Modifier)
*   **Trivial (+0)**: No cost/risk. Information, directions, small talk.
*   **Minor (+5)**: Small favor/cost. A discount, a free drink, looking the other way for a moment.
*   **Significant (+10)**: Real risk/cost. Lending a horse, betraying a minor duty, fighting alongside you.
*   **Major (+20)**: High risk/cost. Betraying a lord, giving away a magical heirlooom.
*   **Extreme (+30)**: "Die for me." Nearly impossible without magic/leverage.

#### Examples:
*   Asking a **Friend** (0) for a **Major Favor** (20) = **DC 20**.
*   Asking a **Hostile** (20) for a **Trivial thing** (0) = **DC 20**.
*   Asking an **Indifferent** (10) for a **Minor Favor** (5) = **DC 15**.

### 2. Apply Modifiers (The Roleplay)
Before the roll, adjust the final DC based on the player's approach:
*   **Good Roleplay/Leverage**: -2 to -5 (Lowers DC).
*   **Bad Roleplay/Insult**: +2 to +5 (Increases DC).
*   **Intimidation**: Generally targets Wisdom/Charisma Save instead of DC, or grants Advantage but risks Hostility on failure.

### 3. Resolution
1.  **Call for Check**:
    -   `request_player_roll("Persuasion/Deception/Intimidation", DC, "Refusal/Consequence")`.
2.  **Outcome**:
    -   **Success**: The NPC agrees or compromises.
    -   **Failure**: The NPC refuses. Attitude may shift (e.g., Indifferent -> Hostile).
    -   **Critical Failure**: NPC becomes Hostile immediately or calls guards.
