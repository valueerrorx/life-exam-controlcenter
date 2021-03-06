#! /usr/bin/env python3
# STUDENT - CLIENT #
#
# Copyright (C) 2018 Thomas Michael Weissel
#
# This software may be modified and distributed under the terms
# of the GPLv3 license.  See the LICENSE file for details.

# for debugging run plugin from terminal - only if env_keep += PYTHONPATH is set in "sudoers" file
# export PYTHONPATH="/home/student/.life/applications/life-exam"
# sudo twistd -n --pidfile client.pid examclient -p 11411 -h 10.2.1.251 -i testuser -c 1234


import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # add application root to python path for imports

import shutil
import zipfile
import time
import datetime

from twisted.internet import reactor, protocol, stdio, defer
from twisted.protocols import basic
from twisted.application.internet import TCPClient
from zope.interface import implementer

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker

# local imports
import classes.mutual_functions as mutual_functions
import classes.system_commander as system_commander
from classes.client2server import *
from config.config import *
from config.enums import DataType, Command


class MyClientProtocol(basic.LineReceiver):
    def __init__(self, factory):
        self.factory = factory
        self.client_to_server = self.factory.client_to_server
        self.file_handler = None
        self.buffer = []
        self.line_data_list = ()
        mutual_functions.prepareDirectories()  # cleans everything and copies script files 

    # twisted
    def connectionMade(self):
        self.buffer = []
        self.file_handler = None
        self.line_data_list = ()
        line = '%s %s %s' % (Command.AUTH.value, self.factory.options['id'],  self.factory.options['pincode'])
        self.sendEncodedLine(line)
        
        print('Connected. Auth sent to the server')
        mutual_functions.showDesktopMessage('Connected. Auth sent to the server')

    # twisted
    def connectionLost(self, reason):
        self.factory.failcount += 1
        self.file_handler = None
        self.line_data_list = ()
        print('Connection to the server has been lost')
        mutual_functions.showDesktopMessage('Connection to the server has been lost')

        if self.factory.failcount > 3:  # failcount is set to 100 if server refused connection otherwise its slowly incremented
            command = "%s/client/client.py &" %(APP_DIRECTORY)
            os.system(command)
            os._exit(1)

    # twisted
    def rawDataReceived(self, data):
        print(self.line_data_list)
        filename = self.line_data_list[3]
        cleanup_abgabe = self.line_data_list[5]
        file_path = os.path.join(self.factory.files_path, filename)
        print('Receiving file chunk (%d KB)' % (len(data)))

        if not self.file_handler:
            self.file_handler = open(file_path, 'wb')

        if data.endswith(b'\r\n'):
            data = data[:-2]
            self.file_handler.write(data)
            self.file_handler.close()
            self.file_handler = None
            self.setLineMode()

            if mutual_functions.validate_file_md5_hash(file_path, self.line_data_list[4]):

                if self.line_data_list[2] == DataType.EXAM.value:  # initialize exam mode.. unzip and start exam
                    mutual_functions.showDesktopMessage('Initializing Exam Mode')
                    self._startExam(filename, file_path, cleanup_abgabe)
                    
                elif self.line_data_list[2] == DataType.FILE.value:
                    if os.path.isfile(os.path.join(SHARE_DIRECTORY, filename)):
                        filename = "%s-%s" %(filename, datetime.datetime.now().strftime("%H-%M-%S")) #save with timecode
                        targetpath = os.path.join(SHARE_DIRECTORY, filename)
                        shutil.move(file_path, targetpath)
                    else:
                        shutil.move(file_path, SHARE_DIRECTORY)

                    mutual_functions.showDesktopMessage('File %s received!' %(filename))
                    mutual_functions.fixFilePermissions(SHARE_DIRECTORY)
                    
                elif self.line_data_list[2] == DataType.PRINTER.value:
                    mutual_functions.showDesktopMessage('Receiving Printer Configuration')
                    self._activatePrinterconfig(file_path)

            else:
                os.unlink(file_path)
                print('File %s has been successfully transfered, but deleted due to invalid MD5 hash' % (filename))
        else:
            self.file_handler.write(data)


    def sendEncodedLine(self,line):
        # twisted
        self.sendLine(line.encode() )


    # twisted
    def lineReceived(self, line):
        """whenever the SERVER sent something """
        line = line.decode()   #decode the moment you recieve a line and encode it right before you send
        self.line_data_list = mutual_functions.clean_and_split_input(line)
        print("\nDEBUG: line received and decoded:\n%s\n" % self.line_data_list)
        self.line_dispatcher(line)
        


    def line_dispatcher(self, line):
        if len(self.line_data_list) == 0 or self.line_data_list == '':
            return
        """       
        FILETRANSFER  (send oder get files)
        command = self.line_data_list[0]    
        task = self.line_data_list[1]     (SEND, GET)  (SCREENSHOT, ABGABE, EXAM, FILE, PRINTER)
        filetype= self.line_data_list[2] 
        filename = self.line_data_list[3] 
        filehash = self.line_data_list[4] 
        cleanup_abgabe = client.file_data[5]
        """
        command = {
            Command.ENDMSG.value: self.client_to_server.end_msg,    
            Command.REFUSED.value: self.client_to_server.connection_refused,  
            Command.REMOVED.value: self.client_to_server.connection_removed, 
            Command.FILETRANSFER.value: self.client_to_server.file_transfer_request,  
            Command.LOCK.value: self.client_to_server.lock_screen,  
            Command.UNLOCK.value: self.client_to_server.lock_screen, 
            Command.EXITEXAM.value: self.client_to_server.exitExam, 
        }
        
        line_handler = command.get(self.line_data_list[0], None)
        line_handler(self) if line_handler is not None else self.buffer.append(line)  #attach "self" (client) # triggert entweder einen command oder (falls es einfach nur text ist) füllt einen buffer.. ENDMSG macht diesen dann als deskotp message sichtbar
        


    def _triggerAutosave(self):
        """this function uses xdotool to find windows and trigger ctrl+s shortcut on them
            which will show the save dialog the first time and silently save the document the next time
        """ 
        app_id_list = []
        for app in SAVEAPPS:
            if app == "calligrawords" or app == "calligrasheets" or app == "kate":  # these programs are qdbus enabled therefore we can trigger "save" directly from commandline
                if app == "kate":   
                    savetrigger = "file_save_all"
                else: 
                    savetrigger = "file_save"
                try:
                    command = "pidof %s" % (app)
                    pids = subprocess.check_output(command, shell=True).decode().rstrip()
                    print(pids)
                    pids = pids.split(' ')
                    print(pids)
                    for pid in pids:
                        qdbuscommand = "runuser -u %s -- qdbus org.kde.%s-%s /%s/MainWindow_1/actions/%s trigger" % (USER, app, pid, app, savetrigger)
                        print(qdbuscommand)
                        os.system(qdbuscommand)
                except:
                    print("program not running") 

            else:  # make a list of the other running apps
                command = "xdotool search --name %s &" % (app)
                app_ids = subprocess.check_output(command, shell=True).decode().rstrip()
                if app_ids:
                    app_ids = app_ids.split('\n')
                    for app_id in app_ids:
                        app_id_list.append(app_id)

        for application_id in app_id_list:  # try to invoke ctrl+s on the running apps
            command = "xdotool windowactivate %s && xdotool key ctrl+s &" % (application_id)
            os.system(command)
            print("ctrl+s sent to %s" % (application_id) )

        # try the current active window too in order to catch other applications not in config.py
        #command = "xdotool getactivewindow && xdotool key ctrl+s &"   #this is bad if you want to whatch with konsole
        #os.system(command)

    def _sendFile(self, filename, filetype):
        """send a file to the server"""
        self.factory.files = mutual_functions.get_file_list(
            self.factory.files_path)  # rebuild here just in case something changed (zip/screensho created )

        if not filename in self.factory.files:  # if folder exists
            self.sendLine(b'filename not found in client directory')
            return
        
        if filetype in DataType.list():
            line = '%s %s %s %s' % (Command.FILETRANSFER.value, filetype, filename, self.factory.files[filename][2])  # command type filename filehash
            self.sendEncodedLine(line)
        else:
            return  # TODO: inform that nothing has been done
        
        self.setRawMode()
        for bytes in mutual_functions.read_bytes_from_file(self.factory.files[filename][0]):  # complete filepath as arg
            self.transport.write(bytes)

        self.transport.write(b'\r\n')  # send this to inform the server that the datastream is finished
        self.setLineMode()  # When the transfer is finished, we go back to the line mode 
        print("DEBUG201: Filetransfer finished, back to linemode")

    def _activatePrinterconfig(self, file_path):
        """extracts the config folder /etc/cups moves it to /etc restarts cups service"""
        
        print("stopping cups service")
        command = "systemctl stop cups.service &"
        os.system(command)
        time.sleep(3)
        
        print("extracting received printer config")
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(PRINTERCONFIG_DIRECTORY)
        

        os.unlink(file_path)  # delete zip file
        time.sleep(1)

        print("restarting cups service")
        mutual_functions.showDesktopMessage('Restarting Cups Printer Service')
        command = "systemctl start cups.service &"
        os.system(command)
        
        print("fixing printer files permissions")
        command = "chmod 775 /etc/cups -R &"
        os.system(command)


    def _startExam(self, filename, file_path, cleanup_abgabe ):
        """extracts the config folder and starts the startexam.sh script"""

        if self.factory.options['host'] != "127.0.0.1":  # testClient running on the same machine
            # extract to unzipDIR / clientID / foldername without .zip
            # (cut last four letters #shutil.unpack_archive(file_path, extract_dir, 'tar')
            # python3 only but twisted RPC is not ported to python3 yet
            extract_dir = os.path.join(WORK_DIRECTORY, filename[:-4])
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)
            os.unlink(file_path)  # delete zip file
            time.sleep(2)

            # add current server IP address to firewall exceptions
            ipstore = os.path.join(EXAMCONFIG_DIRECTORY, "EXAM-A-IPS.DB")
            thisexamfile = open(ipstore, 'a+')  # anhängen
            thisexamfile.write("\n")
            thisexamfile.write("%s:5000" % self.factory.options['host'])   # server IP, port 5000 (twisted)

            command = "chmod +x %s/startexam.sh &" % EXAMCONFIG_DIRECTORY  # make examscritp executable
            os.system(command)
            time.sleep(2)
            startcommand = "%s/startexam.sh %s &" %(EXAMCONFIG_DIRECTORY, cleanup_abgabe) # start as user even if the twistd daemon is run by root
            os.system(startcommand)  # start script
        else:
            return  # running on the same machine.. do not start exam mode / do not copy zip content over original


class MyClientFactory(protocol.ReconnectingClientFactory):
    # ReconnectingClientFactory tries to reconnect automatically if connection fails
    def __init__(self, files_path, options):
        self.files_path = files_path
        self.options = options
        self.deferred = defer.Deferred()
        self.files = None
        self.failcount = 0
        self.delay
        self.client_to_server = ClientToServer() # type: ClientToServer
        
        #self.factor = 1.8

    def clientConnectionFailed(self, connector, reason):
        self.failcount += 1

        if self.failcount > 3:  # failcount is set to 100 if server refused connection otherwise its slowly incremented
            command = "%s/client/client.py &" %(APP_DIRECTORY)
            os.system(command)
            os._exit(1)

        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def buildProtocol(self, addr):
        # http://twistedmatrix.com/documents/12.1.0/api/twisted.internet.protocol.Factory.html#buildProtocol
        return MyClientProtocol(self)


"""
Um diese Datei als twisted plugin mit twistd -l client.log --pidfile client.pid examclient -p PORT -h HOST starten zu können 
muss die ClientFactory im Service (MyServiceMaker) gestartet werden
tapname ist der name des services 
damit twistd dieses überallfindet sollte das stammverzeichnis im pythonpath eingetragen werden

export PYTHONPATH="/pathto/life-exam-controlcenter:$PYTHONPATH"


"""


# from twisted.application.internet import backoffPolicy    #only with twisted >=16.03
# retryPolicy=backoffPolicy(initialDelay=1, factor=0.5)    # where to put ???


class Options(usage.Options):
    optParameters = [["port", "p", 5000, "The port number to connect to."],
                     ["host", "h", '127.0.0.1', "The host machine to connect to."],
                     ["id", "i", 'unnamed', "A custom unique Client id."],
                     ["pincode", "c", '12345', "The pincode needed for authorization"]
                     ]



@implementer(IServiceMaker, IPlugin)
class MyServiceMaker(object):
    tapname = "examclient"
    description = "LiFE-Exam Client"
    options = Options

    def makeService(self, options):
        return TCPClient(options["host"],
                         int(options["port"]),
                         MyClientFactory(CLIENTFILES_DIRECTORY, options))


serviceMaker = MyServiceMaker()
