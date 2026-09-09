"""Materialmodelle und Konvertierung in pyva-Materialklassen.

Das Modul definiert die in Projekten und der Materialbibliothek verwendeten
Fluid-, Festkörper- und poroelastischen Modelle samt JSON-Serialisierung.
"""

import pyva.properties.materialClasses as matC

class Material:
	"""Basismodell gemeinsamer akustischer und thermischer Materialgrößen."""
	
	def __init__(self, name, c0=343.0, rho0=1.23, eta=0.01,
				dynamic_viscosity=1.84e-5, kappa=1.4, Cp=1005.1,
				heat_conductivity=0.0257673):
		"""Initialisiert die gemeinsamen Materialparameter.

		Args:
			name: Eindeutige Bezeichnung des Materials.
			c0: Schallgeschwindigkeit in Metern pro Sekunde.
			rho0: Dichte in Kilogramm pro Kubikmeter.
			eta: Verlustfaktor.
			dynamic_viscosity: Dynamische Viskosität in Pascalsekunden.
			kappa: Adiabatenexponent.
			Cp: Spezifische Wärmekapazität bei konstantem Druck.
			heat_conductivity: Wärmeleitfähigkeit.
		"""
		self.name = name
		self.c0 = c0
		self.rho0 = rho0
		self.eta = eta
		self.dynamic_viscosity = dynamic_viscosity
		self.kappa = kappa
		self.Cp = Cp
		self.heat_conductivity = heat_conductivity
		
	def beschreibung(self):
		"""Erzeugt eine kompakte textuelle Materialbeschreibung.

		Returns:
			Materialname sowie Schallgeschwindigkeit, Dichte und Verlustfaktor.
		"""
		return f"{self.name}: c0={self.c0}, rho0={self.rho0}, eta={self.eta}"
	
	def to_dict(self):
		"""Serialisiert die gemeinsamen Materialparameter.

		Returns:
			JSON-kompatibles Dictionary des Basismaterials.
		"""
		return {"typ": "Material", "name": self.name,
				"c0": self.c0, "rho0": self.rho0, "eta": self.eta,
				"dynamic_viscosity": self.dynamic_viscosity,
				"kappa": self.kappa, "Cp": self.Cp,
				"heat_conductivity": self.heat_conductivity}
	
class Fluid(Material):
	"""Beschreibt ein homogenes Fluid für akustische Berechnungen."""

	def to_pyva(self):
		"""Konvertiert das Fluid in ein pyva-Material.

		Returns:
			Fluidinstanz aus ``pyva.properties.materialClasses``.
		"""
		return matC.Fluid(c0=self.c0, rho0=self.rho0, eta=self.eta,
						  dynamic_viscosity=self.dynamic_viscosity,
						  kappa=self.kappa, Cp=self.Cp,
						  heat_conductivity=self.heat_conductivity)
	
	def to_dict(self):
		"""Serialisiert das Fluid.

		Returns:
			JSON-kompatibles Dictionary mit dem Typ ``Fluid``.
		"""
		daten = super().to_dict()
		daten["typ"] = "Fluid"
		return daten

class EquivalentFluid(Fluid):
	"""Modelliert ein poröses Absorbermaterial als äquivalentes Fluid."""

	def __init__(self, name, porosity, flow_res, tortuosity=1.0,
				rho_bulk=30.0, length_visc=90e-6, length_therm=180e-6,
				limp=True, c0=343.0, rho0=1.23, eta=0.0,
				dynamic_viscosity=1.84e-5, kappa=1.4, Cp=1005.1,
				heat_conductivity=0.0257673):
		"""Initialisiert ein äquivalent-fluides Material.

		Args:
			name: Eindeutige Bezeichnung des Materials.
			porosity: Offene Porosität als dimensionsloser Anteil.
			flow_res: Strömungswiderstand.
			tortuosity: Tortuosität des Porenraums.
			rho_bulk: Rohdichte des porösen Materials.
			length_visc: Viskose charakteristische Länge in Metern.
			length_therm: Thermische charakteristische Länge in Metern.
			limp: Ob das Limp-Frame-Modell verwendet wird.
			c0: Schallgeschwindigkeit des Porenfluids in Metern pro Sekunde.
			rho0: Dichte des Porenfluids in Kilogramm pro Kubikmeter.
			eta: Verlustfaktor des Fluids.
			dynamic_viscosity: Dynamische Viskosität des Porenfluids.
			kappa: Adiabatenexponent des Porenfluids.
			Cp: Spezifische Wärmekapazität des Porenfluids.
			heat_conductivity: Wärmeleitfähigkeit des Porenfluids.
		"""
		super().__init__(name, c0, rho0, eta, dynamic_viscosity, kappa, Cp,
						 heat_conductivity)
		self.porosity = porosity
		self.flow_res = flow_res
		self.tortuosity = tortuosity
		self.rho_bulk = rho_bulk
		self.length_visc = length_visc
		self.length_therm = length_therm
		self.limp = limp
		
	def beschreibung(self):
		"""Erzeugt eine Beschreibung der Fluid- und Porenparameter.

		Returns:
			Kompakte textuelle Materialbeschreibung.
		"""
		basis = super().beschreibung()
		return f"{basis}, porosity = {self.porosity}, flow_res = {self.flow_res}, tortuosity = {self.tortuosity}"
	
	def to_pyva(self):
		"""Konvertiert das Modell in ein pyva-Äquivalentfluid.

		Returns:
			Äquivalentfluidinstanz aus pyva.
		"""
		return matC.EquivalentFluid(flow_res=self.flow_res,
									porosity=self.porosity,
									tortuosity=self.tortuosity,
									rho_bulk=self.rho_bulk,
									length_visc=self.length_visc,
									length_therm=self.length_therm,
									limp=self.limp,
									c0=self.c0, rho0=self.rho0, eta=self.eta,
									dynamic_viscosity=self.dynamic_viscosity,
									kappa=self.kappa, Cp=self.Cp,
									heat_conductivity=self.heat_conductivity)
		
	def to_dict(self):
		"""Serialisiert sämtliche Fluid- und Porenparameter.

		Returns:
			JSON-kompatibles Dictionary mit dem Typ ``EquivalentFluid``.
		"""
		daten = super().to_dict()
		daten["typ"] = "EquivalentFluid"
		daten["porosity"] = self.porosity
		daten["flow_res"] = self.flow_res
		daten["tortuosity"] = self.tortuosity
		daten["rho_bulk"] = self.rho_bulk
		daten["length_visc"] = self.length_visc
		daten["length_therm"] = self.length_therm
		daten["limp"] = self.limp
		return daten


class DelanyBazley(Fluid):
	"""Empirisches Fasermodell nach Delany-Bazley beziehungsweise Miki."""

	def __init__(self, name, flow_res, miki=False, c0=343.0, rho0=1.23,
				eta=0.0, dynamic_viscosity=1.84e-5, kappa=1.4, Cp=1005.1,
				heat_conductivity=0.0257673):
		"""Initialisiert das empirische Fasermodell.

		Args:
			name: Eindeutige Bezeichnung des Materials.
			flow_res: Strömungswiderstand des Fasermaterials.
			miki: Verwendet bei ``True`` die Miki-Variante.
			c0: Schallgeschwindigkeit des Umgebungsfluids.
			rho0: Dichte des Umgebungsfluids.
			eta: Verlustfaktor.
			dynamic_viscosity: Dynamische Viskosität.
			kappa: Adiabatenexponent.
			Cp: Spezifische Wärmekapazität.
			heat_conductivity: Wärmeleitfähigkeit.
		"""
		super().__init__(name, c0, rho0, eta, dynamic_viscosity, kappa, Cp,
						 heat_conductivity)
		self.flow_res = flow_res
		self.miki = miki

	def beschreibung(self):
		"""Erzeugt eine Beschreibung einschließlich der Modellvariante.

		Returns:
			Kompakte textuelle Materialbeschreibung.
		"""
		basis = super().beschreibung()
		modell = "Miki" if self.miki else "Delany-Bazley"
		return f"{basis}, flow_res = {self.flow_res}, Modell = {modell}"

	def to_pyva(self):
		"""Konvertiert das Fasermodell in ein pyva-Material.

		Returns:
			Delany-Bazley- beziehungsweise Miki-Instanz aus pyva.
		"""
		return matC.DelanyBazley(flow_res=self.flow_res, miki=self.miki,
								 c0=self.c0, rho0=self.rho0, eta=self.eta,
								 dynamic_viscosity=self.dynamic_viscosity,
								 kappa=self.kappa, Cp=self.Cp,
								 heat_conductivity=self.heat_conductivity)

	def to_dict(self):
		"""Serialisiert das empirische Fasermodell.

		Returns:
			JSON-kompatibles Dictionary mit Modellvariante.
		"""
		daten = super().to_dict()
		daten["typ"] = "DelanyBazley"
		daten["flow_res"] = self.flow_res
		daten["miki"] = self.miki
		return daten


class Solid(Material):
	"""Isotropes, elastisches Festkörpermaterial (entspricht pyva.IsoMat)."""

	def __init__(self, name, E=7.1e10, rho0=2700.0, nu=0.34, eta=0.01):
		"""Initialisiert ein isotropes Festkörpermaterial.

		Args:
			name: Eindeutige Bezeichnung des Materials.
			E: Elastizitätsmodul in Pascal.
			rho0: Festkörperdichte in Kilogramm pro Kubikmeter.
			nu: Poissonzahl.
			eta: Struktureller Verlustfaktor.
		"""
		self.name = name
		self.E = E
		self.rho0 = rho0
		self.nu = nu
		self.eta = eta

	def beschreibung(self):
		"""Erzeugt eine Beschreibung der mechanischen Kennwerte.

		Returns:
			Kompakte textuelle Materialbeschreibung.
		"""
		return f"{self.name}: E={self.E}, rho0={self.rho0}, nu={self.nu}, eta={self.eta}"

	def to_pyva(self):
		"""Konvertiert den Festkörper in ein isotropes pyva-Material.

		Returns:
			Instanz von ``pyva.properties.materialClasses.IsoMat``.
		"""
		return matC.IsoMat(E=self.E, rho0=self.rho0, nu=self.nu, eta=self.eta)

	def to_dict(self):
		"""Serialisiert die mechanischen Materialparameter.

		Returns:
			JSON-kompatibles Dictionary mit dem Typ ``Solid``.
		"""
		return {"typ": "Solid", "name": self.name,
				"E": self.E, "rho0": self.rho0,
				"nu": self.nu, "eta": self.eta}


class PoroElasticMat(EquivalentFluid):
	"""Poroelastisches Material nach Biot (fasriges Skelett + Fluid)."""

	def __init__(self, name, solid_mat, flow_res, porosity, tortuosity,
				length_visc, length_therm, limp=False,
				c0=343.0, rho0=1.23, dynamic_viscosity=1.84e-5,
				kappa=1.4, Cp=1005.1, heat_conductivity=0.0257673):
		"""Initialisiert ein gekoppeltes Rahmen-Fluid-Modell.

		Args:
			name: Eindeutige Bezeichnung des Materials.
			solid_mat: Festkörpermaterial des porösen Rahmens.
			flow_res: Strömungswiderstand.
			porosity: Offene Porosität als dimensionsloser Anteil.
			tortuosity: Tortuosität des Porenraums.
			length_visc: Viskose charakteristische Länge in Metern.
			length_therm: Thermische charakteristische Länge in Metern.
			limp: Ob das Limp-Frame-Modell verwendet wird.
			c0: Schallgeschwindigkeit des Porenfluids.
			rho0: Dichte des Porenfluids.
			dynamic_viscosity: Dynamische Viskosität des Porenfluids.
			kappa: Adiabatenexponent des Porenfluids.
			Cp: Spezifische Wärmekapazität des Porenfluids.
			heat_conductivity: Wärmeleitfähigkeit des Porenfluids.
		"""
		rho_bulk = solid_mat.rho0 + porosity * rho0
		# pyva.PoroElasticMat unterstützt keinen freien Verlustfaktor des Fluids.
		super().__init__(name, porosity, flow_res, tortuosity,
						 rho_bulk, length_visc, length_therm,
						 limp, c0, rho0, 0.0,
						 dynamic_viscosity, kappa, Cp, heat_conductivity)
		self.solid_mat = solid_mat

	def beschreibung(self):
		"""Erzeugt eine Beschreibung einschließlich des Rahmenmaterials.

		Returns:
			Kompakte textuelle Materialbeschreibung.
		"""
		basis = super().beschreibung()
		return f"{basis}, Rahmenmaterial = {self.solid_mat.name}"

	def to_pyva(self):
		"""Konvertiert Rahmen und Porenfluid in ein pyva-Biot-Material.

		Returns:
			Poroelastische Materialinstanz aus pyva.
		"""
		return matC.PoroElasticMat(solid_mat=self.solid_mat.to_pyva(),
								   flow_res=self.flow_res,
								   porosity=self.porosity,
								   tortuosity=self.tortuosity,
								   length_visc=self.length_visc,
								   length_therm=self.length_therm,
								   limp=self.limp,
								   c0=self.c0, rho0=self.rho0,
								   dynamic_viscosity=self.dynamic_viscosity,
								   kappa=self.kappa, Cp=self.Cp,
								   heat_conductivity=self.heat_conductivity)

	def to_dict(self):
		"""Serialisiert das poroelastische Material und seinen Rahmen.

		Returns:
			JSON-kompatibles Dictionary mit eingebettetem Festkörpermaterial.
		"""
		daten = super().to_dict()
		daten["typ"] = "PoroElasticMat"
		daten["solid_mat"] = self.solid_mat.to_dict()
		del daten["rho_bulk"]
		del daten["eta"]
		return daten


def material_from_dict(daten):
	"""Rekonstruiert ein konkretes Material aus serialisierten Daten.

	Args:
		daten: Dictionary mit Materialtyp und den zugehörigen Parametern.

	Returns:
		Instanz der im Feld ``typ`` angegebenen Materialklasse.

	Raises:
		KeyError: Wenn ein erforderlicher Materialparameter fehlt.
		TypeError: Wenn Parameter nicht in der erwarteten Form vorliegen.
		ValueError: Wenn der Materialtyp unbekannt ist.
	"""
	typ = daten["typ"]
	
	match typ:
		case "Fluid":
			return Fluid(name=daten["name"],
						 c0=daten["c0"],
						 rho0=daten["rho0"],
						 eta=daten.get("eta", 0.01),
						 dynamic_viscosity=daten.get("dynamic_viscosity", 1.84e-5),
						 kappa=daten.get("kappa", 1.4),
						 Cp=daten.get("Cp", 1005.1),
						 heat_conductivity=daten.get("heat_conductivity", 0.0257673))
		case "EquivalentFluid":
			return EquivalentFluid(name=daten["name"],
								   porosity=daten["porosity"],
								   flow_res=daten["flow_res"],
								   tortuosity=daten["tortuosity"],
								   c0=daten["c0"],
								   rho0=daten["rho0"],
								   rho_bulk=daten["rho_bulk"],
								   length_visc=daten["length_visc"],
								   length_therm=daten["length_therm"],
								   limp=daten.get("limp", True),
								   eta=daten.get("eta", 0.0),
								   dynamic_viscosity=daten.get("dynamic_viscosity", 1.84e-5),
								   kappa=daten.get("kappa", 1.4),
								   Cp=daten.get("Cp", 1005.1),
								   heat_conductivity=daten.get("heat_conductivity", 0.0257673))
		case "DelanyBazley":
			return DelanyBazley(name=daten["name"],
								flow_res=daten["flow_res"],
								miki=daten.get("miki", False),
								c0=daten["c0"],
								rho0=daten["rho0"],
								eta=daten.get("eta", 0.0),
								dynamic_viscosity=daten.get("dynamic_viscosity", 1.84e-5),
								kappa=daten.get("kappa", 1.4),
								Cp=daten.get("Cp", 1005.1),
								heat_conductivity=daten.get("heat_conductivity", 0.0257673))
		case "Solid":
			return Solid(name=daten["name"],
						E=daten["E"],
						rho0=daten["rho0"],
						nu=daten["nu"],
						eta=daten["eta"])
		case "PoroElasticMat":
			solid_mat = material_from_dict(daten["solid_mat"])
			return PoroElasticMat(name=daten["name"],
								  solid_mat=solid_mat,
								  flow_res=daten["flow_res"],
								  porosity=daten["porosity"],
								  tortuosity=daten["tortuosity"],
								  length_visc=daten["length_visc"],
								  length_therm=daten["length_therm"],
								  limp=daten.get("limp", False),
								  c0=daten["c0"],
								  rho0=daten["rho0"],
								  dynamic_viscosity=daten.get("dynamic_viscosity", 1.84e-5),
								  kappa=daten.get("kappa", 1.4),
								  Cp=daten.get("Cp", 1005.1),
								  heat_conductivity=daten.get("heat_conductivity", 0.0257673))
		case _:
			raise ValueError(f"Unbekannter Materialtyp: {typ}")