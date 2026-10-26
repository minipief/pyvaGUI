"""Material specifications of pyvaGUI.

A material specification ("spec") stores the parameters of one pyva
material as plain Python values. Specs can be saved to JSON and are
turned into real pyva objects with :meth:`MaterialSpec.to_pyva` right
before a calculation.

All physical values are given in SI units.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field, replace
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    import pyva.properties.materialClasses as matC


def new_id() -> str:
    """Create a new unique identifier.

    Returns
    -------
    str
        Random 32 character hexadecimal string.
    """
    return uuid.uuid4().hex


def check_positive(name: str, values: dict[str, float]) -> list[str]:
    """Return an error message for every value that is not positive.

    Parameters
    ----------
    name : str
        Name of the material, used as prefix of the messages.
    values : dict of str to float
        Readable parameter label mapped to its value.

    Returns
    -------
    list of str
        One error message per value that is <= 0.

    Examples
    --------
    >>> check_positive("Air", {"density": -1.0})
    ['Air: density must be > 0.']
    """
    errors = []
    for label, value in values.items():
        if value <= 0:
            errors.append(f"{name}: {label} must be > 0.")
    return errors


@dataclass(kw_only=True)
class MaterialSpec(ABC):
    """Abstract base class of all material specifications.

    Parameters
    ----------
    name : str
        Name shown in the user interface.
    id : str
        Unique identifier, created automatically.
    """

    type_name: ClassVar[str] = ""

    name: str = "New material"
    id: str = field(default_factory=new_id)

    @abstractmethod
    def to_pyva(self, materials: dict[str, "MaterialSpec"]):
        """Create the pyva material object.

        Parameters
        ----------
        materials : dict of str to MaterialSpec
            All materials of the project, keyed by their id. Only
            needed by materials that reference other materials.

        Returns
        -------
        object
            Instance of a class of ``pyva.properties.materialClasses``.
        """

    @abstractmethod
    def validate(self) -> list[str]:
        """Check the parameters for physically valid values.

        Returns
        -------
        list of str
            Error messages. An empty list means the material is valid.
        """

    def to_dict(self) -> dict:
        """Convert the material to a dictionary for JSON export.

        Returns
        -------
        dict
            All fields plus the key ``"type"`` with the material type.
        """
        data = asdict(self)
        data["type"] = self.type_name
        return data

    def copy_with_new_id(self) -> "MaterialSpec":
        """Return a copy of the material with a new identifier.

        Used when a material is copied from the library into a project.

        Returns
        -------
        MaterialSpec
            Copy with identical parameters but a new ``id``.
        """
        return replace(self, id=new_id())


@dataclass(kw_only=True)
class FluidPropertiesSpec(MaterialSpec):
    """Fluid properties shared by fluid and porous materials.

    This class is not used directly. It only collects the fields that
    all fluid-like pyva materials have in common.

    Parameters
    ----------
    c0 : float
        Speed of sound [m/s].
    rho0 : float
        Density [kg/m^3].
    dynamic_viscosity : float
        Dynamic viscosity [Pa s].
    kappa : float
        Ratio of specific heat capacities [-].
    Cp : float
        Specific heat capacity at constant pressure [J/(kg K)].
    heat_conductivity : float
        Heat conductivity [W/(m K)].
    """

    c0: float = 343.0
    rho0: float = 1.23
    dynamic_viscosity: float = 1.84e-5
    kappa: float = 1.4
    Cp: float = 1005.1
    heat_conductivity: float = 0.0257673

    def validate_fluid_properties(self) -> list[str]:
        """Check all shared fluid properties.

        Returns
        -------
        list of str
            Error messages, empty if all values are valid.
        """
        return check_positive(self.name, {
            "speed of sound": self.c0,
            "density": self.rho0,
            "dynamic viscosity": self.dynamic_viscosity,
            "ratio of specific heats": self.kappa,
            "heat capacity": self.Cp,
            "heat conductivity": self.heat_conductivity,
        })


@dataclass(kw_only=True)
class DampedFluidPropertiesSpec(FluidPropertiesSpec):
    """Fluid properties plus a damping loss factor.

    Parameters
    ----------
    eta : float
        Damping loss factor [-].
    """

    eta: float = 0.01

    def validate_fluid_properties(self) -> list[str]:
        """Check the shared fluid properties and the loss factor.

        Returns
        -------
        list of str
            Error messages, empty if all values are valid.
        """
        errors = super().validate_fluid_properties()
        if self.eta < 0:
            errors.append(f"{self.name}: loss factor must be >= 0.")
        return errors


@dataclass(kw_only=True)
class FluidSpec(DampedFluidPropertiesSpec):
    """Specification of a fluid, e.g. air or water.

    All parameters are inherited from :class:`DampedFluidPropertiesSpec`.
    """

    type_name: ClassVar[str] = "fluid"

    def to_pyva(self, materials: dict[str, MaterialSpec]) -> matC.Fluid:
        """Create a :class:`pyva.properties.materialClasses.Fluid`.

        Parameters
        ----------
        materials : dict of str to MaterialSpec
            Not used, a fluid does not reference other materials.

        Returns
        -------
        matC.Fluid
            The pyva fluid object.
        """
        import pyva.properties.materialClasses as matC

        return matC.Fluid(
            c0=self.c0,
            rho0=self.rho0,
            eta=self.eta,
            dynamic_viscosity=self.dynamic_viscosity,
            kappa=self.kappa,
            Cp=self.Cp,
            heat_conductivity=self.heat_conductivity,
        )

    def validate(self) -> list[str]:
        """Check all parameters of the fluid.

        Returns
        -------
        list of str
            Error messages, empty if the fluid is valid.
        """
        return self.validate_fluid_properties()


@dataclass(kw_only=True)
class EquivalentFluidSpec(DampedFluidPropertiesSpec):
    """Fibre or foam material with rigid or limp frame (Champoux-Allard).

    The default values describe a typical fibre material.

    Parameters
    ----------
    flow_res : float
        Flow resistivity [Pa s/m^2].
    porosity : float
        Volume porosity [-], 0 < porosity <= 1.
    tortuosity : float
        Tortuosity [-], >= 1.
    rho_bulk : float
        Apparent density of fluid and frame [kg/m^3].
    length_visc : float
        Viscous characteristic length [m].
    length_therm : float
        Thermal characteristic length [m].
    limp : bool
        True for the limp frame model, False for the rigid frame model.
    """

    type_name: ClassVar[str] = "equivalent_fluid"

    flow_res: float = 25000.0
    porosity: float = 0.98
    tortuosity: float = 1.02
    rho_bulk: float = 31.176
    length_visc: float = 90.0e-6
    length_therm: float = 180.0e-6
    limp: bool = True

    def to_pyva(
        self, materials: dict[str, MaterialSpec]
    ) -> matC.EquivalentFluid:
        """Create a :class:`pyva.properties.materialClasses.EquivalentFluid`.

        Parameters
        ----------
        materials : dict of str to MaterialSpec
            Not used, an equivalent fluid does not reference other
            materials.

        Returns
        -------
        matC.EquivalentFluid
            The pyva equivalent fluid object.
        """
        import pyva.properties.materialClasses as matC

        return matC.EquivalentFluid(
            flow_res=self.flow_res,
            porosity=self.porosity,
            tortuosity=self.tortuosity,
            rho_bulk=self.rho_bulk,
            length_visc=self.length_visc,
            length_therm=self.length_therm,
            limp=self.limp,
            c0=self.c0,
            rho0=self.rho0,
            eta=self.eta,
            dynamic_viscosity=self.dynamic_viscosity,
            kappa=self.kappa,
            Cp=self.Cp,
            heat_conductivity=self.heat_conductivity,
        )

    def validate(self) -> list[str]:
        """Check all parameters of the equivalent fluid.

        Returns
        -------
        list of str
            Error messages, empty if the material is valid.
        """
        errors = self.validate_fluid_properties()
        errors += check_positive(self.name, {
            "flow resistivity": self.flow_res,
            "bulk density": self.rho_bulk,
            "viscous length": self.length_visc,
            "thermal length": self.length_therm,
        })
        if not 0 < self.porosity <= 1:
            errors.append(f"{self.name}: porosity must be in (0, 1].")
        if self.tortuosity < 1:
            errors.append(f"{self.name}: tortuosity must be >= 1.")
        return errors


@dataclass(kw_only=True)
class DelanyBazleySpec(DampedFluidPropertiesSpec):
    """Fibre material after the empirical Delany-Bazley or Miki model.

    Parameters
    ----------
    flow_res : float
        Flow resistivity [Pa s/m^2].
    miki : bool
        True for the Miki model, False for the Delany-Bazley model.
    """

    type_name: ClassVar[str] = "delany_bazley"

    flow_res: float = 25000.0
    miki: bool = False

    def to_pyva(
        self, materials: dict[str, MaterialSpec]
    ) -> matC.DelanyBazley:
        """Create a :class:`pyva.properties.materialClasses.DelanyBazley`.

        Parameters
        ----------
        materials : dict of str to MaterialSpec
            Not used, this material does not reference other materials.

        Returns
        -------
        matC.DelanyBazley
            The pyva Delany-Bazley object.
        """
        import pyva.properties.materialClasses as matC

        return matC.DelanyBazley(
            flow_res=self.flow_res,
            c0=self.c0,
            rho0=self.rho0,
            eta=self.eta,
            dynamic_viscosity=self.dynamic_viscosity,
            kappa=self.kappa,
            Cp=self.Cp,
            heat_conductivity=self.heat_conductivity,
            miki=self.miki,
        )

    def validate(self) -> list[str]:
        """Check all parameters of the Delany-Bazley material.

        Returns
        -------
        list of str
            Error messages, empty if the material is valid.
        """
        errors = self.validate_fluid_properties()
        errors += check_positive(
            self.name, {"flow resistivity": self.flow_res}
        )
        return errors


@dataclass(kw_only=True)
class IsoMatSpec(MaterialSpec):
    """Isotropic solid material, e.g. steel or aluminium.

    The default values describe aluminium.

    Parameters
    ----------
    E : float
        Young's modulus [Pa].
    rho0 : float
        Density [kg/m^3].
    nu : float
        Poisson ratio [-], 0 <= nu < 0.5.
    eta : float
        Damping loss factor [-].
    """

    type_name: ClassVar[str] = "isomat"

    E: float = 7.1e10
    rho0: float = 2700.0
    nu: float = 0.34
    eta: float = 0.01

    def to_pyva(self, materials: dict[str, MaterialSpec]) -> matC.IsoMat:
        """Create a :class:`pyva.properties.materialClasses.IsoMat`.

        Parameters
        ----------
        materials : dict of str to MaterialSpec
            Not used, a solid does not reference other materials.

        Returns
        -------
        matC.IsoMat
            The pyva isotropic material object.
        """
        import pyva.properties.materialClasses as matC

        return matC.IsoMat(
            E=self.E,
            rho0=self.rho0,
            nu=self.nu,
            eta=self.eta,
        )

    def validate(self) -> list[str]:
        """Check all parameters of the solid material.

        Returns
        -------
        list of str
            Error messages, empty if the material is valid.
        """
        errors = check_positive(self.name, {
            "Young's modulus": self.E,
            "density": self.rho0,
        })
        if not 0 <= self.nu < 0.5:
            errors.append(f"{self.name}: Poisson ratio must be in [0, 0.5).")
        if self.eta < 0:
            errors.append(f"{self.name}: loss factor must be >= 0.")
        return errors


@dataclass(kw_only=True)
class PoroElasticMatSpec(FluidPropertiesSpec):
    """Poro-elastic material (e.g. foam) according to Biot-Allard.

    The elastic frame is a separate :class:`IsoMatSpec` that is
    referenced by its id. pyva's PoroElasticMat has no ``eta`` and no
    ``rho_bulk``, so this class inherits from
    :class:`FluidPropertiesSpec` and not from the damped variant.

    Parameters
    ----------
    solid_mat_id : str
        Id of the IsoMatSpec of the frame material.
    flow_res : float
        Flow resistivity [Pa s/m^2].
    porosity : float
        Volume porosity [-], 0 < porosity <= 1.
    tortuosity : float
        Tortuosity [-], >= 1.
    length_visc : float
        Viscous characteristic length [m].
    length_therm : float
        Thermal characteristic length [m].
    limp : bool
        True for the limp frame model. The default is False (as in pyva).
    """

    type_name: ClassVar[str] = "poroelastic"

    solid_mat_id: str = ""
    flow_res: float = 25000.0
    porosity: float = 0.98
    tortuosity: float = 1.02
    length_visc: float = 90.0e-6
    length_therm: float = 180.0e-6
    limp: bool = False

    def to_pyva(
        self, materials: dict[str, MaterialSpec]
    ) -> matC.PoroElasticMat:
        """Create a :class:`pyva.properties.materialClasses.PoroElasticMat`.

        Parameters
        ----------
        materials : dict of str to MaterialSpec
            All materials of the project. Must contain the frame
            material with the id ``solid_mat_id``.

        Returns
        -------
        matC.PoroElasticMat
            The pyva poro-elastic material object.

        Raises
        ------
        ValueError
            If ``solid_mat_id`` does not belong to an IsoMatSpec in
            ``materials``.
        """
        solid = materials.get(self.solid_mat_id)
        if not isinstance(solid, IsoMatSpec):
            raise ValueError(
                f"{self.name}: frame material must be an Isomat."
            )
        import pyva.properties.materialClasses as matC

        return matC.PoroElasticMat(
            solid_mat=solid.to_pyva(materials),
            flow_res=self.flow_res,
            porosity=self.porosity,
            tortuosity=self.tortuosity,
            length_visc=self.length_visc,
            length_therm=self.length_therm,
            limp=self.limp,
            c0=self.c0,
            rho0=self.rho0,
            dynamic_viscosity=self.dynamic_viscosity,
            kappa=self.kappa,
            Cp=self.Cp,
            heat_conductivity=self.heat_conductivity,
        )

    def validate(self) -> list[str]:
        """Check all parameters of the poro-elastic material.

        Whether the referenced frame material exists is checked by the
        project, because only the project knows all materials.

        Returns
        -------
        list of str
            Error messages, empty if the material is valid.
        """
        errors = self.validate_fluid_properties()
        if self.solid_mat_id == "":
            errors.append(f"{self.name}: no frame material selected.")
        errors += check_positive(self.name, {
            "flow resistivity": self.flow_res,
            "viscous length": self.length_visc,
            "thermal length": self.length_therm,
        })
        if not 0 < self.porosity <= 1:
            errors.append(f"{self.name}: porosity must be in (0, 1].")
        if self.tortuosity < 1:
            errors.append(f"{self.name}: tortuosity must be >= 1.")
        return errors


def material_from_dict(data: dict) -> MaterialSpec:
    """Create the matching material specification from a dictionary.

    Parameters
    ----------
    data : dict
        Dictionary created by :meth:`MaterialSpec.to_dict`.

    Returns
    -------
    MaterialSpec
        Instance of the subclass given by ``data["type"]``.

    Raises
    ------
    ValueError
        If the material type is unknown.
    """
    data = dict(data)  # copy, so the dictionary of the caller is unchanged
    type_name = data.pop("type")
    match type_name:
        case FluidSpec.type_name:
            return FluidSpec(**data)
        case EquivalentFluidSpec.type_name:
            return EquivalentFluidSpec(**data)
        case DelanyBazleySpec.type_name:
            return DelanyBazleySpec(**data)
        case IsoMatSpec.type_name:
            return IsoMatSpec(**data)
        case PoroElasticMatSpec.type_name:
            return PoroElasticMatSpec(**data)
    raise ValueError(f"Unknown material type: {type_name}")
