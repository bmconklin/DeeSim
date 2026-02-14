---
name: Treasure Hunter
description: Workflow for generating balanced random loot based on Encounter CR and Party Level.
tools:
  - roll_dice
  - manage_inventory
  - lookup_item_details
---

# Treasure Hunter: The Balanced Loot Generator

This skill ensures that rewards are appropriate for the party's level and the challenge faced.

## Loot Generation Rules

### Step 1: Determine the Tier
Use the **Encounter CR** (or Party Level if non-combat) to select the Tier.
*   **Tier 0 (CR 0-4)**: Local Heroes. Low magic.
*   **Tier 1 (CR 5-10)**: Realm Heroes. Uncommon/Rare magic.
*   **Tier 2 (CR 11-16)**: Masters of the Realm. Very Rare magic.
*   **Tier 3 (CR 17+)**: Masters of the World. Legendary artifacts.

### Step 2: Roll for Individual Treasure (Gold)
Roll the dice appropriate for the Tier.
*   **Tier 0**: `roll_dice("2d6*10", "Gold (Tier 0)")` gp.
*   **Tier 1**: `roll_dice("4d6*100", "Gold (Tier 1)")` gp.
*   **Tier 2**: `roll_dice("4d6*1000", "Gold (Tier 2)")` gp.
*   **Tier 3**: `roll_dice("10d6*1000", "Gold (Tier 3)")` gp.

*Note: For a "Horde" (large accumulation like a dragon's hoard), multiply the result by 5.*

### Step 3: Check for Magic Items
Roll d100 `roll_dice("1d100", "Magic Item Chance")`. Compare to the table below.

#### Tier 0 Table (CR 0-4)
*   **01-85**: No Item.
*   **86-95**: Common Item (Potion of Healing, Scroll).
*   **96-00**: Uncommon Item (Weapon +1, Bag of Holding).
*   **RESTRICTION**: NO Rare/Very Rare items.

#### Tier 1 Table (CR 5-10)
*   **01-60**: No Item.
*   **61-80**: Common/Uncommon Item.
*   **81-95**: Rare Item (Weapon +2, Armor +1).
*   **96-00**: Very Rare Item (only on CR 10+ deadly encounters, otherwise Rare).

#### Tier 2 Table (CR 11-16)
*   **01-40**: No Item.
*   **41-80**: Rare Item.
*   **81-95**: Very Rare Item.
*   **96-00**: Legendary Item (Story specific only).

### Step 4: Verify Item Rarity (Critical)
Before confirming the item, you **MUST** verify its rarity matches the Tier:
1.  Call `lookup_item_details("<Item Name>")`.
2.  Check the "Rarity" in the output.
3.  **If the rarity is too high** (e.g., Rare item in Tier 0):
    -   Discard the result.
    -   Pick a weaker item or convert it to Gold.
    -   *Do not give low-level players high-tier items.*

### Step 5: Distribute
1.  **Ask**: "Who picks this up?"
2.  **Assign**: `manage_inventory("add", "<Item>", "<Character>", weight=...)`
