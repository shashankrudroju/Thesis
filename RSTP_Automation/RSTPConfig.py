#!/usr/bin/env python
from GENIutils import *

def main():
    cmdList = [] # List for commands to execute on remote GENI nodes
    interfaceList = [] # List for the interface names on a remote GENI node

    # Information from credentials file needed for operation
    RSPEC = getConfigInfo("Local Utilities", "RSPEC")
    switchNamingSyntax = getConfigInfo("RSTP Utilities", "MTSName")
    endNodeNamingSyntax = getConfigInfo("RSTP Utilities", "endNodeName")
    rootBridge = getConfigInfo("RSTP Utilities", "rootNode")
    GENIDict = buildDictonary(RSPEC)

    # Configuration commands needed to install Open vSwitch on a node and various packages for both switches and end-nodes
    updatePackages = "sudo apt-get update"
    installServerDependencies = "sudo apt -y install chrony qemu-kvm libvirt-bin ubuntu-vm-builder bridge-utils"
    configTimeServer = ("sudo sed -i '/^$/d; /#/d; s/pool/#pool/g; "
                        r"$ a\\n#MTP/RSTP Research Time Server Information (questions? pjw7904@rit.edu)\n"
                        "server time.google.com iburst' /etc/chrony/chrony.conf")
    updateTimeServer = "sudo invoke-rc.d chrony restart && sudo chronyc -a 'burst 4/4' && sudo chronyc -a makestep"
    installOVS = "sudo apt -y install openvswitch-switch"
    addBridge = "sudo ovs-vsctl add-br br{0}" # br is appended with the number of the node (ex: node-1 would be "br1")
    addBridgePorts = "sudo ovs-vsctl add-port br{0} {1}" # br is appended with the number of the node and then appended with interface names (ex: eth1)
    updatePortLoggingNums = "sudo ovs-vsctl set port {0} other_config:rstp-port-num={1}"
    enableRSTP = "sudo ovs-vsctl set bridge br{0} rstp_enable=true" # bridge number is appended
    installTshark = "sudo DEBIAN_FRONTEND=noninteractive apt-get -y install tshark"
    installDependencies = "wget https://bootstrap.pypa.io/get-pip.py && sudo python get-pip.py --prefix=/usr/local/ && sudo rm get-pip.py"
    downloadScapy = "wget --trust-server-names https://github.com/secdev/scapy/archive/master.zip && unzip master"
    installScapy = "cd scapy-master && sudo python setup.py install"
    cleanupInstall = "sudo rm master && sudo rm -r scapy-master"
    updateRootBridge = "sudo ovs-vsctl set bridge br{0} other_config:rstp-priority=28672"

    # extra command needed to get things going
    getInterfaces = "ls /sys/class/net/"

    for currentRemoteNode in GENIDict:
        cmdList[:] = [] # Clear command list for the current GENI node
        nodeNumber = currentRemoteNode[-1] # The number at the end of the node's name (ex: 2 for node-2)

        if(endNodeNamingSyntax in currentRemoteNode):
            cmdList.extend([updatePackages, installTshark, installDependencies, downloadScapy, installScapy, cleanupInstall])

        elif(switchNamingSyntax in currentRemoteNode):
            # Grabbing interface names from the node (excluding eth0 and anything that isn't a normal interface [ex: loopback])
            interfaceList[:] = [] # Clear interface list for the current GENI node
            interfaceList = orchestrateRemoteCommands(currentRemoteNode, GENIDict, getInterfaces, getOutput=True).split("\n")
            interfaceList[:] = [interface for interface in interfaceList if "eth" in interface and "eth0" not in interface]

            # Adding the inital commands needed before having to check on each interface
            custom_addBridge = addBridge.format(nodeNumber)
            cmdList.extend([updatePackages, installServerDependencies, configTimeServer, updateTimeServer, installOVS, custom_addBridge])

            # Adding the commands needed to add each active interface to the Open vSwitch configuration
            for interface in interfaceList:
                custom_addBridgePorts = addBridgePorts.format(nodeNumber, interface)
                cmdList.append(custom_addBridgePorts)
                custom_updatePortLoggingNums = updatePortLoggingNums.format(interface, interface[-1])
                cmdList.append(custom_updatePortLoggingNums)

            # Adding the rest of the commands, per the order necessary
            custom_enableRSTP = enableRSTP.format(nodeNumber)
            cmdList.extend([custom_enableRSTP, installTshark, installDependencies, downloadScapy, installScapy, cleanupInstall])

            if(currentRemoteNode in rootBridge):
                custom_updateRootBridge = updateRootBridge.format(nodeNumber)
                cmdList.append(custom_updateRootBridge)

        else:
            print("ERROR: Node name isn't valid for a switch ({0}) or end node ({1})".format(switchNamingSyntax, endNodeNamingSyntax))
            break

        orchestrateRemoteCommands(currentRemoteNode, GENIDict, cmdList) # Execute the commands on the remote GENI nodes

    return None


if __name__ == "__main__":
    main()
