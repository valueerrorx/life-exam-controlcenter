#!/bin/bash
# last updated: 13.12.2016

BACKUPDIRADVANCED="/home/student/.kde/life-resources/backup-exam"
CONFDIR="/etc/NetworkManager/system-connections/"
CONFFILE="/etc/NetworkManager/system-connections/lifespot"
PUBLIC="/home/student/ABGABE"
PUBLICIN="/home/student/ABGABE/IN"
PUBLICOUT="/home/student/ABGABE/OUT"
EXPORTS="/etc/exports"
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"   ##get script directory




if [ "$(id -u)" != "0" ]; then
    kdialog  --msgbox 'You need root privileges - Stopping program' --title 'LIFE' --caption "LIFE" > /dev/null
    exit 1
fi

APAVAILABLE=$(iw list|grep AP |wc -l)

if [[( $APAVAILABLE -eq 0   )]];
then
    kdialog  --msgbox 'Ihre wlan Karte unterstützt die Accesspoint-Funktion nicht!\nStoppe Programm' --title 'LIFE' --caption "LIFE" > /dev/null
    exit 0
else
    echo "fu"
fi



#---------------------------------------------------------------------#
# NETWORKMANAGER Verbindung vorbereiten, konfigurieren und starten
#---------------------------------------------------------------------#

getSSID(){
    SSID=$(kdialog  --caption "LIFE" --title "LIFE" --inputbox "Geben sie bitte die gewünschte SSID an!");
    if [ "$?" = 0 ]; then
        PASSWD=$(kdialog  --caption "LIFE" --title "LIFE" --inputbox 'Geben sie bitte das gewünschte Passwort an! 
(mind. 8 Zeichen)');
        if [ "$?" = 0 ]; then
            SIZE=${#PASSWD}
            if [ "$SIZE" -gt 7 ]; then
                sudo -u student kdialog  --caption "LIFE" --title "LIFE" --passivepopup "Password ok!" 3
            else
                kdialog  --caption "LIFE" --title "LIFE" --error "Das Passwort ist zu kurz!"
                getSSID 
            fi
        else
            exit 0
        fi
    else
        exit 0
    fi
}

getSSID





        
   
if [ -f  $CONFFILE ];then
    echo "connection exists"
else   # erstellt eine networkmanager verbindung (nicht an ein gerät gebunden)
    sudo nmcli connection add type 802-11-wireless con-name lifespot ifname "*" ssid lifespot 
    sudo systemctl restart network-manager.service 
fi 



# configuration in die neue verbindung schreiben
echo "[connection]
id=lifespot
uuid=6fae1135-c011-4908-a7d5-6505a88d7a53
type=wifi
autoconnect=false
permissions=user:student:;
secondaries=

[wifi]
mac-address-blacklist=
mac-address-randomization=0
mode=ap
seen-bssids=
ssid=${SSID}

[wifi-security]
group=
key-mgmt=wpa-psk
pairwise=
proto=
psk=${PASSWD}

[ipv4]
dns-search=
method=shared

[ipv6]
addr-gen-mode=stable-privacy
dns-search=
method=auto
" > ${CONFFILE}
    
# neue config initialisieren und starten
sudo systemctl restart network-manager.service 

sudo -u student kdialog  --caption "LIFE" --title "LIFE" --passivepopup "Accespoint wird aktiviert!" 3
sleep 3
# verbindung aktivieren
exec nmcli c up lifespot &
sleep 1  #warte bis das interface up ist  



#-----------------------------------------------------#
#  Zeige deine IP  (WLAN)
#-----------------------------------------------------#
    

IFACE=$(iwconfig 2>/dev/null |grep -o "^\w*")   #get wlan device name

IP=$(ip -4 address show dev ${IFACE} |grep inet | awk '{print $2}'|cut -d '/' -f 1)
if [ "$IP" = "" ]; then
    sleep 4  #warte länger bis das interface up ist
    IP=$(ip -4 address show dev ${IFACE} |grep inet | awk '{print $2}'|cut -d '/' -f 1)
fi
kdialog  --msgbox "Deine wlan IP Adresse lautet:\n\n$IP" --title 'LIFE' --caption "LIFE" > /dev/null
            
    
    
    
    
    
    
    
    
    
    
#-----------------------------------------------------#
#  NFS (Verzeichnisse vorbereiten und starten
#-----------------------------------------------------#


lifesudo $DIR/gui-activate-life-share-root.sh &

