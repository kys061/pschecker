#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
# Write by yskang(kys061@gmail.com)

import subprocess
import time
from logging.handlers import RotatingFileHandler
import logging
import sys
import re
from time import sleep

stm_ver = r'7.3'
stm_id = r'cli_admin'
stm_pass = r'cli_admin'
stm_host = r'localhost'
stm_port = r'5000'
stm_script_path = r'/opt/stm/target/pcli/stm_cli.py'
stm_flow_path = 'configurations/running/flows/'
stm_interface_path = r'configurations/running/interfaces/'
LOG_FILENAME = r'/var/log/stm_thread_monitor.log'

is_stm_started = False
is_stm_err = True

stm_chk_interval = 10
thread_chk_count = 0
apache_restart_count = 0

logger = None

err_lists = ['Cannot connect to server', 'does not exist', 'no matching objects', 'waiting for server']

MUL = 30
##########

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


def logging_line():
    logger.info("=================================")

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


def subprocess_open(command, timeout):
    try:
        p_open = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    except Exception as e:
        logger.error("subprocess_open() cannot be executed, {}".format(e))
        pass
    else:
        for t in xrange(timeout):
            sleep(1)
            if p_open.poll() is not None:
                (stdout_data, stderr_data) = p_open.communicate()
                return stdout_data, stderr_data
        p_open.kill()
        return [False]


def reboot_system():
    try:
        logger.info("Try system restarting")
        subprocess_open('sudo reboot', 10)
    except Exception as e:
        logger.error("reboot system() cannot be executed, {}".format(e))
        pass


def restart_apache():
    try:
        global version
        global apache_restart_count

        logger.info("Try APACHE restarting")
        if version == 'V7.3':
            subprocess_open('sudo service apache2 restart', 10)
            apache_restart_count += 1
        elif version == 'V7.1':
            subprocess_open('sudo apache2ctl restart', 10)
            apache_restart_count += 1
        else:
            logger.error("The version of stm is not correct.. plz check.")
            logging_line()
    except Exception as e:
        logger.error("reboot system() cannot be executed, {}".format(e))
        logging_line()
        pass


def get_stm_version():
    if check_subprocess_data(subprocess_open(
            get_command("show version", "| awk '{print $1}' | egrep 'V[0-9]+\.[0-9]+' -o"), 10)):
        try:
            stm_version = subprocess_open(get_command("show version", "| awk '{print $1}' | egrep 'V[0-9]+\.[0-9]+' -o"), 10)[0]
        except Exception as e:
            logger.error("reboot system() cannot be executed, {}".format(e))
            pass
        else:
            # print('{}:V7.3'.format(stm_version.strip()))
            # print(stm_version.strip() == 'V7.3')
            stm_version = stm_version.strip()
            return stm_version
    else:
        return False

def check_subprocess_data(sub):
    result = sub
    if result is '':
        try:
            raise Exception('NullDataError, result from subprocess is Null')
        except Exception as e:
            logger.error('{}'.format(e))
            pass
    elif result is False:
        try:
            raise Exception('TimeOutError, No respond from stm')
        except Exception as e:
            logger.error('{}'.format(e))
            pass
    else:
        return True


def check_data_error(raw_data):
    global is_stm_err

    for err in err_lists:
        if err in raw_data:
            is_stm_err = True
            err_contents = re.sub(r"\n", "", err)
            logger.error('failed from rest cli, msg : {}'.format(err_contents))
            logging_line()
        else:
            is_stm_err = False

    if not is_stm_err:
        return True
    else:
        return False

def check_stm_status():
    global is_stm_err
    global version

    logger.info("The version of stm is now {}".format(version))
    # print(version == 'V7.3')
    if version == "V7.3":
        if check_subprocess_data(subprocess_open(
            get_command(r"show int", "| egrep '(Socket|Ethernet)' |awk '{print $1\",\"$6}'"), 10)[0]):
            raw_data = subprocess_open(
                get_command(r"show int", "| egrep '(Socket|Ethernet)' |awk '{print $1\",\"$6}'"), 10)[0]
        else:
            return False
    elif version is "V7.1":
        if check_subprocess_data(subprocess_open(
            get_command(r"show int", "| egrep '(Socket|Ethernet)' |awk '{print $1\",\"$4}'"), 10)[0]):
            raw_data = subprocess_open(
                get_command(r"show int", "| egrep '(Socket|Ethernet)' |awk '{print $1\",\"$4}'"), 10)[0]
        else:
            return False
    else:
        logger.error("The version of stm is not correct.. plz check.")
        logging_line()
        return False

    return check_data_error(raw_data)


def check_dpdk_interface(enabled_ints):
    try:
        global is_stm_started
        enable_count = 0
        enabled_ints.split()
        ints_count = len(enabled_ints)
    except Exception as e:
        logger.error("cannot get length of ints_count, {}".format(e))
        logging_line()
    else:
        for enabled_int in enabled_ints:
            if 'Enable' or 'enable' in enabled_int:
                enable_count += 1

        if enable_count == ints_count:
            logger.info("Change is_stm_started to TRUE...")
            logger.info("STM is now running...")
            logging_line()
            is_stm_started = True
            return True
        else:
            logger.info("STM is NOT running...")
            logging_line()
            return False

def check_stm_enable_count():
    global is_stm_started
    global is_stm_err
    global version

    logger.info("STM status checking is started...")
    if not is_stm_err:
        if version == 'V7.3':
            if check_subprocess_data(subprocess_open(
                    get_command(r"show int", "| egrep '(Socket|Ethernet)' |awk '{print $1\",\"$6}'"), 10)[0]):
                enabled_ints = subprocess_open(
                    get_command(r"show int", "| egrep '(Socket|Ethernet)' |awk '{print $1\",\"$6}'"), 10)[0]
            else:
                return False
        elif version == 'V7.1':
            if check_subprocess_data(subprocess_open(
                get_command(r"show int", "| egrep '(Socket|Ethernet)' |awk '{print $1\",\"$4}'"), 10)[0]):
                enabled_ints = subprocess_open(
                    get_command(r"show int", "| egrep '(Socket|Ethernet)' |awk '{print $1\",\"$4}'"), 10)[0]
            else:
                return False
        else:
            logger.error("The version of stm is not correct.. plz check.")
            logging_line()
            return False
        return check_dpdk_interface(enabled_ints)
    else:
        is_stm_started = False
        logger.error("STM is error or stm's id/password is wrong, please check stm, error stats: {}".format(is_stm_err))
        logger.error("Try again after 30sec...")
        logging_line()
        return False


def check_interface_thread():
    global thread_chk_count

    logger.info("STM Thread Checking is Started...")

    if check_subprocess_data(subprocess_open(
        get_command(r"show parameter", r"|grep 'interfaces_per_core' |awk '{print $2}'"), 10)[0].strip()):
        parameter = subprocess_open(
            get_command(r"show parameter", r"|grep 'interfaces_per_core' |awk '{print $2}'"), 10)[0].strip()
    else:
        return False

    if int(parameter) >= 2:
        thread_count = 2
        _interfaces = subprocess_open(
            get_command(r"show int", r"| grep 'Ethernet' |grep 'External' |awk '{{ print $1 }}'"), 10)[0].split('\n')
        interfaces = [_int for _int in _interfaces if len(_int) > 0]

        for _int in interfaces:
            if not get_pid(_int):
                logger.info('no {} threads : will start rebooting...'.format(_int))
                thread_chk_count += 1
                logging_line()
            else:
                logger.info('{} threads is alive,  No need to reboot!'.format(_int))
                logging_line()
    elif int(parameter) == 1:
        thread_count = 4
        _interfaces = subprocess_open(
            get_command(r"show int", r"| grep 'Ethernet' |awk '{{ print $1 }}'"), 10)[0].split('\n')
        interfaces = [_int for _int in _interfaces if len(_int) > 0]
        for _int in interfaces:
            if not get_pid(_int):
                logger.info('no {} threads : will start rebooting...'.format(_int))
                thread_chk_count += 1
            else:
                logger.info('{} threads is alive,  No need to reboot!'.format(_int))
        logging_line()
    else:
        thread_count = 10
        logger.info('Interfaces per core is 0, Please check parameters...')
        logging_line()

    if thread_chk_count > thread_count * MUL:
        logger.info('No stm threads : start rebooting now...')
        logging_line()
        reboot_system()


def main():
    global version
    global is_stm_started, is_stm_err
    global thread_chk_count, apache_restart_count

    make_logger()
    time.sleep(1)

    while not is_stm_started:
        if check_stm_status():
            check_stm_enable_count()
            time.sleep(stm_chk_interval)
        time.sleep(30)

    while is_stm_started:
        if check_stm_status():
            check_stm_enable_count()
            time.sleep(stm_chk_interval)

        if is_stm_started:
            check_interface_thread()
            time.sleep(stm_chk_interval)
        else:
            logger.error("STM or APACHE is not running, Please check admin.")
            if apache_restart_count > 7:
                apache_restart_count = 0
                reboot_system()
            else:
                restart_apache()


### pre-executed
version = get_stm_version()
###

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("The script is terminated by interrupt!")
        print("\r\nThe script is terminated by user interrupt!")
        print("Bye!!")
        sys.exit()