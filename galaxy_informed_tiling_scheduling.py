import logging
import logging.config
import multiprocessing
from sky_tiling import ranked_tiling, scheduler, galaxy_informed_tiling
from astropy.coordinates import EarthLocation
import os, sys
import astropy.units as u
import matplotlib.pyplot as plt
import pandas as pd
from astropy.table import Table
from astropy.time import Time
import numpy as np
logging.config.dictConfig({'version': 1,'disable_existing_loggers': True,})
logging.basicConfig(level=logging.INFO, format='%(message)s')

duration = 100*3600
integration_times = [50, 303, 140, 32, 50] ## taken from gwemopt
lim_mag = [26, 21, 24, 24.4, 20.4] ## taken from gwemopt
image_per_pointing = 1
CI = 0.9

trial = "bayestar_new_time"

###################################################################################################
path = "data/flat_fits/"+trial+"/"

latency = 900
resolution = 256
fov = [0.28, 1, 3, 9.6, 47]
units = [1, 1, 1, 1, 1]
inj_list = ["bns_50Mpc", "bns_100Mpc", "bns_150Mpc", "bns_200Mpc"]
site_names = ["Roman", "WINTER", "DECam", "Rubin", "ZTF"]
config_dir = "palomar_telescope_configurations/"
detectability_file = "results/"+trial+"_detectability_gal_informed.csv"
outdir = "results/"+trial+"_gal_informed/"
cat = Table.read("data/NEDLVS_20210922_v2_modified.fits")

if not os.path.exists(outdir):
       os.makedirs(outdir)


def source_observed_time(args):
    source_index, schedule = args
    if schedule is None:
        logging.info("Schedule is none")
    else:
        t_obs_source = schedule.loc[schedule['Tile_Index'] == int(source_index), "Observation_Time"]
        if t_obs_source.empty:
            logging.info("Source not observed!")
            return None
        else:
            return t_obs_source.item()
        
#################################################################################

df = pd.DataFrame({"site_names":site_names})
df.to_csv(detectability_file, index=False)

ra = -87.85234195489255
dec = 35.308376046435775
inj_trigger_gps = 1383977402

def process_inj(j):
    inj_name = inj_list[j]
    fname = [filename for filename in os.listdir(path) if filename.startswith(inj_name+"_data_flattened")][0]
    print(fname)
    nsites = len(site_names)
    source_tile_ranks = np.full(nsites, np.nan)
    delta_t_array = np.full(nsites, np.nan)

     # Configure a separate log file for each GRB inside the outdir
    log_filename = os.path.join(outdir, f'{inj_name}_logfile.log')
    file_handler = logging.FileHandler(log_filename, mode='w')
    file_handler.setFormatter(logging.Formatter('%(message)s'))
    logging.getLogger().addHandler(file_handler)
    logging.info(f'{inj_name}: Starting Analysis\n')

    for i in range(nsites):
        logging.info(f'{inj_name}: Generating tiling for {site_names[i]}')
        tag = inj_name+"_"+site_names[i]
        tileObj = galaxy_informed_tiling.GalaxyTileGenerator(configfile=config_dir+site_names[i]+"_config.ini", 
                                                             outdir=outdir, skymapfile=path+fname,)
        gal_informed_tiles = tileObj.get_galaxy_informed_tiles(cat, site_names[i], sort_metric = 'Mstar', CI=CI,
                                  sort_by_metric_times_tile_prob = False, save_csv=True)
        gal_informed_saved_csv = outdir+tag+"_galaxy_informed_tiles.csv"
        
        prob_ranked = gal_informed_tiles.sort_values(by='tile_prob', ascending=False)
        prob_ranked_saved_csv = outdir+tag+"_prob_ranked.csv"
        prob_ranked.to_csv(prob_ranked_saved_csv, index=False)
        
        mstar_prob_ranked = gal_informed_tiles.sort_values(by='tile_Mstar*tile_prob', ascending=False)
        mstar_prob_ranked_saved_csv = outdir+tag+"_mass_prob_gal_informed.csv"
        mstar_prob_ranked.to_csv(mstar_prob_ranked_saved_csv, index=False)

        tileObj.plotTiles(event=[ra, dec], save_plot=True, tag=tag, tileEdges=True, FOV=fov[i])
        source_index = tileObj.sourceTile(ra, dec)
        source_withinin_CI_area = gal_informed_tiles[gal_informed_tiles["tile_index"]== source_index]
        if not source_withinin_CI_area.empty:
            rank = source_withinin_CI_area.index.values[0] + 1  ##rank starts from 1. Only used for printing and detectability csv file 
            source_tile_ranks[i] = int(rank)
            logging.info(f"{inj_name}: Source tile rank: {source_tile_ranks[i]}")
        else:
            logging.info(f"{inj_name}: Source not within CI area!")
        logging.info(f"{inj_name}: Source tile index: {source_index}")       

        logging.info(f'{inj_name}: Generating observation schedule for {site_names[i]}')
        gal_informd_observing = scheduler.Scheduler(ranked_tiles_csv = gal_informed_saved_csv, configfile=config_dir+site_names[i]+"_config.ini",
                                        outdir=outdir, logfile=log_filename)
        gal_informed_schedule = gal_informd_observing.observationSchedule(duration=duration, eventTime=inj_trigger_gps,
                                                integrationTime=image_per_pointing * integration_times[i], CI=CI,
                                                save_schedule=True, tag=tag+'_gal_informed', latency = latency)
        
        gal_informd_observing_2 = scheduler.Scheduler(ranked_tiles_csv = mstar_prob_ranked_saved_csv, configfile=config_dir+site_names[i]+"_config.ini",
                                        outdir=outdir, logfile=log_filename)
        gal_informed_schedule = gal_informd_observing_2.observationSchedule(duration=duration, eventTime=inj_trigger_gps,
                                                integrationTime=image_per_pointing * integration_times[i], CI=CI,
                                                save_schedule=True, tag=tag+'_gal_informed_mstar_prob', latency = latency)
        
        observing = scheduler.Scheduler(ranked_tiles_csv = prob_ranked_saved_csv, configfile=config_dir+site_names[i]+"_config.ini",
                                        outdir=outdir, logfile=log_filename)
        schedule = observing.observationSchedule(duration=duration, eventTime=inj_trigger_gps,
                                                integrationTime=image_per_pointing * integration_times[i], CI=CI,
                                                save_schedule=True, tag=tag+'_prob_ranked', latency = latency)
    
        when_was_source_observed = source_observed_time((source_index, schedule))
        if when_was_source_observed is not None:
            source_observation_time_gps = Time(when_was_source_observed).gps
            delta_t = source_observation_time_gps - inj_trigger_gps
            if units[i] > 1:
                delta_t = latency + (delta_t - latency)/units[i]
            delta_t_array[i] =  (delta_t*u.s).to(u.day).value
            logging.info(f"{inj_name}: Delta_t = {delta_t_array[i]}")
        logging.info('\n')


    df_detectability = pd.read_csv(detectability_file, header=0)
    df_detectability[inj_name+"_dt_days"] = delta_t_array
    df_detectability[inj_name+"_source_tile_rank"] = source_tile_ranks
    df_detectability.to_csv(detectability_file, index=False, na_rep='N/A')
    logging.info(f'{inj_name}: Data saved!')
    logging.getLogger().removeHandler(file_handler)

if __name__ == "__main__":
    #main log
    main_log_filename = os.path.join(outdir, 'main_logfile.log')
    main_file_handler = logging.FileHandler(main_log_filename, mode='w')
    main_file_handler.setFormatter(logging.Formatter('%(message)s'))
    logging.getLogger().addHandler(main_file_handler)
    logging.info(f"Configuration settings\n")
    logging.info(f"path: {path}")
    logging.info(f"outdir: {outdir}")
    logging.info(f"duration: {duration}")
    logging.info(f"CI: {CI}")
    logging.info(f"integration_times: {integration_times}")
    logging.info(f"lim_mag: {lim_mag}")
    logging.info(f"image_per_pointing: {image_per_pointing}")
    logging.info(f"resolution: {resolution}")
    logging.getLogger().removeHandler(main_file_handler)

    multiprocessing.set_start_method("spawn")
    num_processes = multiprocessing.cpu_count()-1 # You can adjust this based on your system's capabilities
    if num_processes < 4:
        print("\033[91m {}\033[00m" .format("WARNING: Individual log files won't be logged properly when using less than 4 cores"))
    with multiprocessing.Pool(num_processes) as pool:
        pool.map(process_inj, range(4)) #all grb