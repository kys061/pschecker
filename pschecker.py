import subprocess
import time
from logging.handlers import RotatingFileHandler
# from logging import StreamHandler
import logging
import re
import sys

#echo 'show int external1 flows top 10000 by average_rate select distress geolocation autonomous_system retransmissions round_trip_time timeouts udp_jitter red_threshold_discards in_control delay rtt_server rtt_client' |sudo /opt/stm/target/pcli/stm_cli.py admin:FlowCommand#1@localhost
# echo 'show parameter ' |sudo /opt/stm/target/pcli/stm_cli.py admin:FlowCommand#1@localhost |grep 'interfaces_per_core' |awk '{print $2}'
# echo 'show int ' |sudo /opt/stm/target/pcli/stm_cli.py admin:FlowCommand#1@localhost |grep 'Ethernet' |awk '{print $1}'

# logging
LOG_FILENAME = r'/var/log/pschecker.log'

stm_id = r'monitor_only'
stm_pass = r'Monitor_Only#1'
stm_host = r'localhost'
stm_script_path = r'/opt/stm/target/pcli/stm_cli.py'
stm_start = False
stm_chk_interval = 5

logger = None


def make_logger():
    global logger
    try:
        logger = logging.getLogger('saisei.pschecker')
        fh = RotatingFileHandler(LOG_FILENAME, 'a', 50 * 1024 * 1024, 4)
        logger.setLevel(logging.INFO)
        # else:
        #     fh = StreamHandler(sys.stdout)
        #     logger.setLevel(logging.INFO)
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
    return subprocess.check_output("sudo ps -elL |grep %s" % name, shell=True)
    # return check_output(["ps", "-elL", "|", "grep", name])


def subprocess_open(command):
    try:
        popen = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        (stdoutdata, stderrdata) = popen.communicate()
    except Exception as e:
        logger.error("subprocess_open() cannot be executed, {}".format(e))
        pass
    return stdoutdata, stderrdata


def reboot_system(command):
    try:
        subprocess_open(command)
    except Exception as e:
        logger.error("reboot system() cannot be executed, {}".format(e))
        pass


def main():
    global stm_start
    if re.search('pschecker.py', sys.argv[0]):
        make_logger()
        time.sleep(1)

    while not stm_start:
        # print(subprocess_open(get_command(r"show int", "| egrep '(Socket|Ethernet)' |awk '{print $1\",\"$6}'")))
        ints_enable = subprocess_open(get_command(r"show int", "| egrep '(Socket|Ethernet)' |awk '{print $1\",\"$6}'"))[0].split()

        try:
            ints_count = len(ints_enable)
        except Exception as e:
            logger.error("cannot get length of ints_count, {}".format(e))

        enable_count = 0

        for int_enable in ints_enable:
            if 'Enable' or 'enable' in int_enable:
                enable_count += 1
            #     print('true')
            #     # stm_start = True
            # else:
            #     print('false')
            #     # stm_start = False
        # print(ints_enable)
        if enable_count == ints_count:
            logger.info("Change stm_start to {{True}}...")
            stm_start = True
        time.sleep(stm_chk_interval)
    time.sleep(stm_chk_interval)

    while stm_start:
        parameter = subprocess_open(get_command(r"show parameter", r"|grep 'interfaces_per_core' |awk '{print $2}'"))[0]\
            .strip()

        # check logic
        logger.info("STM Thread Checking Start...")
        if int(parameter) >= 2:
            thread_count = 2
            _interfaces = subprocess_open(get_command(r"show int",
                                                      r"| grep 'Ethernet' |grep 'External' |awk '{{ print $1 }}'"))[0]\
                .split('\n')
            interfaces = [_int for _int in _interfaces if len(_int) > 0]
            # print(interfaces)
            for _int in interfaces:
                if not get_pid(_int):
                    logger.info('no {} threads : start rebooting...'.format(_int))
                    reboot_system('sudo reboot')
                    # print('no {} thread : reboot'.format(_int))
                else:
                    logger.info('{} threads is alive,  No need to reboot!'.format(_int))
        elif int(parameter) == 1:
            thread_count = 4
            _interfaces = subprocess_open(get_command(r"show int", r"| grep 'Ethernet' |awk '{{ print $1 }}'"))[0].split('\n')
            interfaces = [_int for _int in _interfaces if len(_int) > 0]
            # print(interfaces)
            for _int in interfaces:
                if not get_pid(_int):
                    logger.info('no {} threads : start rebooting...'.format(_int))
                    reboot_system('sudo reboot')
                else:
                    logger.info('{} threads is alive,  No need to reboot!'.format(_int))
        else:
            logger.info('Interfaces per core is 0, Please check parameters...')
        time.sleep(stm_chk_interval)


if __name__ == "__main__":
    main()
