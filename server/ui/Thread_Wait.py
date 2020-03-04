#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Stefan Hagmann

import time

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal
from server.resources.MyCustomWidget import MyCustomWidget


class Thread_Wait(QtCore.QThread):
    
    client_finished = pyqtSignal(str)
    client_received_file = pyqtSignal(MyCustomWidget)
    client_lock_screen = pyqtSignal(str)
    client_unlock_screen = pyqtSignal(str)
    
    
    running = False
    clients = []
    
    def __init__(self, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.running = False
        
    def __del__(self):
        self.wait()
        
    def fireEvent_Lock_Screen(self, who):
        self.client_lock_screen.emit(who)
        
    def fireEvent_UnLock_Screen(self, who):
        self.client_unlock_screen.emit(who)
        
    def fireEvent_Abgabe_finished(self, who):
        self.client_finished.emit(who)   
    
    def fireEvent_File_received(self, clientWidget):
        """ client has received a file """
        #delete client from list
        if len(self.clients)>0:
            self.deleteItemFromList(clientWidget.getName())
            self.client_received_file.emit(clientWidget)
            
    def deleteItemFromList(self, who):
        """ delete an Item from the client list """
        index=-1
        for x in range(len(self.clients)):
            if self.clients[x].id == who:
                index = x
                break
        #remove Element
        #time critical only if you find an index
        if index!=-1:
            self.clients = self.clients[:index] + self.clients[index+1 :]
        
    def isAlive(self):
        if self.running:
            return True
        else:
            return False
        
    def stop(self):
        self.running = False
        self.quit()
    
    def setClients(self, clients):
        """ a list within all clients to actually work with """
        self.clients = clients
     
    def run(self):    
        """
        on exit Exam, this thread waits for all Clients to sent their files,
        the fireEvent() will be fired
        """
        self.running = True
        while(self.running):
            time.sleep(0.01)
    
        return 0
    