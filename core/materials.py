import pyva.properties.materialClasses as matC

class Material:
    """Basis Material Class"""
    
    def __init__(self, name, c0 = 343.0, rho0 = 1.23):
        self.name = name
        self.c0 = c0
        self.rho0 = rho0
        
    def beschreibung(self):
        return f"{self.name}: c0={self.c0}, rho0={self.rho0}"
    
    def to_dict(self):
        return {"typ": "Material", "name": self.name,
                "c0": self.c0, "rho0": self.rho0}
    
class Fluid(Material):
    def to_pyva(self):
        return matC.Fluid(c0=self.c0, rho0=self.rho0)
    
    def to_dict(self):
        daten = super().to_dict()
        daten["typ"] = "Fluid"
        return daten

class EquivalentFluid(Fluid):
    def __init__(self, name, porosity, flow_res, tortuosity=1.0,
                rho_bulk=30.0, length_visc=90e-6, length_therm=180e-6,
                c0=343.0, rho0=1.23):
        super().__init__(name, c0, rho0)
        self.porosity = porosity
        self.flow_res = flow_res
        self.tortuosity = tortuosity
        self.rho_bulk = rho_bulk
        self.length_visc = length_visc
        self.length_therm = length_therm
        
    def beschreibung(self):
        basis = super().beschreibung()
        return f"{basis}, porosity = {self.porosity}, flow_res = {self.flow_res}, tortuosity = {self.tortuosity}"
    
    def to_pyva(self):
        return matC.EquivalentFluid(flow_res=self.flow_res,
                                    porosity=self.porosity,
                                    tortuosity=self.tortuosity,
                                    rho_bulk=self.rho_bulk,
                                    length_visc=self.length_visc,
                                    length_therm=self.length_therm,
                                    c0=self.c0, rho0=self.rho0)
        
    def to_dict(self):
        daten = super().to_dict()
        daten["typ"] = "EquivalentFluid"
        daten["porosity"] = self.porosity
        daten["flow_res"] = self.flow_res
        daten["tortuosity"] = self.tortuosity
        daten["rho_bulk"] = self.rho_bulk
        daten["length_visc"] = self.length_visc
        daten["length_therm"] = self.length_therm
        return daten

def material_from_dict(daten):
    typ = daten["typ"]
    
    match typ:
        case "Fluid":
            return Fluid(name=daten["name"],
                         c0=daten["c0"],
                         rho0=daten["rho0"])
        case "EquivalentFluid":
            return EquivalentFluid(name=daten["name"],
                                   porosity=daten["porosity"],
                                   flow_res=daten["flow_res"],
                                   tortuosity=daten["tortuosity"],
                                   c0=daten["c0"],
                                   rho0=daten["rho0"],
                                   rho_bulk=daten["rho_bulk"],
                                   length_visc=daten["length_visc"],
                                   length_therm=daten["length_therm"])
        case _:
            raise ValueError(f"Unbekannter Materialtyp: {typ}")