#!/usr/bin/env python
from GENIutils import *

RSTPInfoList = []
interfaceList = []
cmdList = []

RSPEC = getConfigInfo("Local Utilities", "RSPEC")
endNodeNamingSyntax = getConfigInfo("RSTP Utilities", "endNodeName")
GENIDict = buildDictonary(RSPEC)

cmd = "sudo ovs-vsctl list p {} | grep rstp_status"
getInterfaces = "ls /sys/class/net/"

f = open("RSTPTopology.txt", "w+")

for currentRemoteNode in GENIDict:
    if(endNodeNamingSyntax not in currentRemoteNode):
        RSTPInfoList[:] = []
        interfaceList[:] = []

        f.write("---------------------{}---------------------\n".format(currentRemoteNode))

        interfaceList = orchestrateRemoteCommands(currentRemoteNode, GENIDict, getInterfaces, getOutput=True).split("\n")
        interfaceList[:] = [interface for interface in interfaceList if "eth" in interface and "eth0" not in interface]

        for interface in interfaceList:
            f.write("{}:\n".format(interface))

            updated_cmd = cmd.format(interface)
            output = orchestrateRemoteCommands(currentRemoteNode, GENIDict, updated_cmd, getOutput=True)

            RSTPInfoList = re.split(",|}|{", output)
            del RSTPInfoList[0]
            for line in RSTPInfoList:
                f.write("{}\n".format(line))

f.close()
