#!/usr/bin/env python
from GENIutils import *

def main():
    cmdList = [] # List for commands to execute on remote GENI nodes
    interfaceList = [] # List for the interface names on a remote GENI node

    # Information from credentials file needed for operation
    endNodeNamingSyntax = getConfigInfo("RSTP Utilities", "endNodeName")
    username = getConfigInfo("GENI Credentials", "username")
    clientTraffic = getConfigInfo("RSTP Utilities", "trafficToSend")
    clientTrafficSource = getConfigInfo("RSTP Utilities", "endNodeTrafficSource")
    RSPEC = getConfigInfo("Local Utilities", "RSPEC")
    GENIDict = buildDictonary(RSPEC)

    # Switch startup commands
    removingOldLogs = "sudo rm eth* || sudo rm -r *_files*"
    creatingGNUScreen = "cd /users/{0}; screen -dmS pktCapRSTP".format(username)
    refreshOVSLog = "sudo rm /var/log/openvswitch/ovs-vswitchd.log && sudo ovs-appctl vlog/reopen"
    creatingCaptureFile = "touch {0}.pcap && chmod 777 {0}.pcap"
    monitorCmd = "screen -X stuff 'sudo tshark -i {0} -w {0}.pcap stp &\r'"
    startOVSLog = "sudo ovs-appctl vlog/set rstp_sm:file:dbg && sudo ovs-appctl vlog/set rstp:file:dbg"

    # Client startup commands
    clientTrafficReception = "screen -X stuff 'sudo python TrafficGenerator.py -r {0}\r'"

    # Command to get interfaces on GENI nodes running a Linux distribution
    getInterfaces = "ls /sys/class/net/"

    for currentRemoteNode in GENIDict:
        cmdList[:] = []

        if(endNodeNamingSyntax not in currentRemoteNode): # RSTP Switch
            cmdList.extend([removingOldLogs, creatingGNUScreen, refreshOVSLog])

            interfaceList[:] = [] # Clear interface list for the current GENI node
            interfaceList = orchestrateRemoteCommands(currentRemoteNode, GENIDict, getInterfaces, getOutput=True).split("\n")
            interfaceList[:] = [interface for interface in interfaceList if "eth" in interface and "eth0" not in interface]

            for interface in interfaceList:
                updatedCreatingCaptureFile = creatingCaptureFile.format(interface)
                updatedMonitorCmd = monitorCmd.format(interface)
                cmdList.append(updatedCreatingCaptureFile)
                cmdList.append(updatedMonitorCmd)

            cmdList.append(startOVSLog) # Appending command to the end of the list so that it is executed last

            orchestrateRemoteCommands(currentRemoteNode, GENIDict, cmdList) # Execute commands on remote GENI nodes

        else:
            if(currentRemoteNode != clientTrafficSource): # Client receiving traffic
                updatedCreatingCaptureFile = creatingCaptureFile.format("results")
                updatedClientTrafficReception = clientTrafficReception.format(clientTraffic)
                cmdList.extend([removingOldLogs, creatingGNUScreen, updatedCreatingCaptureFile, updatedClientTrafficReception])

                orchestrateRemoteCommands(currentRemoteNode, GENIDict, cmdList) # Execute commands on remote GENI nodes

    return None


if __name__ == "__main__":
    main()
