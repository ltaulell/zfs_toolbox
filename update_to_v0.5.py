#!/usr/bin/env python3
# coding: utf-8
#
# $Id: update_to_v0.5.py 1075 2019-07-18 14:45:39Z gruiick $
# SPDX-License-Identifier: BSD-2-Clause
#

"""
    load <file> as ymldict
    if 0.5, quit
    else keep path/filename
    if 0.3 -> 0.5
        modify, then save inplace
    if 0.4 -> 0.5
        modify, then save inplace

"""

import argparse
import sys

from datetime import datetime
from pprint import pprint

import execo

import zfs_common

__version__ = '0.5'
__author__ = 'See AUTHORS'
__copyright__ = 'Copyright 2019, PSMN, ENS de Lyon'
__credits__ = 'See CREDITS'
__license__ = 'BSD-2'
__maintainer__ = 'Loïs Taulelle'
__email__ = 'None'
__status__ = 'Production'

# global configuration file
CONFIGFILE = '/root/conf/zfs_defaults.yml'
# CONFIGFILE = 'zfs_defaults.yml'
fichierconf = ''


def main():
    """ """
    global fichierconf, GLOBAL_CONFIG
    args = get_args()

    # read global config
    GLOBAL_CONFIG = zfs_common.load_yaml_file(CONFIGFILE)
    GLOBAL_CONFIG['date'] = datetime.now().strftime('%Y/%m/%d-%H:%M:%S')

    # load configuration to modify
    fichierconf = str(args.f[0])
    OLDCONFIG = zfs_common.load_yaml_file(fichierconf)

    if GLOBAL_CONFIG['version'] != __version__:
        execo.log.logger.critical('Configuration version mismatch. Should be '
                                  'version ' + __version__)
        print('Due to refactor, some options have changed and some have been '
              'merged. Hence this script :o)')
        sys.exit(1)

    if args.debug:
        execo.log.logger.setLevel('DEBUG')
        execo.log.logger.debug(args)
        # execo.log.logger.debug(GLOBAL_CONFIG)
        execo.log.logger.debug(OLDCONFIG)
    else:
        execo.log.logger.setLevel('INFO')

    if OLDCONFIG['general']['version'] >= '0.5':
        execo.log.logger.critical('Configuration version mismatch. version must '
                                  'be < 0.5')
        sys.exit(0)
    else:
        todo = OLDCONFIG['action']
        prepare_new_yaml(OLDCONFIG, action=todo, debug=args.debug)


def prepare_new_yaml(old_config, action=None, debug=False):
    """ """
    global fichierconf, GLOBAL_CONFIG
    # prepare configuration
    CONFIG2YAML = {'general': {}, }
    CONFIG2YAML['general']['version'] = __version__
    CONFIG2YAML['general']['log'] = old_config['general']['log']
    CONFIG2YAML['general']['debug'] = old_config['general']['debug']
    # logfile is a bit tricky (zfs-* => zfs_actions)
    oldname = ''.join(['zfs-', action])
    logfile = old_config['general']['logfile'].replace(oldname, 'zfs_actions')
    CONFIG2YAML['general']['logfile'] = logfile
    CONFIG2YAML['retention'] = old_config['retention']

    if action == 'snapshot':
        CONFIG2YAML['action'] = action
        CONFIG2YAML['volume'] = old_config['snapshot']['name']

    elif action == 'replica':
        CONFIG2YAML['action'] = action
        CONFIG2YAML['volume'] = old_config['replica']['sourcename']

        CONFIG2YAML.update({'replica': {'targetpool': '', 'server': ''}, })
        CONFIG2YAML['replica']['type'] = old_config['replica']['type']
        CONFIG2YAML['replica']['archive'] = old_config['replica']['archive']
        CONFIG2YAML['replica']['targetpool'] = old_config['replica']['targetpool']
        CONFIG2YAML['replica']['server'] = old_config['replica']['server']

    # everything is ready, replace?
    pprint(CONFIG2YAML)
    question = ' '.join(['Save this configuration:', fichierconf])

    verifconf = zfs_common.query_yesno(question)
    if verifconf == 1 and not debug:
        zfs_common.save_yaml_file(fichierconf, CONFIG2YAML)
        execo.log.logger.info(str(fichierconf) + ' saved \n')
    elif debug:
        execo.log.logger.info('not writing, dry-run.')
    else:
        execo.log.logger.info('nothing to do.')
        sys.exit(0)

    # modify crontab?
    cronfile = '-'.join([action, str(CONFIG2YAML['volume']).replace('/', '-')])
    cronplete = ''.join([GLOBAL_CONFIG['path']['cron'], cronfile])
    question = ' '.join(['Modify crontab:', cronplete])

    verifcron = zfs_common.query_yesno(question)
    if verifcron == 1 and not debug:
        cmd = ' '.join(['sed -i', '"{s/zfs-snapshot/zfs_actions/ ; s/zfs-replica/zfs_actions/}"', cronplete])
        zfs_common.execute_process(cmd)
    elif debug:
        execo.log.logger.info('not writing, dry-run.')
    else:
        execo.log.logger.info('nothing to do.')
        sys.exit(0)


def get_args():
    """
        read parser and return args (as args namespace)
    """
    parser = argparse.ArgumentParser(description='Modify/Update existing configuration file to v0.5')
    parser.add_argument('-f', nargs=1, type=str, help='File to modify', required=True)
    parser.add_argument('-d', '--debug', action='store_true', help='toggle debug and dry-run (default: no)')
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    """ """
    zfs_common.verif_root()

    main()
