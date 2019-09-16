#!/usr/bin/env python
from GENIutils import *

def main():
    cmdList = []

    # Information from credentials file needed for operation
    RSPEC = getConfigInfo("Local Utilities", "RSPEC")
    switchNamingSyntax = getConfigInfo("MTP Utilities", "MTSName")
    endNodeNamingSyntax = getConfigInfo("MTP Utilities", "endNodeName")
    GENIDict = buildDictonary(RSPEC)

    # sudo sed -i '/^$/d; /#/d; s/pool/#pool/g; $ a\\n#MTP/RSTP Research Time Server Information (questions? pjw7904@rit.edu)\nserver time.google.com iburst' /etc/chrony/chrony.conf
    # Configuration commands needed to get a slice ready for MTP
    updatePackages = "sudo sed -i 's/http:\/\/us./http:\/\//g' /etc/apt/sources.list && sudo apt-get update" # apt vs apt-get does nothing differently for the update function
    installDependencies = "wget https://bootstrap.pypa.io/get-pip.py && sudo python get-pip.py --prefix=/usr/local/ && sudo rm get-pip.py"
    installTimeServer = "sudo apt-get -y install chrony"
    configTimeServer = ("sudo sed -i '/^$/d; /#/d; s/pool/#pool/g; "
                        r"$ a\\n#MTP/RSTP Research Time Server Information (questions? pjw7904@rit.edu)\n"
                        "server time.google.com iburst\\nserver time.google.com iburst\\nserver time.google.com iburst\\nserver time.google.com iburst' /etc/chrony/chrony.conf") # "offline" arugment removed for 18.04 compatability
    updateTimeServer = "sudo invoke-rc.d chrony restart && sudo chronyc -a 'burst 4/4' && sudo chronyc -a makestep"
    installTshark = "sudo DEBIAN_FRONTEND=noninteractive apt-get -y install tshark"
    downloadScapy = "wget --trust-server-names https://github.com/secdev/scapy/archive/master.zip && unzip master"
    installScapy = "cd scapy-master && sudo python setup.py install"
    cleanupInstall = "sudo rm master && sudo rm -r scapy-master"
    # Add stuff to transfer the traffic generator as well.... which includes the nodeinfo script to get the addresses

    # Create a list of all of the commands to run
    cmdList.extend([updatePackages, installDependencies, installTimeServer, configTimeServer, updateTimeServer, installTshark, downloadScapy, installScapy, cleanupInstall])

    for currentRemoteNode in GENIDict:
        orchestrateRemoteCommands(currentRemoteNode, GENIDict, cmdList) # Execute the commands on the remote GENI nodes

    return None


if __name__ == "__main__":
    main()
