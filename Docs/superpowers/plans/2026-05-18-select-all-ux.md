# Select All UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the results-table `全选` control behave predictably, show clear selection feedback, and avoid table reset flicker.

**Architecture:** Keep the existing secondary-actions layout, add a tiny custom checkbox behavior seam in the main window, and move bulk check-state updates into the table model so UI refresh can happen through normal model signals.

**Tech Stack:** PyQt5, `views/main_window.py`, `viewmodels/main_viewmodel.py`, `unittest`

---

### Task 1: Lock down the desired UX in tests

**Files:**
- Modify: `tests/test_main_window_structure.py`

- [ ] Step 1: Add a test that starts from a partially checked table, clicks the `全选` checkbox, and expects every row to become checked.
- [ ] Step 2: Add a test that clicks the `全选` checkbox again from the fully checked state and expects every row to become unchecked.
- [ ] Step 3: Add a test that verifies the checkbox text reflects `全选（已选/总数）`.
- [ ] Step 4: Add a test that verifies the checkbox is disabled and shows `全选（0/0）` when the table is empty.
- [ ] Step 5: Run `python -m pytest tests/test_main_window_structure.py -k select_all -q` and confirm the new tests fail before implementation.

### Task 2: Implement predictable select-all behavior

**Files:**
- Modify: `views/main_window.py`
- Modify: `viewmodels/main_viewmodel.py`

- [ ] Step 1: Add a small `QCheckBox` subclass that promotes `Qt.PartiallyChecked` to `Qt.Checked` in `nextCheckState()`.
- [ ] Step 2: Replace the plain `全选` checkbox with the subclass in the secondary actions bar.
- [ ] Step 3: Add a table-model helper that updates all row check states without calling `beginResetModel()/endResetModel()`.
- [ ] Step 4: Refactor the main-window select-all handler to use the model helper and rely on model signals for downstream refresh.
- [ ] Step 5: Add a refresh helper for `全选` text, enablement, tooltip, and tri-state state.

### Task 3: Verify and hand off

**Files:**
- Modify: `tests/test_main_window_structure.py` only if a failing test needs final assertion cleanup

- [ ] Step 1: Run `python -m pytest tests/test_main_window_structure.py -q`.
- [ ] Step 2: Run `python -m pytest -q`.
- [ ] Step 3: If both pass, summarize the UX behavior changes and point to the touched files.
