# Table Selection UX Design

**Date:** 2026-05-18

**Problem**

The results table currently mixes two different concepts:
- row selection/highlight
- checkbox-based processing selection

That makes single-item selection feel inconsistent next to the top-level `??` control. In addition, the folder entry in the name column does not present a stable, polished folder icon, which makes the table look broken.

**Approved Direction**

The user approved the following interaction model:
- clicking an entire row toggles that row's checkbox state
- the left checkbox remains available for precise clicking
- the top `??` control only manages checkbox state

**Goals**

- make row click and checkbox click behave as one unified selection model
- reduce confusion between "current row" and "selected for processing"
- preserve the existing `??` checkbox as the bulk-selection control
- replace the broken-looking folder square with a clear folder icon in the name column

**Non-Goals**

- no change to scanning, calculating, exporting, or backup workflows
- no redesign of the whole table layout
- no new bulk actions beyond the existing `??`

**Interaction Design**

- Clicking column 0 keeps the native checkbox behavior.
- Clicking any other cell in a row toggles that row's checked state.
- The table keeps a lightweight single-row highlight/focus state, but that highlight is no longer the processing selection model.
- `??` continues to reflect only checked rows, including partial state.

**Visual Design**

- The table should use a real folder icon in the name column.
- The icon should come from a stable Qt/native source so it does not degrade into a missing-glyph square.
- The icon should be compact and aligned with the row height.

**Implementation Approach**

- Add a model helper to toggle one row's checked state through normal model notifications.
- Connect table row clicks in the main window so non-checkbox columns toggle the row's checked state.
- Reduce row-selection behavior from multi-select to single-select to avoid implying a second bulk-selection model.
- Provide a folder icon through the model's `Qt.DecorationRole` for the name column.

**Verification**

Add regression coverage for:
- clicking a row toggles the row checked on
- clicking the same row again toggles it off
- the table uses single-row highlight mode instead of extended multi-select mode
- the name column exposes a non-null folder icon
