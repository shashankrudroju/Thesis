#!/usr/bin/env python
from GENIutils import *

def main():
    RSPEC = getConfigInfo("Local Utilities", "RSPEC")
    username = getConfigInfo("GENI Credentials", "username")
    codeDirectory = getConfigInfo("MTP Utilities", "localCodeDirectory")
    trafficGeneratorLocation = getConfigInfo("Local Utilities", "trafficGeneratorLocation")
    endnodeInfoLocation = getConfigInfo("Local Utilities", "endnodeInfoLocation")
    codeDestination = getConfigInfo("GENI Credentials", "remoteCodeDirectory")
    endNodeNamingSyntax = getConfigInfo("MTP Utilities", "endNodeName")
    GENIDict = buildDictonary(RSPEC)

    userInput = raw_input("Transfer MTP code (1) | Transfer traffic generator (2) | Start MTP Implementation (3) | populate Host Tables (4): ")

    if(userInput == "1"):
        print("\n+---------Number of Nodes: {0}--------+".format(len(GENIDict)))
        for node in GENIDict:
            if(endNodeNamingSyntax not in node):
                uploadToGENINode(node, GENIDict, codeDirectory, codeDestination)
                print("Copied the updated MTP Code to: {0}".format(node))
        print("+-------------------------------------+\n")

    elif(userInput == "2"):
        print("\n+---------Number of Nodes: {0}--------+".format(len(GENIDict)))
        for node in GENIDict:
            if(endNodeNamingSyntax in node):
                uploadToGENINode(node, GENIDict, trafficGeneratorLocation, codeDestination)
                uploadToGENINode(node, GENIDict, endnodeInfoLocation, codeDestination)
                print("Copied the updated Traffic Generator Code to: {0}".format(node))
        print("+-------------------------------------+\n")

    elif(userInput == "3"):
        timing = []
        timing.append(raw_input("* Time for Primary Root MTS to begin: "))
	timing.append(raw_input("* Time for Secondary Root MTS to begin: "))
        timing.append(raw_input("* Time for non-root MTS' to begin: "))
        remoteWorkingDirectory = os.path.join(codeDestination, os.path.basename(codeDirectory)).replace("\\", "/") # Windows POSIX change
        runMTPImplementation(GENIDict, remoteWorkingDirectory, timing)

    elif(userInput == "4"):
        sendGenericUnicastTraffic = "sudo python TrafficGenerator.py -n endnode-generic -u MTP_ucast_test -c 1"
        for node in GENIDict:
            if(endNodeNamingSyntax in node):
                orchestrateRemoteCommands(node, GENIDict, sendGenericUnicastTraffic)
                time.sleep(1)

    elif(userInput == "5"):
        sendGenericUnicastTraffic = "sudo python TrafficGenerator.py -b MTP_bcast -c 5000 -d .005"
        for node in GENIDict:
            if(node == "endnode-0"):
                orchestrateRemoteCommands(node, GENIDict, sendGenericUnicastTraffic)

    else:
        sys.exit("error, please enter 1 (upload MTP code) or 2 (Start MTP implementation on remote nodes)")


def runMTPImplementation(GENIDict, workingDirectory, timing):
    nodes = []
    cmdList = []

    endNodeNamingSyntax  = getConfigInfo("MTP Utilities", "endNodeName")
    primaryRootSwitch           = getConfigInfo("MTP Utilities", "primaryRootNode")
    secondaryRootSwitch           = getConfigInfo("MTP Utilities", "secondaryRootNode")
    trafficToSend        = getConfigInfo("MTP Utilities", "trafficToSend")
    endNodeTrafficSource = getConfigInfo("MTP Utilities", "endNodeTrafficSource")
    newestUbuntuVersion  = getConfigInfo("GENI Credentials", "OSVersion")

    primaryRootSwitchScreenName = "PrimaryMTSroot"
    secondaryRootSwitchScreenName = "SecondaryMTSroot"
    nonrootSwitchScreenName = "MTSnonroot"

    primaryRootStartTime = timing[0]
    secondaryRootStartTime = timing[1]
    nonprimaryRootStartTime = timing[2]

    for node in GENIDict:
        nodes.append(node)

    # Supporting command(s)
    enterDirectory = "cd {0};".format(workingDirectory)

    # Meshed Tree Switch startup commands
    stopMTP = "{0} sudo rm *.log && sudo rm -r *_files*".format(enterDirectory)
    removingOldLogs = "{0} sudo rm *.txt; sudo rm screenlog.0".format(enterDirectory)
    compileMTP = "{0} sudo sh install".format(enterDirectory)
    startMTP = "{0} screen -dmS {1} -L{2}bash -c 'sudo bash MTP_nano_sleep {3} {4}; exec bash'"

    # End node startup commands
    captureSetup = "{0} sudo touch results.pcap && sudo chmod 777 results.pcap".format(enterDirectory)
    captureStart = '{0} screen -dmS pktCapture sudo python TrafficGenerator.py -r {1}'.format(enterDirectory, trafficToSend)

    if(newestUbuntuVersion == "18.04"):
        screenCompatability = " -Logfile screenlog.0 "
    else:
        screenCompatability = ""

    for i in range(0, len(GENIDict)):
        currentRemoteNode = nodes[i]
        cmdList[:] = []

        if(endNodeNamingSyntax not in currentRemoteNode):
            cmdList.extend([stopMTP, removingOldLogs, compileMTP])

            if(currentRemoteNode == primaryRootSwitch):
                print("MTS Status: Primary root node")
                rootStartMTP = startMTP.format(enterDirectory, primaryRootSwitchScreenName, screenCompatability, "one", primaryRootStartTime)
                cmdList.append(rootStartMTP)
	    if(currentRemoteNode == secondaryRootSwitch):
                print("MTS Status: Secondary Root node")
                rootStartMTP1 = startMTP.format(enterDirectory, secondaryRootSwitchScreenName, screenCompatability, "two", secondaryRootStartTime)
                cmdList.append(rootStartMTP1)
            if(currentRemoteNode != secondaryRootSwitch and currentRemoteNode != primaryRootSwitch):
                print("MTS Status: nonroot node")
                nonrootStartMTP = startMTP.format(enterDirectory, nonrootSwitchScreenName, screenCompatability, "n", nonprimaryRootStartTime)
                cmdList.append(nonrootStartMTP)

        else:
            if(currentRemoteNode == endNodeTrafficSource):
                print("MTS Status: client node (sending traffic)")
            else:
                print("MTS Status: client node (receiving traffic)")
                cmdList.extend([captureSetup, captureStart])

        orchestrateRemoteCommands(currentRemoteNode, GENIDict, cmdList)

    return None


if __name__ == "__main__":
    main()
