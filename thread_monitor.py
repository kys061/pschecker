#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
# Write by yskang(kys061@gmail.com)

import subprocess
import time
from logging.handlers import RotatingFileHandler
import logging
import sys
import re

stm_ver = r'7.2'
stm_id = r'cli_admin'
stm_pass = r'cli_admin'
stm_host = r'localhost'
stm_port = r'5000'
stm_script_path = r'/opt/stm/target/pcli/stm_cli.py'
stm_flow_path = 'configurations/running/flows/'
stm_interface_path = r'configurations/running/interfaces/'

stm_start = False
err_marked = True
stm_chk_interval = 5
thread_chk_count = 0

logger = None

err_lists = ['Cannot connect to server', 'does not exist', 'no matching objects', 'waiting for server']

MUL = 30
LOG_FILENAME = r'/var/log/thread_monitor.log'


def make_logger():
    global logger
    try:
        logger = logging.getLogger('saisei.thread_monitor')
        fh = RotatingFileHandler(LOG_FILENAME, 'a', 50 * 1024 * 1024, 4)
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except Exception as e:
        print('cannot make logger, please check system, {}'.format(e))
    else:
        logger.info("***** logger starting %s *****" % (sys.argv[0]))


def get_command(cmd, param=' '):
    return 'echo \'{0} \' |sudo {1} {2}:{3}@{4} {5}'\
        .format(cmd, stm_script_path, stm_id, stm_pass, stm_host, param)


def get_pid(name):
    try:
        subprocess.check_output("sudo ps -elL |grep %s" % name, shell=True)
    except subprocess.CalledProcessError:
        return False
    else:
        return True


def subprocess_open(command):
    try:
        p_open = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        (stdout_data, stderr_data) = p_open.communicate()
    except Exception as e:
        logger.error("subprocess_open() cannot be executed, {}".format(e))
        pass
    else:
        return stdout_data, stderr_data


def reboot_system():
    try:
        subprocess_open('sudo reboot')
    except Exception as e:
        logger.error("reboot system() cannot be executed, {}".format(e))
        pass


def check_error(raw_data):
    global err_marked
    if raw_data != '':
        for err in err_lists:
            if err in raw_data:
                err_marked = True
                err_contents = re.sub(r"\n", "", err)
                logger.error('failed from rest cli, msg : {}'.format(err_contents))
                return True
            else:
                err_marked = False
        if not err_marked:
            return False
    else:
        try:
            raise Exception('NullDataError - data from subprocess is Null')
        except Exception as e:
            logger.error('{}'.format(e))
            pass


def main():
    global stm_start
    global thread_chk_count
    global err_marked

    make_logger()
    time.sleep(1)

    while not stm_start:
        if stm_ver == '7.2':
            ints_enable = subprocess_open(
                get_command(r"show int", "| egrep '(Socket|Ethernet)' |awk '{print $1\",\"$6}'"))[0]
            if not check_error(ints_enable):
                ints_enable.split()
        else:
            ints_enable = subprocess_open(
                get_command(r"show int", "| egrep '(Socket|Ethernet)' |awk '{print $1\",\"$4}'"))[0]
            if not check_error(ints_enable):
                ints_enable.split()

        if not err_marked:
            enable_count = 0
            try:
                ints_count = len(ints_enable)
            except Exception as e:
                logger.error("cannot get length of ints_count, {}".format(e))
            else:
                for int_enable in ints_enable:
                    if 'Enable' or 'enable' in int_enable:
                        enable_count += 1

                if enable_count == ints_count:
                    logger.info("Change stm_start to TRUE...")
                    stm_start = True
            time.sleep(stm_chk_interval)
        else:
            stm_start = False
            logger.error("stm is error or id/password is wrong, please check stm, error stats: {}".format(err_marked))
            logger.error("Try again after 30sec...")
            time.sleep(30)

    while stm_start:
        parameter = subprocess_open(
            get_command(r"show parameter", r"|grep 'interfaces_per_core' |awk '{print $2}'"))[0].strip()
        logger.info("STM Thread Checking Start...")

        if int(parameter) >= 2:
            thread_count = 2
            _interfaces = subprocess_open(
                get_command(r"show int", r"| grep 'Ethernet' |grep 'External' |awk '{{ print $1 }}'"))[0].split('\n')
            interfaces = [_int for _int in _interfaces if len(_int) > 0]

            for _int in interfaces:
                if not get_pid(_int):
                    logger.info('no {} threads : will start rebooting...'.format(_int))
                    thread_chk_count += 1
                else:
                    logger.info('{} threads is alive,  No need to reboot!'.format(_int))
        elif int(parameter) == 1:
            thread_count = 4
            _interfaces = subprocess_open(
                get_command(r"show int", r"| grep 'Ethernet' |awk '{{ print $1 }}'"))[0].split('\n')
            interfaces = [_int for _int in _interfaces if len(_int) > 0]
            for _int in interfaces:
                if not get_pid(_int):
                    logger.info('no {} threads : will start rebooting...'.format(_int))
                    thread_chk_count += 1
                else:
                    logger.info('{} threads is alive,  No need to reboot!'.format(_int))
        else:
            thread_count = 10
            logger.info('Interfaces per core is 0, Please check parameters...')

        if thread_chk_count > thread_count*MUL:
            logger.info('No stm threads : start rebooting now...')
            reboot_system()
        time.sleep(stm_chk_interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("The script is terminated by interrupt!")
        print("\r\nThe script is terminated by user interrupt!")
        print("Bye!!")
        sys.exit()
