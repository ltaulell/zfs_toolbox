#!/usr/bin/env python3
# coding: utf-8

# $Id: manage_conf.py 1398 2020-09-15 14:27:54Z gruiick $
# SPDX-License-Identifier: BSD-2-Clause

"""

    * manage (create/erase) config file for zfs volume provided by
    '<volume>', ask if it is correct before writing,
    * manage (create/erase) related crontab file, ask if it is correct
    before writing,
    * ask and restart cron.

TODO:

FIXME:

"""

import os
import sys
import argparse
from pprint import pprint
from datetime import datetime
import logging

import execo

import zfs_common

__version__ = "0.5"
__author__ = "See AUTHORS"
__copyright__ = "Copyright 2018, PSMN, ENS de Lyon"
__credits__ = "See CREDITS"
__license__ = "BSD-2"
__maintainer__ = "Loïs Taulelle"
__email__ = "None"
__status__ = "Production"

# global configuration file
CONFIGFILE = '/root/conf/zfs_defaults.yml'
# CONFIGFILE = 'zfs_defaults.yml'  # tests only


class ParseArgs(object):
    """ overcharge argparse and fill a dict of arguments, with defaults sets """

    def __init__(self):
        """ select according to first positional (act as mutually_exclusive_group) """
        self.arguments = {}
        parser = argparse.ArgumentParser(description='', usage='''
  %(prog)s {command} {type} <volume> [<crontab options> <args>]

Enable or disable a configuration for automated snapshots or replicas.

Where {command} is:
  enable                enable a new configuration and activate it
  disable               or disable (and erase) an existing configuration

Where {type} is:
  --snapshot            manage configuration file for snapshot(s) on <volume>
  --replica             or manage configuration file for replica(s) of <volume>

<volume>                mandatory zfs volume name

<crontab options> are:
  -H, --hour            Hour parameter (mandatory for enable)
  -m, --minute          minute parameter (mandatory for enable)
  -DM, --dayofmonth     Day of Month parameter
  -M, --month           Month parameter
  -DW, --dayofweek      Day of Week parameter

<args> can be:
  -d, --debug           toggle debug ON
  -l, --log             toggle log ON
  -r, --retention RETENTION
                        retention in days [default: 7]
  --mail [MAIL]         let cron send an email for each snapshot/replica
                        (default: no, [default: root])

For a replica, there are more optional <args>:
  -t, --target TARGET   zfs target pool name [default: None, same as source]
  -s, --server SERVER   server hosting replication target [default: localhost]

  --simple              replica type: simple, only target pool and last dataset [default]
  --complete            or complete, target pool plus complete source dataset'

  --latest              replica archive: only latest snapshot [default]
  --oldest              or complete set of snapshots

''')
        parser.add_argument('command', help='enable or disable')
        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            print('Unrecognized command')
            parser.print_help()
            exit(1)
        # store everything in a global dict
        self.arguments.update(vars(args))
        # use dispatch pattern to invoke method with same name
        getattr(self, args.command)()

    def enable(self):
        """ Parse the enable part of arguments """
        # some default <args>
        enable_parser = argparse.ArgumentParser(description='enable a configuration',
                                                usage='%(prog)s enable {type} '
                                                '[options] <volume>', add_help=True)
        enable_parser.add_argument('-r', '--retention', nargs=1, type=int,
                                   help='retention, in day(s) [default: 7]')
        enable_parser.add_argument('--mail', action='store', nargs='?',
                                   type=str, const='root', help='let cron send '
                                   'an email each snapshot (default: no, '
                                   '[default: root])')
        # <crontab> options
        cron = enable_parser.add_argument_group('crontab options')
        cron.add_argument('-H', '--hour', nargs=1, type=int,
                          help='cron hour parameter', required=True)
        cron.add_argument('-m', '--minute', nargs=1, type=int,
                          help='cron minute parameter', required=True)
        cron.add_argument('-DM', '--dayofmonth', nargs=1, type=int,
                          help='cron day of month parameter')
        cron.add_argument('-M', '--month', nargs=1, type=int,
                          help='cron month parameter')
        cron.add_argument('-DW', '--dayofweek', nargs=1, type=int,
                          help='cron day of week parameter')
        # {type}
        group_enable = enable_parser.add_mutually_exclusive_group()
        group_enable.add_argument('--snapshot', action='store_true',
                                  help='Activate a snapshot configuration')
        group_enable.add_argument('--replica', action='store_true',
                                  help='Activate a replica configuration')
        # replica <args> options [-t <target volume>, -s serveur]
        enable_parser.add_argument('-t', '--target', nargs=1, type=str,
                                   help='zfs target pool name [default: None, '
                                   'same as source]')
        enable_parser.add_argument('-s', '--server', nargs=1, type=str,
                                   help='server hosting replication target '
                                   '[default: localhost]', required=False)
        # replica <args> type [--simple|--complete]
        replicag1 = enable_parser.add_mutually_exclusive_group()
        replicag1.add_argument('--simple', action='store_true',
                               help='replica type: simple, only target pool '
                               'and last dataset [default]', default=True)
        replicag1.add_argument('--complete', action='store_true',
                               help='replica type: complete, target pool plus '
                               'complete source dataset')
        # replica <args> archive [--latest|--oldest]
        replicag2 = enable_parser.add_mutually_exclusive_group()
        replicag2.add_argument('--latest', action='store_true',
                               help='replica archive: only latest snapshot '
                               '[default]', default=True)
        replicag2.add_argument('--oldest', action='store_true',
                               help='replica archive: complete set of snapshots')
        # last common <args>
        enable_parser.add_argument('volume', nargs=1, type=str,
                                   help='Mandatory zfs volume name')
        base = enable_parser.add_argument_group('common options')
        base.add_argument('-d', '--debug', action='store_true',
                          help='toggle debug [default: no]')
        base.add_argument('-l', '--log', action='store_true',
                          help='toggle logs [default: no]')
        args = enable_parser.parse_args(sys.argv[2:])
        self.arguments.update(vars(args))

    def disable(self):
        """ Parse the disable part of arguments """
        disable_parser = argparse.ArgumentParser(description='disable a configuration',
                                                 usage='%(prog)s disable {type} [options] <volume>',
                                                 add_help=True)
        group = disable_parser.add_mutually_exclusive_group()
        group.add_argument('--snapshot', action='store_true',
                           help='Deactivate a snapshot configuration')
        group.add_argument('--replica', action='store_true',
                           help='Deactivate a replica configuration')
        # last common <args>
        disable_parser.add_argument('volume', nargs=1, type=str,
                                    help='Mandatory zfs volume name')
        base = disable_parser.add_argument_group('common options')
        base.add_argument('-d', '--debug', action='store_true',
                          help='toggle debug [default: no]')
        base.add_argument('-l', '--log', action='store_true',
                          help='toggle logs [default: no]')
        args = disable_parser.parse_args(sys.argv[2:])
        self.arguments.update(vars(args))


def enable_snapshot():
    """ simple as snapshot """

    CONFIG2YAML['action'] = 'snapshot'

    # check and save configuration file
    check_and_save_yml()

    # then prepare and save crontab
    prepare_and_save_crontab()


def enable_replica():
    """ complicated as replica """

    CONFIG2YAML['action'] = 'replica'
    CONFIG2YAML.update({'replica': {'targetpool': '', 'server': ''}, })

    if script.arguments['server'] is None:
        CONFIG2YAML['replica']['server'] = 'localhost'
    else:
        CONFIG2YAML['replica']['server'] = str(script.arguments['server'][0])

    # target pool name, needed if server is localhost
    if script.arguments['target'] is None:
        if script.arguments['server'] is None:
            execo.log.logger.critical("Cannot replicate on same zfs pool.")
            sys.exit(1)
        else:
            CONFIG2YAML['replica']['targetpool'] = ''
    else:
        CONFIG2YAML['replica']['targetpool'] = str(script.arguments['target'][0])

    if script.arguments['complete']:
        # Include the dataset's properties in the stream. See 'man zfs'.
        CONFIG2YAML['replica']['type'] = 'complete'
    elif script.arguments['simple']:
        CONFIG2YAML['replica']['type'] = 'simple'

    if script.arguments['oldest']:
        # will replicate all available snapshots
        CONFIG2YAML['replica']['archive'] = 'oldest'
    elif script.arguments['latest']:
        # will replicate only the latest snapshot
        CONFIG2YAML['replica']['archive'] = 'latest'

    # check and save configuration file
    check_and_save_yml()

    # then prepare and save crontab
    prepare_and_save_crontab()


def disable_action(action=None):
    """ find and erase a configuration """

    nomfichier = ''.join([action, '-',
                          str(script.arguments['volume'][0]).replace('/', '-')])

    cronfichier = ''.join([GLOBAL_CONFIG['path']['cron'], nomfichier])

    if os.path.isfile(cronfichier):
        question = ' '.join(['Erase', str(cronfichier)])
        supprime = zfs_common.query_yesno(question)
        if supprime == 1:
            zfs_common.erase_file(cronfichier)

            conffichier = ''.join([GLOBAL_CONFIG['path']['conf'],
                                   nomfichier, '.yml'])

            if os.path.isfile(conffichier):
                question2 = ' '.join(['Erase', str(conffichier)])
                supprime2 = zfs_common.query_yesno(question2)

                if supprime2 == 1:
                    zfs_common.erase_file(conffichier)
            else:
                execo.log.logger.warning('file does not exist: ' + conffichier)

            restart_cron()
    else:
        execo.log.logger.warning('file does not exist: ' + cronfichier)


def check_and_save_yml():
    """ check and save configuration file """

    if script.arguments['snapshot']:
        nomfichier = '-'.join(['snapshot',
                               str(script.arguments['volume'][0]).replace('/', '-')])
        GLOBAL_CONFIG['path']['nomfichier'] = nomfichier

    elif script.arguments['replica']:
        nomfichier = '-'.join(['replica',
                               str(script.arguments['volume'][0]).replace('/', '-')])
        GLOBAL_CONFIG['path']['nomfichier'] = nomfichier

    tosave = ''.join([GLOBAL_CONFIG['path']['conf'],
                      GLOBAL_CONFIG['path']['nomfichier'], '.yml'])

    GLOBAL_CONFIG['path']['tosave'] = tosave  # needed later

    pprint(CONFIG2YAML)
    question = ' '.join(['Save this configuration:', tosave])
    verifconf = zfs_common.query_yesno(question)

    if verifconf == 1:
        zfs_common.verify_or_create_dir(tosave)
        zfs_common.save_yaml_file(tosave, CONFIG2YAML)
        execo.log.logger.info(str(tosave) + ' saved \n')
    else:
        execo.log.logger.info('nothing to do.')
        sys.exit(0)


def prepare_and_save_crontab():
    """ act as 'crontab -e' """

    # prepare crontab, all in str()
    minute = str(script.arguments['minute'][0])
    hour = str(script.arguments['hour'][0])
    if script.arguments['dayofmonth']:
        dom = str(script.arguments['dayofmonth'][0])
    else:
        dom = '*'
    if script.arguments['month']:
        month = str(script.arguments['month'][0])
    else:
        month = '*'
    if script.arguments['dayofweek']:
        dow = str(script.arguments['dayofweek'][0])
    else:
        dow = '*'

    # save crontab
    # deb12: introduce venv
    venv = 'cd GLOBAL_CONFIG['path']['tools'] && source bin/activate &&'
    binpy = ''.join(GLOBAL_CONFIG['path']['tools'],GLOBAL_CONFIG['path']['cmd'])
    ymlconf = GLOBAL_CONFIG['path']['tosave']
    global_cmd = ' '.join('(', venv, binpy, '-c', ymlconf, ')')

    if not script.arguments['mail']:
        cronlist = (minute, hour, dom, month, dow, GLOBAL_CONFIG['user'],
                    global_cmd, '>/dev/null')
        mailto = 'MAILTO=root'
    else:
        cronlist = (minute, hour, dom, month, dow, GLOBAL_CONFIG['user'],
                    global_cmd)
        mailto = 'MAILTO=' + str(script.arguments['mail'])

    crontab = (' '.join(cronlist))
    cronfichier = ''.join([GLOBAL_CONFIG['path']['cron'],
                           GLOBAL_CONFIG['path']['nomfichier']])
    print(mailto)
    print(crontab)
    question = ' '.join(['Save this crontab:', cronfichier])
    verifcron = zfs_common.query_yesno(question)
    if verifcron == 1:
        defaultpath = 'PATH=/sbin:/bin:/usr/sbin:/usr/bin'
        fichier = ['# ' + GLOBAL_CONFIG['date'], GLOBAL_CONFIG['defaultshell'],
                   mailto, defaultpath, crontab, '']
        zfs_common.verify_or_create_dir(cronfichier)
        zfs_common.save_crontab(cronfichier, fichier)
        execo.log.logger.info(cronfichier + ' saved \n')

        restart_cron()


def restart_cron():
    """ restart cron """
    question = zfs_common.query_yesno('Restart cron daemon')
    if question == 1:
        cmd = 'systemctl restart cron.service'
        zfs_common.execute_process(cmd)


if __name__ == '__main__':
    """
        verify admin rights
        load default config file
        set log level & log file
        parse config & args
        if enable:
            using args and config dict, prepare yml config dict
            ask user, then save config dict (as yaml file)
            prepare crontab file
            ask user, then save it
            ask user, restart cron daemon
        elif disable:
            using args and config dict, compute file's names and paths
            ask user, then erase crontab file
            ask user, then erase yaml config file
            ask user, restart cron daemon

    """
    # exit if not euid0
    zfs_common.verif_root()

    # read global config from a yml file
    GLOBAL_CONFIG = zfs_common.load_yaml_file(CONFIGFILE)
    GLOBAL_CONFIG['date'] = datetime.now().strftime('%Y/%m/%d-%H:%M:%S')

    # prepare configuration
    CONFIG2YAML = {'general': {}, }

    if GLOBAL_CONFIG['version'] != __version__:
        execo.log.logger.critical('Configuration version mismatch. Should be '
                                  'version ' + __version__)
        # TODO: explain 0.4 vs 0.5 differences in doc
        # Due to refactor, some options have changed and some have been merged.
        sys.exit(1)
    else:
        CONFIG2YAML['general']['version'] = __version__

    # parse CLI arguments
    script = ParseArgs()

    if script.arguments['debug']:
        CONFIG2YAML['general']['debug'] = 'yes'
        execo.log.logger.setLevel('DEBUG')
        execo.log.logger.debug(script.arguments)
        execo.log.logger.debug(GLOBAL_CONFIG)
    else:
        CONFIG2YAML['general']['debug'] = 'no'
        execo.log.logger.setLevel('INFO')

    if script.arguments['log']:
        CONFIG2YAML['general']['log'] = 'yes'
        logfile = ''.join([GLOBAL_CONFIG['path']['log'], 'zfs_actions.log'])
        CONFIG2YAML['general']['logfile'] = logfile
        file_handler = logging.FileHandler(logfile, 'a')
        # apply 'execo' formatter to file_handler
        file_handler.setFormatter(execo.logger.handlers[0].formatter)
        # create logpath before addHandler
        zfs_common.verify_or_create_dir(logfile)
        execo.log.logger.addHandler(file_handler)
    else:
        CONFIG2YAML['general']['log'] = 'no'
        # even if no log, specify the log file, one may change his mind
        logfile = ''.join([GLOBAL_CONFIG['path']['log'], 'zfs_actions.log'])
        CONFIG2YAML['general']['logfile'] = logfile

    CONFIG2YAML['volume'] = str(script.arguments['volume'][0])
    execo.log.logger.debug(CONFIG2YAML)

    if script.arguments['command'] == 'enable':
        execo.log.logger.debug('enable')

        if script.arguments['retention']:
            CONFIG2YAML['retention'] = str(script.arguments['retention'][0])
        else:
            CONFIG2YAML['retention'] = '7'

        if script.arguments['snapshot']:
            execo.log.logger.debug('snapshot')
            enable_snapshot()

        elif script.arguments['replica']:
            execo.log.logger.debug('replica')
            enable_replica()

    elif script.arguments['command'] == 'disable':
        execo.log.logger.debug('disable')

        if script.arguments['snapshot']:
            execo.log.logger.debug('snapshot')
            disable_action(action='snapshot')

        elif script.arguments['replica']:
            execo.log.logger.debug('replica')
            disable_action(action='replica')

    execo.log.logger.debug(GLOBAL_CONFIG)
    execo.log.logger.debug(CONFIG2YAML)
