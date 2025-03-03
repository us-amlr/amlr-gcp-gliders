# -*- coding: utf-8 -*-
"""
Created on Tue Mar 14 12:39:41 2023

By hand processing of data from amlr07-20221204 
Glider fried and lost data, so let's see what's in here.?

@author: sam.woodman
"""

import os
# import sys
import gdm
from gdm import GliderDataModel
from gdm.gliders.slocum import load_slocum_dba

# import multiprocessing as mp
# mp.cpu_count()

# for d in sys.path: print(d)

smw_gliderdir = 'C:/SMW/Gliders_Moorings/Gliders'

# sys.path.append(os.path.join(smw_gliderdir, 'gdm'))
# sys.path.append(os.path.join(smw_gliderdir, 'amlr-gliders', 'amlr-gliders'))
# from gdm import GliderDataModel
# from amlr import amlr_gdm, amlr_acoustics, amlr_imagery, amlr_year_path


deployment = 'amlr07-20221204'
project = 'FREEBYRD'
mode = 'rt'
deployments_path = os.path.join(smw_gliderdir, 'Glider-Data-gcp')

# gdm_path = args.gdm_path
numcores = 7

loadfromtmp = False
write_trajectory = False
write_ngdac = False
write_acoustics = False
write_imagery = False
imagery_path = ''


deployment_split = deployment.split('-')
year = '2022'
deployment_curr_path = os.path.join(deployments_path, project, year, deployment)
glider_path = os.path.join(deployment_curr_path, 'glider')

gdm = GliderDataModel(os.path.join(glider_path, 'config', 'gdm'))
# gdm = amlr_gdm(deployment, project, mode, glider_path, numcores, loadfromtmp)
dba_path = os.path.join(glider_path, 'data', 'in', 'ascii', 'rt')
os.listdir(dba_path)
dba, pro_meta = load_slocum_dba(os.path.join(dba_path, 'amlr07_2022_298_2_0_sbd.dat'))

gdm.data = dba
gdm.profiles = pro_meta
