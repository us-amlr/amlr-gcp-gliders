import os
import pathlib


def find_extensions(dir_path): #,  excluded = ['', '.txt', '.lnk']):
    """
    Get all the file extensions in the given directory
    From https://stackoverflow.com/questions/45256250
    """
    extensions = set()
    for _, _, files in os.walk(dir_path):   
        for f in files:
            extensions.add(pathlib.Path(f).suffix)
            # ext = Path(f).suffix.lower()
            # if not ext in excluded:
            #     extensions.add(ext)
    return extensions

def amlr_interpolate(df):
    """
    Wrapper around pandas.interpolate, to standardize passed arguments
    Args:
        df (DataFrame): DataFrame to inteprolate
    Returns:
        Interpolated DataFrame
    """
    return df.interpolate(
        method='time', limit_direction='forward', limit_area='inside'
    )

def amlr_year_path(project, deployment_split):
    """
    Generate and return the year string to use in file paths

    For the FREEBYRD project, this will be the Antarctic season, eg '2018-19'
    For all other projects, this will be a single year, eg '2018'
    """

    year = deployment_split[1][0:4]

    if project == 'FREEBYRD':
        month = deployment_split[1][4:6]
        if int(month) <= 7: 
            year = f'{int(year)-1}-{year[2:4]}'
        else:
            year = f'{year}-{str(int(year)+1)[2:4]}'

    return year

# import logging
# def amlr_logger(logfile, loglevel, logname):
#     # logfile = args.logfile
#     loglevel = getattr(logging, loglevel.upper())
#     logformat = '%(module)s:%(levelname)s:%(message)s [line %(lineno)d]'    
#     # logging.basicConfig(filename=args.logname,
#     #                     filemode='a',
#     #                     datefmt='%H:%M:%S',
#     #                     format=log_format, 
#     #                     level=getattr(logging, args.loglevel.upper()))
    
#     logger = logging.getLogger(logname)
#     logger.setLevel(loglevel)
#     formatter = logging.Formatter(logformat)

#     # create console handler
#     ch = logging.StreamHandler()
#     ch.setLevel(loglevel)
#     ch.setFormatter(formatter)
#     logger.addHandler(ch)

#     # create file handler
#     if logfile != '':
#         fh = logging.FileHandler(logfile)
#         fh.setLevel(loglevel)
#         fh.setFormatter(formatter)
#         logger.addHandler(fh)
        
#     return logger
