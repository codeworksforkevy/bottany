
def load_ucum_units(ureg):
    # Photometry
    ureg.define("candela = candela")
    ureg.define("lumen = candela * steradian")
    ureg.define("lux = lumen / meter^2")
    ureg.define("nit = candela / meter^2")
    ureg.define("foot_candle = lumen / foot^2")
    
    # Radiation / energy
    ureg.define("erg = 1e-7 * joule")
    ureg.define("electronvolt = 1.602176634e-19 * joule = eV")
    
    # CGS
    ureg.define("gal = centimeter/second^2")
    ureg.define("dyne = gram*centimeter/second^2")
