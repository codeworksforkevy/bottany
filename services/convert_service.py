
from pint import UnitRegistry
from services.constants import load_constants
from services.ucum_loader import load_ucum_units

_ureg = None

def get_registry():
    global _ureg
    if _ureg is None:
        _ureg = UnitRegistry()
        load_constants(_ureg)
        load_ucum_units(_ureg)
    return _ureg

def convert_units(value: float, from_unit: str, to_unit: str):
    ureg = get_registry()
    quantity = value * ureg(from_unit)
    return quantity.to(to_unit)

def list_units():
    ureg = get_registry()
    return sorted(list(ureg._units.keys()))
