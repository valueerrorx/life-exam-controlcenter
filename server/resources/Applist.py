#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import re
from pathlib import Path
import subprocess
import os
import yaml
from configobj import ConfigObj

from PyQt5 import QtWidgets
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QSize

from config.config import USER_HOME_DIR, PLASMACONFIG
from classes.CmdRunner import CmdRunner


path_to_yml = "%s/%s" % (Path(__file__).parent.parent.parent.as_posix(), 'config/appranking.yaml')


def findApps(applistwidget, appview):
    """
    uses kbuildsycoca5 to list the current application menu from the system
    """
    apps = subprocess.check_output("kbuildsycoca5 --menutest", stderr=subprocess.DEVNULL, shell=True)
    apps = apps.decode()
    desktop_files_list = []

    for line in apps.split('\n'):
        if line == "\n":
            continue
        fields = [final.strip() for final in line.split('/')]

        filepath1 = Path("/usr/share/applications/%s" % fields[-1])
        filepath2 = Path("%s/.local/share/applications/%s" % (USER_HOME_DIR, fields[-1]))

        if filepath1.is_file():
            desktopfilelocation = filepath1

        elif filepath2.is_file():
            desktopfilelocation = filepath2
        else:
            desktopfilelocation = "none"

        if desktopfilelocation != "none":
            desktop_files_list.append(str(desktopfilelocation))

    desktop_files_list = clearDoubles(desktop_files_list)
    listInstalledApplications(applistwidget, desktop_files_list, appview)


def clearDoubles(apps):
    """delete doubles, because they can be in global menue or local at the same time"""
    # using list comprehension to remove duplicated from list
    res = []
    [res.append(x) for x in apps if x not in res]
    return res


def load_yml():
    """
    Load the yaml file config/appranking.yaml
    """
    with open(path_to_yml, 'rt') as f:
        yml = yaml.safe_load(f.read())
    return yml['apps']


def create_pattern(data):
    """
    Creates a Regex Pattern from array
    """
    erg = ".*("
    for i in data:
        erg += i + "|"
    # delete last |
    erg = erg[:-1]
    erg += ").*"
    return erg


def remove_duplicates(other_applist):
    """
    find and remove Duplicates in this AppArray
    """
    seen = set()
    newlist = []
    for item in other_applist:
        t = tuple(item)
        if t not in seen:
            newlist.append(item)
            seen.add(t)
    return newlist


def create_app_ranking(applist):
    """
    Important Apps moving to the top
    delete Kate new Window App
    """
    final_applist = []
    other_applist = []
    yml = load_yml()
    index = 0

    for key in yml:
        pattern = create_pattern(yml[key])
        for app in applist:
            match = re.search(pattern, app[2], re.IGNORECASE)  #noqa
            if match:
                final_applist.insert(index, app)
                index += 1
            else:
                other_applist.append(app)
    other_applist = remove_duplicates(other_applist)
    # other_applist sortieren
    other_applist.sort()
    return final_applist + other_applist


def _esc_char(match):
    return '\\' + match.group(0)


def makeFilenameSafe(filename):
    ''' If Filename has spaces, then escape them '''
    _to_esc = re.compile(r'\s')
    return _to_esc.sub(_esc_char, filename)


def fallbackIcon(APP):
    '''
    if an icon is Null from List, try to extract the name from the file.desktop name
    e.g. from 'libreoffice-calc.desktop' icon is 'libreoffice-document-new' > try 'libreoffice-calc'
    '''
    logger = logging.getLogger(__name__)
    name = APP[1]
    data = name.rsplit('.', 1)
    icon = QIcon.fromTheme(data[0])
    if icon.isNull():
        ''' also not possible than common fallback '''
        logger.error('Fallback Icon for: %s' % APP[1])

        # search a last time in /home/student/.life/icons/
        testfile = "%s.png" % data[0]
        found = False
        last_path = "/home/student/.life/icons/"
        for file in os.listdir(last_path):
            if testfile == file:
                # file found, take it
                found = True
                iconfile = "%s%s" % (last_path, makeFilenameSafe(file))

        if found is False:
            relativeDir = Path(__file__).parent.parent.parent
            iconfile = relativeDir.joinpath('pixmaps/empty_icon.png').as_posix()

        icon = QIcon(iconfile)

    return icon


def listInstalledApplications(applistwidget, desktop_files_list, appview):
    """
    builds a final_applist that contains, desktopfilepath, filename, name, icon
    populates a QListWidgetItem with list entries
    """
    applist = []   # [[desktopfilepath,desktopfilename,appname,appicon],[desktopfilepath,desktopfilename,appname,appicon]]

    cmdRunner = CmdRunner()
    print(desktop_files_list)
    for desktop_filepath in desktop_files_list:
        desktop_filename = desktop_filepath.rpartition('/')
        desktop_filename = desktop_filename[2]

        thisapp = [desktop_filepath, desktop_filename, "", ""]
        # didnt work sometimes anymore because of user rights problem
        try:
            file_lines = open(desktop_filepath, 'r').readlines()
            # print("%s %s" % (len(file_lines), desktop_filepath))
        except:
            # Fallback if open fails
            # read the desktop File via cat
            cmd = "cat %s" % makeFilenameSafe(desktop_filepath)
            cmdRunner.runCmd(cmd)
            file_lines = cmdRunner.getLines()

        if len(file_lines) > 1:
            for line in file_lines:
                if line == "\n":
                    continue
                # this overwrites "Name" with the latest entry if it's defined twice in the .desktop file (like in libreoffice)
                if line.startswith("Name="):
                    fields = [final.strip() for final in line.split('=')]
                    if thisapp[2] == "":   # only write this once
                        thisapp[2] = fields[1]
                elif line.startswith("Icon="):
                    fields = [final.strip() for final in line.split('=')]
                    thisapp[3] = fields[1]

        applist.append(thisapp)

    # sort applist and put most used apps on top
    final_applist = create_app_ranking(applist)
    # what apps are activated and stored in OLD Config?
    activated_apps = get_activated_apps()

    # clear appview first
    thislayout = appview.layout()
    while thislayout.count():
        child = thislayout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()

    # what apps allready added as selected
    apps_added = []
    for APP in final_applist:
        item = QtWidgets.QListWidgetItem()
        item.setSizeHint(QSize(40, 40))
        item.name = QtWidgets.QLabel()
        item.name.setText("%s" % APP[2])

        item.desktop_filename = APP[1]

        item.hint = QtWidgets.QLabel()
        item.hint.setText("sichtbar")

        icon = QIcon.fromTheme(APP[3])
        if icon.isNull():
            icon = fallbackIcon(APP)

        item.icon = QtWidgets.QLabel()
        item.icon.setPixmap(QPixmap(icon.pixmap(28)))

        item.checkbox = QtWidgets.QCheckBox()
        item.checkbox.setStyleSheet("margin-right:-2px;")

        # turn on already activated apps  - add icons to appview widget in UI
        for activated_app in activated_apps:
            app1 = activated_app
            app2 = APP[1]

            if app1 == app2:
                # is this app allready added?
                found = False
                for added_app in apps_added:
                    if added_app == app1:
                        found = True
                        break
                if found is False:
                    item.checkbox.setChecked(True)
                    iconwidget = QtWidgets.QLabel()
                    iconwidget.setPixmap(QPixmap(item.icon.pixmap()))
                    iconwidget.setToolTip(item.name.text())
                    thislayout.addWidget(iconwidget)
                    apps_added.append(app1)

        item.checkbox.clicked.connect(lambda: saveProfile(applistwidget, appview))
        verticalSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Expanding)

        grid = QtWidgets.QGridLayout()
        grid.addWidget(item.icon, 0, 0)
        grid.addWidget(item.name, 0, 1)
        grid.addItem(verticalSpacer, 0, 2)
        grid.addWidget(item.checkbox, 0, 3)
        grid.addWidget(item.hint, 0, 4)

        widget = QtWidgets.QWidget()
        widget.setLayout(grid)
        applistwidget.addItem(item)
        applistwidget.setItemWidget(item, widget)


def saveProfile(applistwidget, appview):
    """
    reads the contents of the listwidget, searches for checked items
    reads the current plasmaconfig file
    changes the plasmaconfig
    writes the plasmaconfig file
    """

    # PLASMACONFIG=Path("plasma-org.kde.plasma.desktop-appletsrc")   # (this should be the config file that is then transferred to the clients and used for the exam desktop)

    if Path(PLASMACONFIG).is_file():
        config = ConfigObj(str(PLASMACONFIG), list_values=False, encoding='utf8')

        # find section for taskmanager (sections - because plasma could contain more than one taskmanager - just in case)
        taskmanagersections = []
        for section in config:
            try:
                if config[section]["plugin"] == "org.kde.plasma.taskmanager":
                    taskmanagersections.append(section)  # don't save the actual section.. just the name of the section
            except:
                continue

    # get activated apps (those apps should be shown in taskmanager)
    items = []
    apps_activated = []
    for index in range(applistwidget.count()):
        items.append(applistwidget.item(index))

    # clear appview first
    thislayout = appview.layout()
    while thislayout.count():
        child = thislayout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()

    checked = False
    # add checked items to apps_activated in order to save them to plasmaconf and make them visible in the UI
    for item in items:
        if item.checkbox.isChecked():
            checked = True
            icon = item.icon.pixmap()
            iconwidget = QtWidgets.QLabel()
            iconwidget.setPixmap(QPixmap(icon))
            iconwidget.setToolTip(item.name.text())

            apps_activated.append(item.desktop_filename)
            thislayout.addWidget(iconwidget)

    if not checked:   # no application launchers are visible
        warninglabel = QtWidgets.QLabel()
        warninglabel.setText('Achtung: Keine Programmstarter gewählt!')
        thislayout.addWidget(warninglabel)

    # generate appstring (value for the launchers section of the taskmanager applet)
    appstring = ""

    # prepare config section for the taskmanager applet
    for targetsection in taskmanagersections:
        launchers_section = "%s][Configuration][General" % (targetsection)

        try:
            config[launchers_section]["launchers"] = ''
        except KeyError:   # key does not exist..  no pinned applications yet
            config[launchers_section] = {}
            config[launchers_section]["launchers"] = ''  # create section(key)

        if len(apps_activated) > 0:
            for app in apps_activated:
                if appstring == "":
                    appstring = "applications:%s" % (app)
                else:
                    appstring = "%s,applications:%s" % (appstring, app)

            config[launchers_section]["launchers"] = appstring
        else:  # prevent empty desktop - add geogebra
            config[launchers_section]["launchers"] = "applications:geogebra.desktop"

    # write new plasmaconfig
    config.filename = str(PLASMACONFIG)
    config.write()


def get_activated_apps():
    """Reads plasmaconfig file and searches for pinned apps in the taskmanager"""
    activated_apps = []

    if Path(PLASMACONFIG).is_file():
        config = ConfigObj(str(PLASMACONFIG), list_values=False)

        # find section for taskmanager (sections - because plasma could contain more than one taskmanager - just in case)
        taskmanagersections = []
        for section in config:
            try:
                if config[section]["plugin"] == "org.kde.plasma.taskmanager":
                    taskmanagersections.append(section)  # don't save the actual section.. just the name of the section
            except:
                continue

        # get activated apps
        for targetsection in taskmanagersections:
            launchers_section = "%s][Configuration][General" % (targetsection)

            try:
                activate_apps_string = config[launchers_section]["launchers"]
            except KeyError:   # key does not exist..  no pinned applications yet
                config[launchers_section] = {}
                # create section(key)
                config[launchers_section]["launchers"] = ""

                # add at least one application to activated apps
                appstring = "applications:geogebra.desktop"
                # and prevent empty desktops
                config[launchers_section]["launchers"] = appstring
                activate_apps_string = config[launchers_section]["launchers"]

            # make a list
            if activate_apps_string in (',', ''):  # catch a corner case
                activate_apps_list = ['applications:geogebra.desktop']
            else:
                activate_apps_list = activate_apps_string.split(",")
            # empty string will work here too
            for app in activate_apps_list:
                app = app.split(":")
                activated_apps.append(app[1])

    return activated_apps