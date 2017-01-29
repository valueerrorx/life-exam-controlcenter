#!/bin/bash
# last updated: 26.01.2017

# SERVER FILE #


IPSFILE="$HOME/.life/EXAM/EXAMCONFIG/EXAM-A-IPS.DB"
 
 
setIPtables(){
    #allow loopback 
    sudo iptables -I INPUT 1 -i lo -j ACCEPT
    #allow DNS
    sudo iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
  
  
    if [ -f $IPSFILE ]; then
        echo "ipsfile found"
        #allow input and output for ALLOWEDIP
        for IP in `cat $IPSFILE`; do
            echo "exception noticed $IP"
            sudo iptables -A INPUT  -p tcp -d $IP -m multiport --dports 80,443 -j ACCEPT
            sudo iptables -A OUTPUT  -p tcp -d $IP -m multiport --dports 80,443 -j ACCEPT
        done
    fi
    
    #allow ESTABLISHED and RELATED (important for active server communication)  
    # (the server is now added from the client automatically - this could be used as loophole to use the internet in exam mode)
    sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    sudo iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED -j ACCEPT

    #drop the rest
    sudo iptables -P INPUT DROP
    sudo iptables -P OUTPUT DROP
}


    
    
stopIPtables(){
    sudo iptables -P INPUT ACCEPT
    sudo iptables -P FORWARD ACCEPT
    sudo iptables -P OUTPUT ACCEPT
    sudo iptables -F
    sudo iptables -X
    sudo iptables -t nat -F
    sudo iptables -t nat -X
    sudo iptables -t mangle -F
    sudo iptables -t mangle -X
    sudo iptables -t raw -F 
    sudo iptables -t raw -X
}




if [ "$1" = "start" ]; then
    stopIPtables
    sleep 1
    setIPtables
elif [ "$1" = "stop" ]; then
    stopIPtables
fi

