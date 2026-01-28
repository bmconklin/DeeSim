# AI DM Enhancements: Feature Deep Dive

This document details the advanced logic implemented to make the AI Dungeon Master more consistent, descriptive, and mechanically accurate.

## 1. High-Fidelity Narration 📖

Previously, if the DM performed multiple actions in a single turn (e.g., rolling for an NPC attack, then rolling for damage), intermediate narration was often lost.

**The Fix:**
- **Turn Aggregation**: The LLM bridge now manually manages the tool-calling loop. It captures every word the AI says *before*, *between*, and *after* each tool call.
- **Unified Response**: All captured text and tool results are concatenated into a single, immersive response for the player.
- **Platform Parity**: This applies to Gemini (Google), Claude (Anthropic), and Local (Ollama) backends.

## 2. Enemy Stat Tracking (Anti-Hallucination) 📊⚔️

To prevent the DM from "forgetting" how much damage an enemy has taken or hallucinating their Armor Class mid-fight, we implemented a persistent state system.

**How it works:**
- **Secret Table**: A hidden `## Active Combat` table is maintained in each session's `secrets_log.md`.
- **Tools**:
    - `initialize_combat`: The DM initializes a pool of enemies with specific HP, AC, and equipment.
    - `track_combat_change`: The DM applies damage, healing, or status effects. This silently updates the markdown table.
- **DM Memory**: The system instructions mandate that the DM *must* check the `secrets_log.md` before narrating a creature's condition or death.

## 3. Universal Naming Principles 📛

To ensure unique and thematic naming for NPCs and locations without repetitive defaults (like "Oakhaven").

**Rules for the DM:**
1. **Pool Generation**: The DM must always generate 5-10 name options using the `generate_name` tool.
2. **Authoritative Choice**: The DM evaluates the options against the campaign's tone and makes the final decision firmware.
3. **Executive DM Role**: Options are NOT presented to players unless requested; the DM remains in character as the authoritative world-builder.

---
These enhancements ensure a professional-grade RPG experience where the rules are consistent and the story is never "skipped over".
