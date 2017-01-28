#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os

SERVER_IP = "localhost"
SERVER_PORT = 5000

USER_HOME_DIR = "/home/student"

# work directory for client and server  - absolute paths 
WORK_DIRECTORY=os.path.join(USER_HOME_DIR,".life/EXAM") 


SCRIPTS_DIRECTORY=os.path.join(WORK_DIRECTORY,"scripts")
EXAMCONFIG_DIRECTORY = os.path.join(WORK_DIRECTORY,"EXAMCONFIG")

CLIENTFILES_DIRECTORY = os.path.join(WORK_DIRECTORY,"CLIENT")
CLIENTSCREENSHOT_DIRECTORY = os.path.join(CLIENTFILES_DIRECTORY,"screenshots")
CLIENTUNZIP_DIRECTORY = os.path.join(CLIENTFILES_DIRECTORY,"unzip")
CLIENTZIP_DIRECTORY = os.path.join(CLIENTFILES_DIRECTORY,"zip")

SERVERFILES_DIRECTORY = os.path.join(WORK_DIRECTORY,"SERVER")
SERVERSCREENSHOT_DIRECTORY = os.path.join(SERVERFILES_DIRECTORY,"screenshots")
SERVERUNZIP_DIRECTORY = os.path.join(SERVERFILES_DIRECTORY,"unzip")
SERVERZIP_DIRECTORY = os.path.join(SERVERFILES_DIRECTORY,"zip")

ABGABE_DIRECTORY = os.path.join(USER_HOME_DIR,"ABGABE")


# relative paths
DATA_DIRECTORY = "./DATA"


