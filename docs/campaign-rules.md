# Campaign rules

## Shared experience

This campaign uses group experience rather than milestones. The DM records the
XP value of an encounter and the application divides it equally across active
player characters. The result is rounded down to a whole XP value and any
remainder is discarded.

For example, an encounter worth 10 XP with five active player characters
awards 2 XP to each character. An 11 XP encounter with the same group still
awards 2 XP each and discards 1 XP.

Only active characters linked to a Player receive shared XP. NPCs and inactive
characters do not. A Player may have only one active character in a campaign.
When a player character is activated, it is automatically brought to the
campaign's current shared-XP value.

Use `campaign.award_shared_experience(..., dry_run=True)` to validate an award and see
the per-character XP value without posting ledger entries or changing campaign
XP. A normal award returns the same per-character value after it posts.

Shared-XP awards are only available where `Campaign.use_shared_exp` is enabled.
Individual XP is intentionally not supported yet.

## Inventory and money history

The application keeps a permanent history of inventory, coin, and XP changes.
For example, finding a torch records it leaving the campaign's system inventory
and entering a character's inventory. Spending a gold piece records where that
gold went. This means the current values are always explainable from the
history rather than being silently edited.

If the DM makes a mistake, they should reverse the original transaction and
then post the correct replacement. Posted transactions are not edited or
deleted. The UI should make this feel like a correction note, not an accounting
exercise: show the original action, its reversal, and the replacement together.
