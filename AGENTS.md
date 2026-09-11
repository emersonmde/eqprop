# Project handoff

Read `docs/project-state.md` first, then the document for the stage being worked on. This repository is the source of truth; do not depend on a previous chat or files in a Codex output folder.

- Current hardware: B.1. Preserve native child sheets, project libraries and rules together.
- Keep the schematic, PCB and `design-manifest.json` consistent. Generate the BOM with `tools/generate_bom.py`; validate with tests and `tools/export_manufacturing.py` after electrical/layout changes.
- Never infer implemented Nano firmware or completed bench measurements from simulation results. Update project-state.md when a milestone actually completes.
- Record calibration, board serial/revision, firmware commit and supply conditions with measurements. No substitution of analog parts without review.
- Retain useful regression tests. Generated exports/caches belong under ignored build/ or their tool's ignored cache directories; do not commit recovery files or duplicate design backups.
- User normally handles commits; commit only when explicitly requested. Never place an order or send files/messages without authorization for that action.
