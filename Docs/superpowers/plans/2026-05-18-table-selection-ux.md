# Table Selection UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify row click and checkbox selection in the results table, while replacing the broken-looking folder square with a proper folder icon.

**Architecture:** Keep the existing table and select-all layout, teach the table model how to toggle one row's checked state, and let the main window route row clicks into that helper. Keep bulk selection in the existing `??` checkbox. Provide folder visuals through `Qt.DecorationRole` in the model.

**Tech Stack:** PyQt5, `views/main_window.py`, `viewmodels/main_viewmodel.py`, `tests/test_main_window_structure.py`

---

### Task 1: Lock down the new row-selection UX in tests

**Files:**
- Modify: `tests/test_main_window_structure.py`

- [ ] Step 1: Add a test that clicks a non-checkbox cell and expects the row to become checked.
- [ ] Step 2: Add a test that clicks the same row again and expects the row to become unchecked.
- [ ] Step 3: Add a test that verifies the table is configured for single-row highlight mode instead of extended multi-select mode.
- [ ] Step 4: Add a test that verifies the name column returns a non-null icon through `Qt.DecorationRole`.
- [ ] Step 5: Run `python -m pytest tests/test_main_window_structure.py -k row_toggle -q` and confirm the new tests fail before implementation.

### Task 2: Implement unified row-toggle behavior and folder icon display

**Files:**
- Modify: `viewmodels/main_viewmodel.py`
- Modify: `views/main_window.py`

- [ ] Step 1: Add a table-model helper that toggles one row's checked state and emits the smallest necessary `dataChanged` signal.
- [ ] Step 2: Return a stable folder icon from the model's `Qt.DecorationRole` for the name column.
- [ ] Step 3: Switch the table view from extended multi-selection to single-row highlight mode.
- [ ] Step 4: Connect table row clicks so non-checkbox columns toggle the row checked state.
- [ ] Step 5: Keep `??` and downstream button/status refreshes driven by the existing model signal flow.

### Task 3: Verify behavior

**Files:**
- Modify: `tests/test_main_window_structure.py` only if assertion cleanup is needed

- [ ] Step 1: Run `python -m pytest tests/test_main_window_structure.py -q`.
- [ ] Step 2: Run `python -m pytest -q`.
- [ ] Step 3: Summarize the selection and icon UX changes with touched file paths.
