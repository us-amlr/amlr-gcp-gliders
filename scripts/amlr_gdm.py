#!/usr/bin/env python

import os
import sys
import logging
import argparse

import multiprocessing as mp
import pandas as pd



def main(args):
    """
    Process raw AMLR glider data and write data to parquet and nc files.

    This script depends requires the directory structure specified in the 
    AMLR glider data management readme:
    https://docs.google.com/document/d/1X5DB4rQRBhBqnFdAAY_5Eyh_yPjG3UZ43Ga7ZGWcSsg

    Returns a gdm object. Note the gdm object in the tmp file has not 
    removed 1970-01-01 timestamps or made column names lowercase. 
    """

    #--------------------------------------------
    # Set up logger
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(module)s:%(levelname)s:%(message)s [line %(lineno)d]'
    logging.basicConfig(format=log_format, level=log_level)
    
    deployment = args.deployment
    project = args.project
    mode = args.mode
    deployments_path = args.deployments_path

    gdm_path = args.gdm_path
    num_cores = args.num_cores

    load_from_tmp = args.load_from_tmp
    remove_19700101 = args.remove_19700101
    write_trajectory = args.write_trajectory
    write_ngdac = args.write_ngdac


    # Check mode and deployment and set related variables
    if not (mode in ['delayed', 'rt']):
        logging.error("mode must be either 'delayed' or 'rt'")
        return
    else:
        if mode == 'delayed':
            binary_type = 'debd'
        else: 
            binary_type = 'stbd'


    deployment_split = deployment.split('-')
    if len(deployment_split[1]) != 8:
        logging.error("The deployment string format must be 'glider-YYYYmmdd', eg amlr03-20220101")
        return

    else:
        logging.info(f'Processing glider data for deployment {deployment}, mode {mode}')
        glider = deployment_split[0]
        year = deployment_split[1][0:4]
        # glider_data_in = os.path.join(deployments_path, project, year, deployment, 
        #     'glider', 'data', 'in')
        # binary_path = os.path.join(glider_data_in, 'binary', binary_type)
        # ascii_path = os.path.join(glider_data_in, 'ascii', binary_type)
        # cache_path = os.path.join(deployments_path, 'cache')

        # logging.debug(f'Binary path: {binary_path}')
        # logging.debug(f'Ascii path: {ascii_path}')
        # logging.debug(f'Cache path: {cache_path}')


    # Append gdm path, and import functions
    if not os.path.isdir(gdm_path):
        logging.error(f'gdm_path ({gdm_path}) does not exist')
        return
    else:
        sys.path.append(gdm_path)
        from gdm import GliderDataModel
        from gdm.gliders.slocum import load_slocum_dba #, get_dbas


    #--------------------------------------------
    # Checks
    prj_list = ['FREEBYRD', 'REFOCUS', 'SANDIEGO']
    if not (project in prj_list):
        logging.error(f"project must be one of {', '.join(prj_list)}")
        return 
    
    if not (1 <= num_cores and num_cores <= mp.cpu_count()):
        logging.error(f'num_cores must be between 1 and {mp.cpu_count()}')
        return 
    
    if not os.path.isdir(deployments_path):
        logging.error(f'deployments_path ({deployments_path}) does not exist')
        return
    else:
        dir_expected = prj_list + ['cache']
        if not all(x in os.listdir(deployments_path) for x in dir_expected):
            logging.error(f"The expected folders ({', '.join(dir_expected)}) " + 
                f'were not found in the provided directory ({deployments_path}). ' + 
                'Did you provide the right path via deployments_path?')
            return 


    #--------------------------------------------
    ### Set path/file variables, and create file paths if necessary
    deployment_mode = deployment + '-' + mode
    glider_path = os.path.join(deployments_path, project, year, deployment, 'glider')
    logging.info(f'Gldier path: {glider_path}')

    ascii_path  = os.path.join(glider_path, 'data', 'in', 'ascii', binary_folder)
    config_path = os.path.join(glider_path, 'config', 'gdm')
    nc_ngdac_path = os.path.join(glider_path, 'data', 'out', 'nc', 'ngdac', mode)
    nc_trajectory_path = os.path.join(glider_path, 'data', 'out', 'nc', 'trajectory', mode)

    tmp_path = os.path.join(glider_path, 'data', 'tmp')
    pq_data_file = os.path.join(tmp_path, deployment_mode + '-data.parquet')
    pq_profiles_file = os.path.join(tmp_path, deployment_mode + '-profiles.parquet')
    
    # This is for GCP because buckets don't do implicit directories well on upload
    if not os.path.exists(tmp_path):
        logging.info(f'Creating directory at: {tmp_path}')
        os.makedirs(tmp_path)
        
    if write_trajectory and (not os.path.exists(nc_trajectory_path)):
        logging.info(f'Creating directory at: {nc_trajectory_path}')
        os.makedirs(nc_trajectory_path)
        
    if write_ngdac and (not os.path.exists(nc_ngdac_path)):
        logging.info(f'Creating directory at: {nc_ngdac_path}')
        os.makedirs(nc_ngdac_path)


    #--------------------------------------------
    # # Read dba files - not necessary
    # logging.info('Getting dba files from: {:}'.format(ascii_path))
    # dba_files = get_dbas(ascii_path)
    # # logging.info('dba file info: {:}'.format(dba_files.info()))

    # Create and process gdm object
    if not os.path.exists(config_path):
        logging.error(f'The config path does not exist {config_path}')
        return 
                        
    gdm = GliderDataModel(config_path)
    if load_from_tmp:        
        logging.info(f'Loading gdm data from parquet files in: {tmp_path}')
        gdm.data = pd.read_parquet(pq_data_file)
        gdm.profiles = pd.read_parquet(pq_profiles_file)
        logging.info('gdm from parquet files:\n {gdm}')

    else:    
        logging.info(f'Creating GliderDataModel object from configs: {config_path}')
        gdm = GliderDataModel(config_path)
    
        # Add data from dba files to gdm
        dba_files_list = list(map(lambda x: os.path.join(ascii_path, x), os.listdir(ascii_path)))
        dba_files = pd.DataFrame(dba_files_list, columns = ['dba_file'])
        
        logging.info(f'Reading ascii data into gdm object using {num_cores} core(s)')
        if num_cores > 1:
            # If num_cores is greater than 1, run load_slocum_dba in parallel
            pool = mp.Pool(num_cores)
            load_slocum_dba_list = pool.map(load_slocum_dba, dba_files_list)
            pool.close()   
            
            load_slocum_dba_list_unzipped = list(zip(*load_slocum_dba_list))
            dba = pd.concat(load_slocum_dba_list_unzipped[0]).sort_index()
            pro_meta = pd.concat(load_slocum_dba_list_unzipped[1]).sort_index()            
            
            gdm.data = dba 
            gdm.profiles = pro_meta

        else :        
            # If num_cores == 1, run load_slocum_dba in normal for loop
            for index, row in dba_files.iterrows():
                # dba_file = os.path.join(row['path'], row['file'])
                dba, pro_meta = load_slocum_dba(row['dba_file'])
                
                gdm.data = pd.concat([gdm.data, dba])
                gdm.profiles = pd.concat([gdm.profiles, pro_meta])
            
        logging.info(f'gdm with data and profiles from dbas:\n {gdm}')
    
        logging.info('Writing gdm to parquet files')
        gdm.data.to_parquet(pq_data_file, version="2.6", index = True)
        gdm.profiles.to_parquet(pq_profiles_file, version="2.6", index = True)

    # Remove garbage data, if specified
    if remove_19700101:
        row_count_orig = len(gdm.data.index)
        gdm.data = gdm.data[gdm.data.index != '1970-01-01']
        num_records_diff = len(gdm.data.index) - row_count_orig
        logging.info(f'Removed {num_records_diff} invalid timestamps of 1970-01-01')

        
    # Make columns lowercase to match gdm behavior
    logging.info('Making sensor (data column) names lowercase to match gdm behavior')
    gdm.data.columns = gdm.data.columns.str.lower()


    #--------------------------------------------
    # Convert to time series, and write to nc file
    if write_trajectory:
        logging.info("Creating timeseries")
        ds = gdm.to_timeseries_dataset()
        
        logging.info("Writing timeseries to nc file")
        ds.to_netcdf(os.path.join(nc_trajectory_path, deployment_mode + '-trajectory.nc'))

    # Write individual (profile) nc files
    # TODO: make parallel, when applicable
    if write_ngdac:
        logging.warning("CANNOT CURRENTLY WRITE TO NGDAC NC FILES")
        # logging.info("Writing ngdac to nc files")
        # glider = dba_files.iloc[0].file.split('_')[0]
        # for profile_time, pro_ds in gdm.iter_profiles():
        #     nc_name = '{:}-{:}-{:}.nc'.format(glider, profile_time.strftime('%Y%m%dT%H%M'), mode)
        #     nc_path = os.path.join(nc_ngdac_path, nc_name)
        #     logging.info('Writing {:}'.format(nc_path))
        #     pro_ds.to_netcdf(nc_path)
        
        
    logging.info('amlr_gdm processing complete for {:}'.format(deployment_mode))
    return gdm



if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=main.__doc__, 
        formatter_class=argparse.ArgumentDefaultsHelpFormatter, 
        allow_abbrev=False)

    arg_parser.add_argument('deployment', 
        type=str,
        help='Deployment name, eg amlr03-20220425')

    arg_parser.add_argument('project', 
        type=str,
        help='Glider project name', 
        choices=['FREEBYRD', 'REFOCUS', 'SANDIEGO'])

    arg_parser.add_argument('mode', 
        type=str,
        help="Specify which binary files will be converted to dbas. " + 
            "'delayed' means [de]bd files will be converted, " + 
            "and 'rt' means [st]bd files will be converted", 
        choices=['delayed', 'rt'])

    arg_parser.add_argument('deployments_path', 
        type=str,
        help='Path to glider deployments directory. ' + 
            'In GCP, this will be the mounted bucket path')

    
    arg_parser.add_argument('--gdm_path', 
        type=str,
        help='Path to gdm module', 
        default='/opt/gdm')

    arg_parser.add_argument('--numcores',
        type=int,
        help='Number of cores to use when processing. ' + 
            'If greater than 1, parallel processing via mp.Pool.map will ' + 
            'be used for load_slocum_dbas and ' + 
            '(todo) writing individual (profile) nc files. ' +
            'This argument must be between 1 and mp.cpu_count()',
        default=1)

    arg_parser.add_argument('--load_from_tmp',
        help='boolean; indicates gdm object should be loaded from ' + 
            'parquet files in glider/data/tmp directory',
        action='store_false')

    arg_parser.add_argument('--remove_19700101',
        help='boolean; indicates if data with the timestamp 1970-01-01 '  + 
            'should be removed (before writing to pkl file). ' + 
            'Will be ignored if load_from_tmp is True. ' + 
            "Removing these timestamps is for situations when there is a " + 
            "'Not enough timestamps for yo interpolation' warning",
        action='store_true')

    arg_parser.add_argument('--write_trajectory',
        help='boolean; indicates if trajectory nc file should be written',
        action='store_false')

    arg_parser.add_argument('--write_ngdac',
        help='boolean; indicates if ngdac nc files should be written',
        action='store_false')

    arg_parser.add_argument('-l', '--loglevel',
        type=str,
        help='Verbosity level',
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default='info')

    parsed_args = arg_parser.parse_args()

    sys.exit(main(parsed_args))