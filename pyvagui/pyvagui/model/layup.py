"""Layer and layup specifications for infinite-layer calculations.

The model stores layers as plain Python data. It validates those values
and converts them to pyva objects only when a calculation model is built.
All physical values are in SI units.
"""

import math
from dataclasses import dataclass, field
from enum import Enum

import pyva.models as pyva_models
import pyva.systems.infiniteLayers as pyva_layers
from pyva.properties.structuralPropertyClasses import PlateProp

from pyvagui.model.materials import (
    DelanyBazleySpec,
    EquivalentFluidSpec,
    FluidSpec,
    IsoMatSpec,
    MaterialSpec,
    PoroElasticMatSpec,
    new_id,
)


class LayerType(Enum):
    """Representation of a material inside an infinite-layer layup."""

    FLUID = "fluid"
    POROELASTIC = "poroelastic"
    SOLID = "solid"
    PLATE = "plate"
    MASS = "mass"


@dataclass(kw_only=True)
class PerforationSpec:
    """Dimensions of a square perforation pattern.

    Parameters
    ----------
    hole_radius : float
        Radius of each hole [m].
    distance : float
        Center-to-center spacing between holes [m].
    """

    hole_radius: float
    distance: float

    def to_pyva(self, thickness: float) -> pyva_layers.PerforatedLayer:
        """Create the pyva perforation for its host layer.

        The host thickness is required because pyva uses it in the
        perforation's transfer resistance and reactance.

        Parameters
        ----------
        thickness : float
            Thickness of the perforated host layer [m].

        Returns
        -------
        pyva.systems.infiniteLayers.PerforatedLayer
            Perforation object accepted by pyva plate and mass layers.
        """
        # pyva calculates the transfer impedance of a square hole pattern.
        return pyva_layers.PerforatedLayer(
            thickness=thickness,
            hole_radius=self.hole_radius,
            distance=self.distance,
        )

    def to_dict(self) -> dict[str, float]:
        """Convert the perforation dimensions to a JSON-ready dictionary.

        Returns
        -------
        dict of str to float
            Hole radius and center-to-center distance in meters.
        """
        return {
            "hole_radius": self.hole_radius,
            "distance": self.distance,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> "PerforationSpec":
        """Create a perforation specification from serialized values.

        Parameters
        ----------
        data : dict of str to float
            Dictionary created by :meth:`to_dict`.

        Returns
        -------
        PerforationSpec
            Restored perforation specification.
        """
        return cls(
            hole_radius=data["hole_radius"],
            distance=data["distance"],
        )

    def validate(self) -> list[str]:
        """Check that holes are finite, positive, and do not overlap.

        Returns
        -------
        list of str
            Validation errors, or an empty list if the values are valid.
        """
        errors = []
        radius_is_valid = math.isfinite(self.hole_radius) and (
            self.hole_radius > 0
        )
        distance_is_valid = math.isfinite(self.distance) and (
            self.distance > 0
        )
        if not radius_is_valid:
            errors.append("Hole radius must be finite and > 0.")
        if not distance_is_valid:
            errors.append("Hole distance must be finite and > 0.")
        if radius_is_valid and distance_is_valid:
            if 2 * self.hole_radius >= self.distance:
                errors.append(
                    "Hole diameter must be smaller than hole distance."
                )
        return errors


@dataclass(kw_only=True)
class LayerSpec:
    """One material layer in a layup.

    Parameters
    ----------
    material_id : str
        Identifier of the material used by this layer.
    thickness : float
        Layer thickness [m].
    layer_type : LayerType
        Infinite-layer representation used for the material.
    perforation : PerforationSpec or None, optional
        Optional perforation for a plate or mass layer.
    """

    material_id: str
    thickness: float
    layer_type: LayerType
    perforation: PerforationSpec | None = None

    @staticmethod
    def allowed_types(material: MaterialSpec) -> list[LayerType]:
        """Return layer representations supported by a material.

        Parameters
        ----------
        material : MaterialSpec
            Material whose supported layer types are requested.

        Returns
        -------
        list of LayerType
            Supported representations, or an empty list for an unknown
            material type.
        """
        if isinstance(
            material,
            (FluidSpec, EquivalentFluidSpec, DelanyBazleySpec),
        ):
            return [LayerType.FLUID]
        if isinstance(material, PoroElasticMatSpec):
            return [LayerType.POROELASTIC]
        if isinstance(material, IsoMatSpec):
            return [LayerType.SOLID, LayerType.PLATE, LayerType.MASS]
        return []

    def build(
        self, materials: dict[str, MaterialSpec]
    ) -> pyva_layers.AcousticLayer:
        """Build the matching pyva infinite-layer object.

        Parameters
        ----------
        materials : dict of str to MaterialSpec
            Project materials, keyed by their identifiers.

        Returns
        -------
        pyva.systems.infiniteLayers.AcousticLayer
            pyva layer corresponding to this specification.

        Raises
        ------
        ValueError
            If this layer fails validation.
        """
        errors = self.validate(materials)
        if errors:
            raise ValueError("Cannot build layer: " + " ".join(errors))

        material = materials[self.material_id]
        # Material specs convert their values to the matching pyva class.
        pyva_material = material.to_pyva(materials)
        pyva_perforation = None
        if self.perforation is not None:
            pyva_perforation = self.perforation.to_pyva(self.thickness)

        match self.layer_type:
            case LayerType.FLUID:
                # FluidLayer models a fluid-like material at this thickness.
                return pyva_layers.FluidLayer(
                    self.thickness,
                    pyva_material,
                )
            case LayerType.POROELASTIC:
                # PoroElasticLayer applies the Biot-Allard material model.
                return pyva_layers.PoroElasticLayer(
                    pyva_material,
                    self.thickness,
                )
            case LayerType.SOLID:
                # PlateProp combines the layer thickness and frame material.
                plate_property = PlateProp(self.thickness, pyva_material)
                # SolidLayer models longitudinal and shear waves in the solid.
                return pyva_layers.SolidLayer(plate_property)
            case LayerType.PLATE:
                # PlateProp supplies the bending properties for a plate.
                plate_property = PlateProp(self.thickness, pyva_material)
                # PlateLayer models an infinite plate, optionally perforated.
                return pyva_layers.PlateLayer(
                    plate_property,
                    perforation=pyva_perforation,
                )
            case LayerType.MASS:
                # MassLayer uses the solid density multiplied by thickness.
                return pyva_layers.MassLayer(
                    self.thickness,
                    pyva_material.rho0,
                    perforation=pyva_perforation,
                )

        raise ValueError(f"Unsupported layer type: {self.layer_type!r}.")

    def validate(self, materials: dict[str, MaterialSpec]) -> list[str]:
        """Check the material, representation, dimensions, and perforation.

        Parameters
        ----------
        materials : dict of str to MaterialSpec
            Project materials, keyed by their identifiers.

        Returns
        -------
        list of str
            Validation errors, or an empty list if the layer is valid.
        """
        errors = []
        if not math.isfinite(self.thickness) or self.thickness <= 0:
            errors.append("Thickness must be finite and > 0.")

        material = materials.get(self.material_id)
        if material is None:
            errors.append("Material does not exist in the project.")
        elif not isinstance(self.layer_type, LayerType):
            errors.append("Layer type is invalid.")
        elif self.layer_type not in self.allowed_types(material):
            errors.append(
                f"Layer type '{self.layer_type.value}' is not allowed "
                f"for material '{material.name}'."
            )

        if self.perforation is not None:
            if self.layer_type not in (LayerType.PLATE, LayerType.MASS):
                errors.append(
                    "Perforation is only allowed for plate and mass layers."
                )
            errors.extend(self.perforation.validate())
        return errors

    def to_dict(self) -> dict:
        """Convert the layer specification to JSON-ready values.

        Returns
        -------
        dict
            Layer fields with the enum stored by its string value.
        """
        perforation_data = None
        if self.perforation is not None:
            perforation_data = self.perforation.to_dict()
        return {
            "material_id": self.material_id,
            "thickness": self.thickness,
            "layer_type": self.layer_type.value,
            "perforation": perforation_data,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LayerSpec":
        """Create a layer specification from serialized values.

        Parameters
        ----------
        data : dict
            Dictionary created by :meth:`to_dict`.

        Returns
        -------
        LayerSpec
            Restored layer specification.
        """
        perforation_data = data.get("perforation")
        perforation = None
        if perforation_data is not None:
            perforation = PerforationSpec.from_dict(perforation_data)
        return cls(
            material_id=data["material_id"],
            thickness=data["thickness"],
            layer_type=LayerType(data["layer_type"]),
            perforation=perforation,
        )


@dataclass(kw_only=True)
class Layup:
    """Named, ordered sequence of layer specifications.

    Parameters
    ----------
    id : str
        Unique layup identifier, created automatically.
    name : str
        User-visible layup name.
    layers : list of LayerSpec
        Layers ordered from incident side to receiving side.
    """

    id: str = field(default_factory=new_id)
    name: str = "New layup"
    layers: list[LayerSpec] = field(default_factory=list)

    def add_layer(self, layer: LayerSpec) -> None:
        """Append a layer to the receiving side of the layup.

        Parameters
        ----------
        layer : LayerSpec
            Layer to append.
        """
        self.layers.append(layer)

    def remove_layer(self, index: int) -> LayerSpec:
        """Remove and return the layer at an index.

        Parameters
        ----------
        index : int
            Zero-based layer index.

        Returns
        -------
        LayerSpec
            Removed layer.

        Raises
        ------
        IndexError
            If the index does not identify a layer.
        """
        self._check_index(index)
        return self.layers.pop(index)

    def move_layer(self, source: int, target: int) -> None:
        """Move a layer to a new zero-based position.

        Parameters
        ----------
        source : int
            Current layer index.
        target : int
            Destination index after the move.

        Raises
        ------
        IndexError
            If either index does not identify a position in the layup.
        """
        self._check_index(source)
        self._check_index(target)
        layer = self.layers.pop(source)
        self.layers.insert(target, layer)

    def total_thickness(self) -> float:
        """Return the sum of all layer thicknesses [m].

        Returns
        -------
        float
            Total layup thickness in meters.
        """
        return sum(layer.thickness for layer in self.layers)

    def build_tmmodel(
        self, materials: dict[str, MaterialSpec]
    ) -> pyva_models.TMmodel:
        """Build a pyva transfer-matrix model in incident-side order.

        Parameters
        ----------
        materials : dict of str to MaterialSpec
            Project materials, keyed by their identifiers.

        Returns
        -------
        pyva.models.TMmodel
            Model containing the layup's pyva layers in stored order.

        Raises
        ------
        ValueError
            If the layup or any layer fails validation.
        """
        errors = self.validate(materials)
        if errors:
            raise ValueError("Cannot build layup: " + " ".join(errors))

        pyva_layer_objects = tuple(
            layer.build(materials) for layer in self.layers
        )
        # TMmodel combines the infinite layers in incident-to-receiving order.
        return pyva_models.TMmodel(pyva_layer_objects)

    def validate(self, materials: dict[str, MaterialSpec]) -> list[str]:
        """Validate the layup and prefix errors with their layer number.

        Parameters
        ----------
        materials : dict of str to MaterialSpec
            Project materials, keyed by their identifiers.

        Returns
        -------
        list of str
            Layup and layer errors, or an empty list if valid.
        """
        errors = []
        if not self.layers:
            errors.append("Layup must contain at least one layer.")
        for index, layer in enumerate(self.layers, start=1):
            for error in layer.validate(materials):
                errors.append(f"Layer {index}: {error}")
        return errors

    def to_dict(self) -> dict:
        """Convert the layup and its layers to JSON-ready values.

        Returns
        -------
        dict
            Layup identifier, name, and ordered layer dictionaries.
        """
        return {
            "id": self.id,
            "name": self.name,
            "layers": [layer.to_dict() for layer in self.layers],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Layup":
        """Create a layup from serialized values.

        Parameters
        ----------
        data : dict
            Dictionary created by :meth:`to_dict`.

        Returns
        -------
        Layup
            Restored layup with its original layer order.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            layers=[LayerSpec.from_dict(layer) for layer in data["layers"]],
        )

    def _check_index(self, index: int) -> None:
        """Raise an error unless an index identifies an existing layer.

        Parameters
        ----------
        index : int
            Layer index to check.

        Raises
        ------
        IndexError
            If the index is negative or outside the layer list.
        """
        if not 0 <= index < len(self.layers):
            raise IndexError("Layer index is out of range.")
