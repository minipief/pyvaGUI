# Changelog

## 0.1.0 - unreleased

- Save and open projects as `.pyvagui` files while preserving the versioned JSON content
- Modernized desktop styling with visible splitter handles, compact project navigation, and a resizable application log
- Grouped library materials by category and sorted their names; linked frame materials are copied automatically
- Replaced routine add, save-to-library, and result-export popups with inline feedback; retained data-loss safeguards
- Project setup: folder structure, pyproject.toml, flake8, pytest
- Material specs: Fluid, EquivalentFluid, Delany-Bazley, IsoMat, and PoroElasticMat
- Phase 1: inspected pyva-toolbox 1.3.1 and documented its API
- Updated smoke tests to the current ID-based poroelastic material API
- Phase 2: added layup, layer, and perforation model specifications
- Phase 3: added logarithmic frequency settings, solver presets, and result containers
- Phase 4: added versioned project JSON, material library, and bundled default materials
- Phase 5: added CSV result and PNG/SVG figure export
- Phase 6: added the PyQt application entry point and resizable main-window shell
- Phase 7: added project tree, project file actions, and unsaved-change handling
- Phase 8: added material dialogs and legacy material-library migration
- Phase 9: added layup and perforation editors with layer reordering
- Phase 10: added a QPainter stack preview to the layup editor
- Phase 11: added solver configuration dialogs and one result placeholder tab per solver
- Phase 12: added threaded solver execution, progress, cancellation, and error reporting
- Phase 13: added result plots, complex impedance views, export, and end-to-end GUI coverage
- Phase 14: expanded GUI workflow and regression coverage across all dialogs
- Phase 15: completed README, architecture overview, and final verification
