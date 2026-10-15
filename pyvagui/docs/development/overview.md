# pyvaGUI Architecture and Workflow

## Purpose

pyvaGUI is a PyQt6 desktop application for configuring infinite-layer
models and running calculations with pyva. The project model stores
materials, ordered layups, and solver settings. Calculated arrays remain
in memory and are displayed or exported separately.

## Architecture

```mermaid
classDiagram
    class Project {
        +name
        +materials
        +layups
        +solvers
        +save(path)
        +load(path)
        +validate()
    }
    class MaterialSpec {
        <<abstract>>
        +id
        +name
        +validate()
        +to_pyva(materials)
    }
    class FluidSpec
    class EquivalentFluidSpec
    class DelanyBazleySpec
    class IsoMatSpec
    class PoroElasticMatSpec
    class Layup {
        +layers
        +validate(materials)
        +build_tmmodel(materials)
    }
    class LayerSpec {
        +material_id
        +thickness
        +layer_type
    }
    class SolverSpec {
        +solver_type
        +frequencies
        +run(layup, materials)
    }
    class FrequencySettings {
        +f_start
        +f_end
        +n_points
        +frequencies()
    }
    class CalculationWorker {
        +progress
        +finished
        +failed
        +run()
    }
    class ResultSet {
        +frequencies
        +results
    }
    class LayupResult {
        +layup_id
        +values
    }
    class MaterialLibrary {
        +load()
        +save()
        +import_materials(path)
        +export_materials(ids, path)
    }
    class MainWindow
    class MaterialEditorDialog
    class LayupEditorDialog
    class SolverEditorDialog
    class LibraryDialog
    class ResultTab

    MaterialSpec <|-- FluidSpec
    MaterialSpec <|-- IsoMatSpec
    MaterialSpec <|-- FluidPropertiesSpec
    FluidPropertiesSpec <|-- DampedFluidPropertiesSpec
    DampedFluidPropertiesSpec <|-- EquivalentFluidSpec
    DampedFluidPropertiesSpec <|-- DelanyBazleySpec
    FluidPropertiesSpec <|-- PoroElasticMatSpec
    PoroElasticMatSpec --> IsoMatSpec : frame ID
    Project o-- MaterialSpec
    Project o-- Layup
    Project o-- SolverSpec
    Layup *-- LayerSpec
    LayerSpec --> MaterialSpec : material ID
    SolverSpec *-- FrequencySettings
    SolverSpec --> Layup : selected IDs
    CalculationWorker --> SolverSpec
    CalculationWorker --> Layup
    CalculationWorker --> ResultSet
    ResultSet *-- LayupResult
    MainWindow --> Project
    MainWindow --> CalculationWorker : QThread
    MainWindow --> MaterialEditorDialog
    MainWindow --> LayupEditorDialog
    MainWindow --> SolverEditorDialog
    MainWindow --> LibraryDialog
    MainWindow --> ResultTab
    LibraryDialog --> MaterialLibrary
```

### Layered responsibilities

- `pyvagui.model` contains plain Python specifications, validation,
  serialization, and pyva conversion. It never imports PyQt6.
- `pyvagui.services` handles work that crosses the GUI boundary, such as
  calculation workers and file export.
- `pyvagui.gui` presents model objects, collects input, and sends user
  actions to the model or services.
- The GUI edits copies in dialogs and commits them only after validation.
  The project model remains the source of truth for tree and table views.

## User Workflow

```mermaid
flowchart TD
    Start[Start pyvaGUI] --> Project[Create, open, or save a project]
    Project --> Materials[Create or copy materials]
    Materials --> Library{Use material library?}
    Library -->|Yes| Copy[Select or import material copies]
    Library -->|No| Layup[Create a layup]
    Copy --> Layup
    Layup --> Layers[Add, edit, perforate, and reorder layers]
    Layers --> Preview[Inspect stack preview]
    Preview --> Solver[Create a solver preset]
    Solver --> Select[Select fluids, frequency range, angle, and layups]
    Select --> Validate[Validate project and solver]
    Validate -->|Errors| Fix[Correct highlighted settings]
    Fix --> Solver
    Validate -->|Valid| Worker[Run in a QThread worker]
    Worker --> Progress[Show progress and log messages]
    Progress --> Result[Update solver result tab and plot]
    Result --> View{Impedance result?}
    View -->|Yes| Complex[Choose magnitude, phase, real, or imaginary]
    View -->|No| Export[Export CSV or PNG/SVG]
    Complex --> Export
    Export --> Project
```

## Data and Units

- Project files use the `.pyvagui` extension and contain the existing JSON
  structure with `format_version: 1`, materials, layups, and solvers. The
  extension changes; the serialized project content does not. Files do not
  store window state or calculated results.
- The material library is stored separately under
  `%APPDATA%/pyvaGUI/library.json` on Windows or `~/.pyvagui/library.json`
  on other platforms. Missing libraries are initialized from bundled
  materials.
- Physical model values use SI units. Layup and perforation length fields
  display millimeters in the GUI and convert to meters before saving.
- Frequency samples preserve start, end, and point count with logarithmic
  spacing; they are not necessarily exact third-octave center frequencies.
- Solver angles are entered in degrees and converted to radians at the
  pyva boundary. Diffuse solvers default to a maximum angle of 78 degrees.

## Verification

Run the complete suite with `python -m pytest` and check style with
`flake8`. Model tests exercise serialization, validation, library file
operations, and all six pyva solver methods. GUI tests use pytest-qt and
temporary directories; they cover project workflows, editor dialogs,
worker signals, plotting, and exports.
