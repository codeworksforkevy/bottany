
def load_constants(ureg):
    # NIST CODATA constants
    ureg.define("speed_of_light = 299792458 * meter/second = c")
    ureg.define("planck_constant = 6.62607015e-34 * joule*second = h")
    ureg.define("gravitational_constant = 6.67430e-11 * meter^3/kilogram/second^2 = G")
    ureg.define("avogadro_constant = 6.02214076e23 / mole = N_A")
    
    # IAU astronomy units
    ureg.define("solar_mass = 1.98847e30 * kilogram")
    ureg.define("earth_mass = 5.9722e24 * kilogram")
    ureg.define("jupiter_mass = 1.898e27 * kilogram")
    ureg.define("astronomical_unit = 1.495978707e11 * meter = AU")
    ureg.define("light_year = 9.4607e15 * meter = ly")
    ureg.define("parsec = 3.0857e16 * meter = pc")
