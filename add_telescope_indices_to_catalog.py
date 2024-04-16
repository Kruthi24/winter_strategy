from astropy.table import Table
from sky_tiling import galaxy_informed_tiling


telescopes = ["Roman", "WINTER", "DECam", "Rubin", "ZTF"]
catalog_file = "./data/NEDLVS_20210922_v2"
extension = ".fits"
new_cat = Table.read(catalog_file+extension)

for telescope in telescopes:
    configfile = "./palomar_telescope_configurations/"+telescope+"_config.ini"
    gal_obj = galaxy_informed_tiling.GalaxyTileGenerator(configfile)
    new_cat = gal_obj.append_tile_indices_to_catalog(new_cat, telescope)

new_cat.write(catalog_file+"_modified"+extension, overwrite=True)

