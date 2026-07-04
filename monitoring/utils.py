import logging as log
import os
import sys


def root_check():
    '''A function to check if the program is running with root privileges'''
    if os.geteuid() != 0:
        log.critical("Root privilege required to run this script.")
        print("Run as root.")
        sys.exit(os.EX_NOPERM)
