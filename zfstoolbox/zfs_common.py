#!/usr/bin/env python3
# coding: utf-8

# $Id: zfs_common.py 1116 2019-09-06 08:46:29Z gruiick $
# SPDX-License-Identifier: BSD-2-Clause

"""
    Common functions for manage_conf.py and zfs_actions.py

    TODO/FIXME: reclasser par ordre alphabétique
"""

import os
import sys
import distutils.spawn
import distutils.util
import datetime
import yaml

import execo

__version__ = "0.6"
__author__ = "See AUTHORS"
__copyright__ = "Copyright 2018, PSMN, ENS de Lyon"
__credits__ = "See CREDITS"
__license__ = "BSD-2"
__maintainer__ = "Loïs Taulelle"
__email__ = "None"
__status__ = "Production"


def erase_file(fichier):
    """
        erase the file given as argument
    """
    try:
        os.remove(fichier)
        execo.log.logger.info(str(fichier) + ' erased')
    except EnvironmentError as err:
        execo.log.logger.warning('Environment Error: ' + err.strerror +
                                 ' ' + err.errno +
                                 ' ' + err.filename)


def execute_process(commande, silent=True):
    """
        execute commande, return nothing by default, else return stdout
    """
    with execo.process.Process(commande).run() as process:
        if process.exit_code != 0:
            execo.log.logger.critical('process:\n' + str(process))
            execo.log.logger.warning('process stdout:\n' + process.stdout)
            execo.log.logger.warning('process stderr:\n' + process.stderr)

    if not silent:
        execo.log.logger.debug(type(process.stdout))
        return process.stdout


def execute_zfs(zfscmd, host=None, shell=False, nolog=False):
    """
        execute zfs command, return stdout as a string or None
        if host, use SshProcess (remote)
        if shell, use shell=True (accept '|' in zfscmd)
        if nolog, use nolog_exit_code=True (don't go CRITICAL rightaway)
            process zfs expected error 'dataset does not exist'
    """

    use_ssh = host not in [None, 'localhost']
    args = [zfscmd, host] if use_ssh else [zfscmd]
    kwargs = {'nolog_exit_code': nolog, 'shell': shell}
    func = execo.process.SshProcess if use_ssh else execo.process.Process

    execo.log.logger.debug(str(func), str(args), str(kwargs))

    try:
        process = func(*args, **kwargs).run()
    except execo.exception.ProcessesFailed:
        execo.log.logger.exception('Process error')
        sys.exit(1)

    if process.exit_code == 0:  # everything is OK, return stdout
        execo.log.logger.debug(type(process.stdout))
        return process.stdout

    # NOTE: every zfs error code seem to be 256.
    # best to search "dataset does not exist" in stdout/stderr
    message = process.stdout + process.stderr
    if message.count('dataset does not exist'):
        execo.log.logger.debug('This is expected: dataset does not exist')
        return None

    # something went wrong, explode nicely
    execo.log.logger.critical('process:\n%s', process)
    execo.log.logger.warning('process stdout:\n%s', process.stdout)
    execo.log.logger.warning('process stderr:\n%s', process.stderr)
    sys.exit(1)


def filter_date_snap(liste_snap):
    """ filter list of snapshots, return list of dates """

    lstsnapdates = []

    for element in liste_snap:
        # keep the second part of snapshot name, as a date
        # ignore snapshots which aren't in the format "dataset@snapshot-%Y%m%d%H%M%S"
        try:
            # avoid dataset part, as it can contain '-'
            temppartition = element.partition('@')[2]
            execo.log.logger.debug('volume: ' + element.partition('@')[0])
            # we're only insterested in the date part
            tempdate = datetime.datetime.strptime(temppartition.partition('-')[2], '%Y%m%d%H%M%S')
            execo.log.logger.debug('date: ' + str(tempdate))
            lstsnapdates.append(tempdate)
        except ValueError:
            execo.log.logger.debug('ignored: ' + str(element))
            pass

    return lstsnapdates


def load_yaml_file(yamlfile):
    """ Load yamlfile, return a dict

        yamlfile is mandatory, using safe_load
        Throw yaml errors, with positions, if any, and quit.
        return a dict
    """
    try:
        with open(yamlfile, 'r') as fichier:
            contenu = yaml.safe_load(fichier)
            return contenu
    except IOError:
        execo.log.logger.critical('Unable to read/load config file: ' +
                                  fichier.name)
        sys.exit(1)
    except yaml.MarkedYAMLError as erreur:
        if hasattr(erreur, 'problem_mark'):
            mark = erreur.problem_mark
            msg_erreur = "YAML error position: ({}:{}) in ".format(mark.line + 1,
                                                                   mark.column)
            execo.log.logger.critical(msg_erreur + str(fichier.name))
        sys.exit(1)


def query_yesno(question):
    """
        Ask a yes/no question via input() and return 1 if y(es), 0 elsewhere.
        no default
    """
    print('\n' + question + ' [y/n]?')
    while True:
        try:
            return distutils.util.strtobool(input().lower())
        except ValueError:
            print('Please reply "y" or "n".')


def save_crontab(nomfichier, contenufichier):
    """
        Write crontab file
    """
    try:
        verify_or_create_dir(nomfichier)
        with open(nomfichier, 'w') as fic:
            fic.write('\n'.join(contenufichier))
            fic.write('\n')
    except EnvironmentError as err:
        execo.log.logger.critical('Environment Error: ' + err.strerror +
                                  ' ' + err.errno + ' ' + err.filename)
        sys.exit(1)


def save_yaml_file(yamlfile, data):
    """ save data{dict} into yamlfile

    Filename is mandatory. Data must be a dict{}.
    Throw errors using execo logger, and quit
    """
    try:
        with open(yamlfile, 'w') as fichier:
            fichier.write('%YAML 1.1\n---\n')
            yaml.safe_dump(data, stream=fichier, encoding='utf-8',
                           canonical=False, default_flow_style=False,
                           default_style='')
    except EnvironmentError as err:
        execo.log.logger.critical('Environment Error: ' + err.strerror +
                                  ' ' + str(err.errno) + ' ' + err.filename)
        sys.exit(1)
    except yaml.YAMLError as erreur:
        execo.log.logger.critical('YAML error: ' + erreur + ', ' + fichier.name)
        sys.exit(1)


def verif_exec(binaire):
    """ 'which'-like function
        return the complete path of 'binaire', if found in $PATH
    """
    try:
        cmd_exist = distutils.spawn.find_executable(binaire)
        if cmd_exist is None:
            execo.log.logger.warning('Command not found: ' + binaire)
        else:
            execo.log.logger.debug('Command found: ' + cmd_exist)
            return cmd_exist
    except OSError as error:
        execo.log.logger.critical('Execution failed: ' + error)


def verif_root():
    """
        Verify if euid 0, if not, exit(1)
    """
    if int(os.geteuid()) != 0:
        execo.log.logger.critical('You are not root. Use sudo or biroute.')
        sys.exit(1)


def verify_or_create_dir(filename):
    """
        Verify if path exist (before a file will be created)
        create path if it doesn't exist
    """
    execo.log.logger.debug(filename)
    if not os.path.exists(os.path.dirname(filename)):
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
        except OSError as err:
            execo.log.logger.critical('Cannot create directory: ' + err.strerror)
            sys.exit(1)


if __name__ == '__main__':
    print('this file is to be imported')
