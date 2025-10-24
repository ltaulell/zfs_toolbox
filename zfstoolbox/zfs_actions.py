#!/usr/bin/env python3
# coding: utf-8

# $Id: zfs_actions.py 1075 2019-07-18 14:45:39Z gruiick $
# SPDX-License-Identifier: BSD-2-Clause

"""
    * read config file (given by -c argument),
    * if snapshot
        * create snapshot,
        * list snapshot(s), if snapshot is oldest than retention, erase it.
    * if replica
        * replicate snapshot(s), full or incremental
        * list replica(s), if replica is oldest than retention, erase it.

    TODO/FIXME:
"""

import sys
import argparse
import datetime
import logging

import execo

import zfs_common

__version__ = "0.6"
__author__ = "See AUTHORS"
__copyright__ = "Copyright 2018, PSMN, ENS de Lyon"
__credits__ = "See CREDITS"
__license__ = "BSD-2"
__maintainer__ = "Loïs Taulelle"
__email__ = "None"
__status__ = "Production"

# global configuration file
CONFIGFILE = '/root/conf/zfs_defaults.yml'
# CONFIGFILE = 'zfs_defaults.yml'


def create_snapshot(zvolname):
    """
        create a snapshot of zvolname
        format is <zfs volume name>@snapshot-date
    """
    zdate = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    snapname = ''.join([zvolname, '@snapshot-', zdate])
    cmd = ' '.join([GLOBAL_CONFIG['path']['zfs'], 'snapshot', snapname])
    zfs_common.execute_process(cmd)
    execo.log.logger.info('snapshot: ' + snapname)


def destroy_replica(serveur, tgtzname, borne):
    """ filter and destroy replica(s) older than retention """

    # Refresh the target snapshot list
    snapdates = get_distant_snapshot(serveur, tgtzname)

    tgtdates = zfs_common.filter_date_snap(snapdates)

    lastdate = max(tgtdates)

    for timestp in tgtdates:
        if lastdate - borne <= timestp:
            execo.log.logger.debug('keep: ' + str(timestp))
        else:
            to_erase = ''.join([tgtzname, '@snapshot-',
                                str(timestp.strftime('%Y%m%d%H%M%S'))])
            execo.log.logger.debug('erase: ' + to_erase)

            cmd = ' '.join([GLOBAL_CONFIG['path']['zfs'], 'destroy',
                            to_erase])
            execo.log.logger.info('erasing: ' + to_erase + ' on host ' + serveur)
            zfs_common.execute_zfs(cmd, host=serveur)


def destroy_snapshot(zvolname, retention):
    """
        delete snapshot(s) older(s) than retention on zvolname
    """

    borne = datetime.timedelta(days=int(retention))
    lst_snap = get_local_snapshot(zvolname)

    execo.log.logger.debug(lst_snap)

    snapdates = zfs_common.filter_date_snap(lst_snap)

    lastdate = max(snapdates)
    execo.log.logger.debug('lastdate: ' + str(lastdate))
    for timestp in snapdates:
        if lastdate - borne <= timestp:
            execo.log.logger.debug('keep: ' + str(timestp))
        else:
            to_erase = zvolname + '@snapshot-' + str(timestp.strftime('%Y%m%d%H%M%S'))
            execo.log.logger.debug('erase: ' + str(timestp))
            execo.log.logger.debug(to_erase)
            cmd = ' '.join([GLOBAL_CONFIG['path']['zfs'], 'destroy', to_erase])
            zfs_common.execute_process(cmd)
            execo.log.logger.info('erased: ' + to_erase)

    lastsnap = zvolname + '@snapshot-' + str(lastdate.strftime('%Y%m%d%H%M%S'))
    execo.log.logger.debug('calculated lastsnap: ' + str(lastsnap))


def full_replication(serveur, localzname, tgtzname, reptype=None, archtype=None):
    """
        if archtype is oldest
            send oldest snapshot
            then switch to incremental
        else (None or latest)
            send latest snapshot
    """
    if archtype == 'oldest':
        localsnap = get_local_snapshot(localzname, status='oldest')
    else:  # archtype is latest or None
        localsnap = get_local_snapshot(localzname, status='latest')

    if reptype == 'complete':
        send_cmd = 'send -peL'
    else:  # reptype is simple or None
        send_cmd = 'send -eL'

    local_cmd = ' '.join([GLOBAL_CONFIG['path']['zfs'], send_cmd, localsnap])
    execo.log.logger.debug(local_cmd)

    tgt_cmd = ' '.join([GLOBAL_CONFIG['path']['zfs'], 'receive -F', tgtzname])
    execo.log.logger.debug(tgt_cmd)

    # simpliest: local_cmd | ssh -o BatchMode=yes root@serveur tgt_cmd
    if serveur == 'localhost':
        complete_cmd = ' | '.join([local_cmd, tgt_cmd])
    else:
        complete_cmd = ''.join([local_cmd, ' | ssh -q -o BatchMode=yes root@',
                                serveur, ' ', tgt_cmd])

    execo.log.logger.debug(complete_cmd)
    execo.log.logger.info('copying: ' + localsnap + ' on host ' + serveur)
    zfs_common.execute_zfs(complete_cmd, shell=True)

    # should be this way with mbuffer
    # with execo.process.SshProcess(tgt_cmd, serveur).start() as receiver:
    #    execo.sleep(2)
    #    sender = execo.process.Process(local_cmd).run()
    #    receiver.wait()
    # print(receiver.stdout)

    if archtype == 'oldest':
        # goto incremental
        execo.log.logger.debug('doing incremental')
        incremental_replication(serveur, localzname, tgtzname)


def get_args():
    """
        read parser and return args (as args namespace)
    """
    parser = argparse.ArgumentParser(description='Create, or replicate, and '
                                                 'destroy automated snapshots')
    parser.add_argument('-c', '--conf', nargs=1, type=str,
                        help='Mandatory YAML config file', required=True)
    parser.add_argument('-d', '--debug', action='store_true',
                        help='toggle debug (default: no)')
    args = parser.parse_args()

    return args


def get_distant_snapshot(serveur, volume_name, first=False):
    """
        list snapshots on target host, if None, return 'full'
    """
    cmd = ' '.join([GLOBAL_CONFIG['path']['zfs'],
                    'list -H -o name -t snapshot -r', volume_name])

    if first:
        # target dataset may not exist
        str_snap = zfs_common.execute_zfs(cmd, host=serveur, nolog=True)
    else:
        str_snap = zfs_common.execute_zfs(cmd, host=serveur)

    execo.log.logger.debug(str_snap)

    if str_snap is None:
        # full, for new replication
        execo.log.logger.info('No replica(s), doing full')
        return 'full'
    else:
        # return snapshots list for incremental replication
        lst_snap = str_snap.splitlines()
        execo.log.logger.debug(lst_snap)

        return lst_snap


def get_local_snapshot(volume_name, status=None):
    """
        if status is oldest, return oldest snapshot
        if status is latest, return latest snapshot
        else return snapshots list from a zfs volume
    """

    cmd = ' '.join([GLOBAL_CONFIG['path']['zfs'],
                    'list -H -o name -t snapshot -r', volume_name])
    str_snap = zfs_common.execute_zfs(cmd)
    list_snap = str_snap.splitlines()

    execo.log.logger.debug(type(list_snap))
    execo.log.logger.debug(list_snap)

    snapdates = zfs_common.filter_date_snap(list_snap)

    if status == 'oldest':
        snapdate = min(snapdates)
        snap = ''.join([volume_name, '@snapshot-',
                        str(snapdate.strftime('%Y%m%d%H%M%S'))])
        return snap

    elif status == 'latest':
        snapdate = max(snapdates)
        snap = ''.join([volume_name, '@snapshot-',
                        str(snapdate.strftime('%Y%m%d%H%M%S'))])
        return snap

    else:
        # status is anything else, including None
        return list_snap


def incremental_replication(serveur, localzname, tgtzname):
    """
        do incremental replication using latest tgt and latest src
        find latest snap on target
            use same date on source
        find latest snap on source
        if latest target is less than latest src : replicate snapshot(s)
    """
    # This need to refresh the target snapshot list, as this can be called
    # by full_replication, on oldest mode, a long time after full has
    # started (hours, days).
    # Make sure retention is enought to perform a first replication, in time,
    # with oldest source snapshot before it get destroy on local dataset.

    snaplist = get_distant_snapshot(serveur, tgtzname)
    tgtdates = zfs_common.filter_date_snap(snaplist)
    latest_tgt_date = max(tgtdates)  # datetime
    latest_tmp_snap = ''.join([localzname, '@snapshot-',
                               str(latest_tgt_date.strftime('%Y%m%d%H%M%S'))])
    latestsnap = []
    latestsnap.append(get_local_snapshot(localzname, status='latest'))

    srcdate = zfs_common.filter_date_snap(latestsnap)
    latest_src_date = max(srcdate)  # datetime

    execo.log.logger.debug('latest tgt :' + str(latest_tmp_snap))
    execo.log.logger.debug('latest src :' + str(latestsnap[0]))

    # send diff 'latest on target' vs 'latest on source'
    if latest_tgt_date < latest_src_date:

        lcl_cmd = ' '.join([GLOBAL_CONFIG['path']['zfs'], 'send -eL -I',
                            latest_tmp_snap, latestsnap[0]])

        tgt_cmd = ' '.join([GLOBAL_CONFIG['path']['zfs'], 'receive',
                            tgtzname])

        if serveur == 'localhost':
            complete_cmd = ' | '.join([lcl_cmd, tgt_cmd])
        else:
            complete_cmd = ''.join([lcl_cmd, ' | ssh -q -o BatchMode=yes root@',
                                    serveur, ' ', tgt_cmd])

        execo.log.logger.debug(complete_cmd)
        zfs_common.execute_zfs(complete_cmd, shell=True)

        execo.log.logger.info('copying (up to): ' + latestsnap[0] + ' on host ' + serveur)
    else:
        execo.log.logger.info('nothing to do.')


if __name__ == '__main__':
    """
        verify admin rights
        load config file
        set log level & log file
        check if zfs binary exist
        if action=snapshot
            create snapshot
            delete snapshot(s), if needed
        else if action=replica
            full replication or
            incremental replication
            delete replica(s), if needed
    """
    # exit if not euid0
    zfs_common.verif_root()

    args = get_args()

    # read global config from a yml file
    GLOBAL_CONFIG = zfs_common.load_yaml_file(CONFIGFILE)

    # load action configuration
    fichierconf = str(args.conf[0])
    ACTION_CONFIG = zfs_common.load_yaml_file(fichierconf)

    if ACTION_CONFIG['general']['debug'] == 'yes' or args.debug:
        execo.log.logger.setLevel('DEBUG')
        execo.log.logger.debug(GLOBAL_CONFIG)
        execo.log.logger.debug(ACTION_CONFIG)
    else:
        execo.log.logger.setLevel('INFO')

    if ACTION_CONFIG['general']['log'] == 'yes':
        logfile = ACTION_CONFIG['general']['logfile']
        file_handler = logging.FileHandler(logfile, 'a')
        # apply 'execo' formatter to file_handler
        file_handler.setFormatter(execo.logger.handlers[0].formatter)
        # create logpath before addHandler
        zfs_common.verify_or_create_dir(logfile)
        execo.log.logger.addHandler(file_handler)

    # Check version
    if ACTION_CONFIG['general']['version'] != __version__:
        execo.log.logger.critical('Configuration version mismatch. Should be '
                                  'version ' + __version__)
        sys.exit(1)

    if not GLOBAL_CONFIG['path']['zfs']:
        # search in $PATH
        GLOBAL_CONFIG['path']['zfs'] = str(zfs_common.verif_exec('zfs'))
    else:
        # verify binary presence
        zfs_common.verif_exec(GLOBAL_CONFIG['path']['zfs'])

    volname = ACTION_CONFIG['volume']
    retention = ACTION_CONFIG['retention']

    if ACTION_CONFIG['action'] == 'snapshot':
        # snapshot bloc
        execo.log.logger.debug('snapshot')

        create_snapshot(volname)

        destroy_snapshot(volname, retention)

    elif ACTION_CONFIG['action'] == 'replica':
        # replica bloc
        execo.log.logger.debug('replica')
        # srcname = (volname = ACTION_CONFIG['volume'])
        rtype = ACTION_CONFIG['replica']['type']  # simple/complete
        rarchive = ACTION_CONFIG['replica']['archive']  # oldest/latest
        target_pool = ACTION_CONFIG['replica']['targetpool']

        if target_pool is None:
            target_name = volname
        else:
            if rtype == 'complete':
                # include complete source pool in target dataset
                target_name = '/'.join([target_pool, volname])

            elif rtype == 'simple':
                # add last part of source dataset to target pool
                source_lastpart = volname.rpartition('/')[2]
                target_name = '/'.join([target_pool, source_lastpart])

        srv = ACTION_CONFIG['replica']['server']

        if srv == 'localhost' and target_pool is None:
            execo.log.logger.critical('Configuration error: cannot replicate on '
                                      'same pool')
            sys.exit(1)

        replication = get_distant_snapshot(srv, target_name, first=True)

        if replication == 'full':
            # first, create target dataset on target host
            # replica target volume should'nt be mounted
            target_cmd = ' '.join([GLOBAL_CONFIG['path']['zfs'],
                                   'create -p', '-o mountpoint=none -u',
                                   target_name])
            execo.log.logger.debug(srv + ': ' + target_cmd)
            zfs_common.execute_zfs(target_cmd, host=srv)

            full_replication(srv, volname, target_name, reptype=rtype, archtype=rarchive)

        else:
            # 'replication' contain list of already replicated snapshots
            # on target, but we don't care, as incremental_replication()
            # can also be called from full_replication().
            incremental_replication(srv, volname, target_name)

        # erase replica(s) older than retention
        borne = datetime.timedelta(days=int(ACTION_CONFIG['retention']))
        destroy_replica(srv, target_name, borne)

    execo.log.logger.debug(GLOBAL_CONFIG)
    execo.log.logger.debug(ACTION_CONFIG)
