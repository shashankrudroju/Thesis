#!/usr/bin/env python
from GENIutils import *

def main():
    if(len(sys.argv) != 4):
        sys.exit("Incorrect Number of Arguments given (./RSTPBreakLink.py [UP/DOWN][NODE][INTERFACE])")

    interfaceAction = str(sys.argv[1])
    nodeToBreak = str(sys.argv[2])
    intToBreak = str(sys.argv[3])

    if(interfaceAction != "up" and interfaceAction != "down"):
        sys.exit("First argument needs to be either up or down")

    RSPEC = getConfigInfo("Local Utilities", "RSPEC")
    username = getConfigInfo("GENI Credentials", "username")
    password = getConfigInfo("GENI Credentials", "password")
    GENIDict = buildDictonary(RSPEC)

    interfaceChange = ("sudo ifconfig {0} {1}").format(intToBreak, interfaceAction)

    if nodeToBreak in str(GENIDict):
        orchestrateRemoteCommands(nodeToBreak, GENIDict, interfaceChange)

    else:
        sys.exit("Node not found, please try again")

    return None


if __name__ == "__main__":
    main()
