# Minimal Workflow UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the main window into a minimal workflow-first UI that emphasizes selecting a directory, scanning, and only then performing secondary actions.

**Architecture:** Keep the existing main-window architecture, but simplify the visual hierarchy into a primary toolbar, a secondary action row, a large results table, and a compact status footer. Introduce a tiny layout-config helper that can be tested without Qt.

**Tech Stack:** PyQt5, existing `views/main_window.py`, QSS styling, `unittest`

---

### Task 1: Add layout config test seam

**Files:**
- Create: `utils/ui_layout.py`
- Create: `tests/test_ui_layout.py`

- [ ] Step 1: Write failing tests for primary/secondary action grouping and compact stats layout
- [ ] Step 2: Run the tests and verify they fail because the helper does not exist
- [ ] Step 3: Implement the minimal helper definitions
- [ ] Step 4: Re-run the targeted tests and verify they pass

### Task 2: Apply workflow-first layout in main window

**Files:**
- Modify: `views/main_window.py`
- Modify: `resources/styles/main.qss`

- [ ] Step 1: Move `计算大小 / 导出结果 / 备份目录 / 全选` out of the main toolbar into a compact secondary row
- [ ] Step 2: Keep only `选择目录 / 开始扫描 / 停止` plus current path in the primary toolbar
- [ ] Step 3: Simplify table-area spacing and footer so the table dominates the window
- [ ] Step 4: Update QSS to reduce decoration and emphasize the primary scan flow

### Task 3: Verify behavior and packaging readiness

**Files:**
- Modify: `README.md` only if needed

- [ ] Step 1: Run targeted tests for layout helpers
- [ ] Step 2: Run the full unit test suite
- [ ] Step 3: Run `compileall` for touched modules
