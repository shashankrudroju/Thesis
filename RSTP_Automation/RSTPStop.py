#!/usr/bin/env python
from GENIutils import *

def main():
    RSPEC = getConfigInfo("Local Utilities", "RSPEC")
    username = getConfigInfo("GENI Credentials", "username")
    password = getConfigInfo("GENI Credentials", "password")
    endNodeNamingSyntax = getConfigInfo("RSTP Utilities", "endNodeName")
    GENIDict = buildDictonary(RSPEC)

    cmdList = []
    stoppingLog = "sudo ovs-appctl vlog/set rstp_sm:file:info && sudo ovs-appctl vlog/set rstp:file:info"
    stoppingRSTP = "screen -X quit; sudo pkill tshark"
    cmdList.extend([stoppingLog, stoppingRSTP])

    for currentRemoteNode in GENIDict:
        if(endNodeNamingSyntax not in currentRemoteNode):
            orchestrateRemoteCommands(currentRemoteNode, GENIDict, cmdList)
        else:
            orchestrateRemoteCommands(currentRemoteNode, GENIDict, stoppingRSTP)


if __name__ == "__main__":
    main()
