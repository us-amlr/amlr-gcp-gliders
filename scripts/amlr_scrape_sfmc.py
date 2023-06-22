#!/usr/bin/env python

import os
import sys
import stat
import argparse
from subprocess import run

from amlrgliders.utils import amlr_year_path, find_extensions, amlr_logger
from amlrgliders.scrape_sfmc import access_secret_version, rt_files_mgmt


def main(args):
    """
    rsync files from sfmc, and send them to correct bucket directories;
    Returns 0
    """

    #--------------------------------------------
    # Set up logger and args variables
    logger = amlr_logger(args.logfile, args.loglevel, 'amlr_scrape_sfmc')

    deployment = args.deployment
    project = args.project

    sfmc_path = args.sfmc_path
    sfmc_pwd_file_name = args.sfmc_pwd_file_name
    gcpproject_id = args.gcpproject_id
    bucket = args.bucket
    secret_id = args.secret_id

    logger.info(f'Pulling files from SFMC for deployment {deployment}')


    #--------------------------------------------
    # Checks
    deployment_split = deployment.split('-')
    if len(deployment_split[1]) != 8:
        logger.error('The deployment must be the glider name followed by the deployment date')
        return
    else:
        glider = deployment_split[0]
        year = amlr_year_path(project, deployment_split)

    if not os.path.isdir(sfmc_path):
        logger.error(f'sfmc_path ({sfmc_path}) does not exist')
        return


    #--------------------------------------------
    # Create sfmc directory structure, if needed
    logger.debug('Create local sfmc directory structure')
    sfmc_local_path = os.path.join(sfmc_path, f'sfmc-{deployment}')
    name_cac  = 'cac'
    name_stbd = 'stbd'
    name_ad2  = 'ad2'
    # name_cam  = os.path.join(sfmc_local_path, 'cam')

    if not os.path.isdir(sfmc_local_path):
        logger.info('Making sfmc deployment directory and subdirectories ' + 
            f'at {sfmc_local_path}')
        os.mkdir(sfmc_local_path)
        os.mkdir(os.path.join(sfmc_local_path, name_cac))
        os.mkdir(os.path.join(sfmc_local_path, name_stbd))
        os.mkdir(os.path.join(sfmc_local_path, name_ad2))
        # os.mkdir(os.path.join(sfmc_local_path, name_cam))

    logger.debug('SFMC ssh password')
    sfmc_pwd_file = os.path.join(sfmc_local_path, sfmc_pwd_file_name)
    if not os.path.isfile(sfmc_pwd_file):
        logger.info('Writing SFMC ssh pwd to file')
        file = open(sfmc_pwd_file, 'w+')
        file.write(access_secret_version(gcpproject_id, secret_id))
        file.close()
        os.chmod(sfmc_pwd_file, stat.S_IREAD)


    #--------------------------------------------
    # rsync with SFMC
    logger.info(f'Starting rsync with SFMC dockerver for {glider}')
    sfmc_noaa = '/var/opt/sfmc-dockserver/stations/noaa/gliders'
    sfmc_server_path = os.path.join(sfmc_noaa, glider, 'from-glider', "*")
    sfmc_server = f'swoodman@sfmc.webbresearch.com:{sfmc_server_path}'
    # retcode = run(['sshpass', '-p', access_secret_version(gcpproject_id, secret_id), 
    #            'rsync', sfmc_server, sfmc_local_path], 
    # capture_output=True)
    retcode = run(['sshpass', '-f', sfmc_pwd_file, 'rsync', sfmc_server, sfmc_local_path], 
        capture_output=True)
    logger.debug(retcode.args)

    if retcode.returncode != 0:
        logger.error('Error rsyncing with SFMC dockserver')
        logger.error(f'Args: {retcode.args}')
        logger.error(f'stderr: {retcode.stderr}')
        return
    else:
        logger.info(f'Successfully completed rsync with SFMC dockerver for {glider}')
        logger.debug(f'Args: {retcode.args}')
        logger.debug(f'stderr: {retcode.stdout}')


    # Check for unexpected file extensions
    sfmc_file_ext = find_extensions(sfmc_local_path)
    file_ext_expected = {".cac", ".CAC", ".sbd", ".tbd", ".ad2"} #, ".cam"
    file_ext_weird = sfmc_file_ext.difference(file_ext_expected)
    if len(file_ext_weird) > 0:
        x = os.listdir(sfmc_local_path)
        logger.warning(f'File with unexpected extensions ({file_ext_weird}) ' + 
            'were downloaded from the SFMC, ' + 
            'but will not be copied to the GCP bucket')
        # logger.warning(f'File list: TODO')


    #--------------------------------------------
    # Copy files to subfolders, and rsync with bucket
    # https://docs.python.org/3/library/subprocess.html#replacing-bin-sh-shell-command-substitution

    logger.info('Starting file management')
    bucket_deployment = f'gs://{bucket}/{project}/{year}/{deployment}'
    bucket_stbd = os.path.join(bucket_deployment, 'glider', 'data', 'in', 'binary', 'rt')
    bucket_ad2 = os.path.join(bucket_deployment, 'sensors', 'nortek', 'data', 'in', 'rt')
    # bucket_cam = os.path.join(bucket_deployment, 'sensors', 'glidercam', 'data', 'in', 'rt')
    logger.debug(f"GCP bucket deployment folder: {bucket_deployment}")
    logger.debug(f"GCP bucket stbd folder: {bucket_stbd}")
    logger.debug(f"GCP bucket ad2 folder: {bucket_ad2}")
    # logger.debug(f"GCP bucket cam folder: {bucket_cam}")


    # cache files
    rt_files_mgmt(sfmc_file_ext, '.[Cc][Aa][Cc]', name_cac, sfmc_local_path, 
        f'gs://{bucket}/cache')

    # sbd/tbd files
    # TODO: add in support for compressed files
    rt_files_mgmt(sfmc_file_ext, '.[st]bd', name_stbd, sfmc_local_path, bucket_stbd)

    # ad2 files
    rt_files_mgmt(sfmc_file_ext, '.ad2', name_ad2, sfmc_local_path, bucket_ad2)

    # # cam files TODO
    # rt_files_mgmt(sfmc_file_ext, '.cam', name_cam, sfmc_local_path, bucket_cam)


    #--------------------------------------------
    return 0



if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=main.__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    arg_parser.add_argument('deployment', 
        type=str,
        help='Deployment name, eg amlr03-20220425')

    arg_parser.add_argument('project', 
        type=str,
        help='Glider project name', 
        choices=['FREEBYRD', 'REFOCUS', 'SANDIEGO'])

    arg_parser.add_argument('--sfmcpath', 
        type=str,
        dest='sfmc_path', 
        help='The SFMC directory on the local machine ' + 
            'where the files from the SFMC will be copied', 
        default='/var/sfmc')

    arg_parser.add_argument('--sfmcpwd', 
        type=str,
        dest='sfmc_pwd_file_name', 
        help='The file that contains the SFMC password for the rsync', 
        default='.sfmcpwd.txt')

    arg_parser.add_argument('--gcpproject', 
        type=str,
        dest='gcpproject_id', 
        help='GCP project ID', 
        default='ggn-nmfs-usamlr-dev-7b99')

    arg_parser.add_argument('--gcpbucket', 
        type=str,
        dest='bucket', 
        help='GCP glider deployments bucket name', 
        default='amlr-gliders-deployments-dev')

    arg_parser.add_argument('--gcpsecret', 
        type=str,
        dest='secret_id', 
        help='GCP secret ID that contains the SFMC password for the rsync', 
        default='sfmc-swoodman')

    arg_parser.add_argument('-l', '--loglevel',
        type=str,
        help='Verbosity level',
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default='info')
    
    arg_parser.add_argument('--logfile',
        type=str,
        help='File to which to write logs',
        default='')

    parsed_args = arg_parser.parse_args()

    sys.exit(main(parsed_args))
