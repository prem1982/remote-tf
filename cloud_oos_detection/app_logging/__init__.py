from os.path import dirname, abspath
import logging
from logging.config import fileConfig

d = dirname(dirname(abspath(__file__)))
config_file = d+'/app_logging/logging_config.ini'
fileConfig(config_file)
logger = logging.getLogger()


def log_process_start_n_end(instance, container_name, url, process):
    process = 'started' if process == 'S' else 'ended'
    logger.info('{0}    -  process {1} for container_name - {2} url - {3}: \
    '.format(instance.__module__, process, container_name, url))


def log_time_chunk(tf_call_no, delta):
    logger.debug("Time taken to process chunk - {0} took - {1}".
                 format(tf_call_no, delta))


def logInfo(info):
    logger.info("Info : {0} ".format(info))


def logDebug(info):
    logger.debug("Debug : {0} ".format(info))
