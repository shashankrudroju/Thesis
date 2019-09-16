#!/usr/bin/env python
from GENIutils import *
from operator import attrgetter

VIDFailureExplained = []
HATFailureExplained = []
connectedHosts = {}

def main():
    if(len(sys.argv) != 5):
        sys.exit("Incorrect Number of Arguments given (./MTPTest.py [TEST NAME][NODE][INTERFACE][ITERATIONS])")

    testName           = str(sys.argv[1])
    nodeToBreak        = str(sys.argv[2])
    interfaceToBreak   = str(sys.argv[3])
    numberOfIterations = int(sys.argv[4])

    currentIteration = 0

    username   = getConfigInfo("GENI Credentials", "username")
    clientNode = getConfigInfo("MTP Utilities", "endNodeName")

    codeDirectory          = getConfigInfo("MTP Utilities", "localCodeDirectory")
    codeDestination        = getConfigInfo("GENI Credentials", "remoteCodeDirectory")
    remoteWorkingDirectory = os.path.join(codeDestination, os.path.basename(codeDirectory)).replace("\\", "/")

    trafficGeneratorLocation = getConfigInfo("Local Utilities", "trafficGeneratorLocation")
    endnodeInfoLocation      = getConfigInfo("Local Utilities", "endnodeInfoLocation")
    trafficToSend            = getConfigInfo("MTP Utilities", "trafficToSend")
    endNodeTrafficSource     = getConfigInfo("MTP Utilities", "endNodeTrafficSource")
    endNodeTrafficDest       = getConfigInfo("MTP Utilities", "endNodeTrafficDest")

    RSPEC           = getConfigInfo("Local Utilities", "RSPEC")
    networkTopology = buildDictonary(RSPEC)

    while(currentIteration != numberOfIterations):
        currentIteration += 1

        progressBar(0, 100, "Beginning test {0}".format(currentIteration), currentIteration, bar_length=20)
        time.sleep(1)

        ##### Start the VID convergence process #####
        progressBar(0, 100, "Setting up MTP Implementation Test Environment", numberOfIterations, bar_length=20)

        testStartTime = startMTPImplementation(networkTopology, remoteWorkingDirectory, clientNode, trafficToSend, endNodeTrafficSource)
        #############################################

        progressBar(12, 100, "Waiting for Test to Begin and MT_VID Propogation", numberOfIterations, bar_length=20)
        timeNeededToBeginTest = ((testStartTime + datetime.timedelta(seconds=10)) - datetime.datetime.now()).total_seconds()
        time.sleep(timeNeededToBeginTest)

        ##### Start the HAT convergence process #####
        progressBar(15, 100, "Intoducting Hosts/Clients for Host Tables", numberOfIterations, bar_length=20)

        announceClient = "sudo python TrafficGenerator.py -n {0} -u MTP_ucast_test -c 1"

        orchestrateRemoteCommands(endNodeTrafficSource, networkTopology, announceClient.format(endNodeTrafficDest))
        time.sleep(3)
        orchestrateRemoteCommands(endNodeTrafficDest, networkTopology, announceClient.format(endNodeTrafficSource))
        time.sleep(3)

        '''
        TEST FOR JUST TWO CLIENT NODES
        for node in networkTopology:
            if(clientNode in node):
                if(node != endNodeTrafficDest and node != endNodeTrafficSource):
                    orchestrateRemoteCommands(node, networkTopology, announceClient.format(endNodeTrafficSource))
                    time.sleep(3)
        '''
        #############################################

        progressBar(20, 100, "Capturing Current Meshed Tree Topology Information", numberOfIterations, bar_length=20)
        time.sleep(3)

        ##### Collecting Meshed Tree Topology Info Before the Failure #####
        collectMTPTestOutput(remoteWorkingDirectory, networkTopology, clientNode, testName, currentIteration, "before")
        ###################################################################

        ##### Start the client sending traffic #####
        progressBar(30, 100, "Starting Traffic Generation", numberOfIterations, bar_length=20)

        if(trafficToSend == "MTP_bcast"):
            trafficCommand = "-b MTP_bcast"
        elif(trafficToSend == "MTP_ucast_test"):
            trafficCommand = "-n {0} -u MTP_ucast_test".format(endNodeTrafficDest)

        sendGenericUnicastTraffic = "screen -dmS pktSender sudo python TrafficGenerator.py {0} -c 5000".format(trafficCommand) # Getting rid of -d .005
        print(sendGenericUnicastTraffic)
        for node in networkTopology:
            if(node == endNodeTrafficSource):
                orchestrateRemoteCommands(node, networkTopology, sendGenericUnicastTraffic)
        #############################################

        time.sleep(2) # Changed from 5 to 2
        progressBar(45, 100, "Failing Interface", numberOfIterations, bar_length=20)

        ##### Fail Part of the Topology #####
        interfaceChange = ("sudo ifconfig {0} down").format(interfaceToBreak)

        if nodeToBreak in str(networkTopology):
            orchestrateRemoteCommands(nodeToBreak, networkTopology, interfaceChange)
        ######################################

        progressBar(60, 100, "Switched Topology Reconverging, Waiting for Traffic to Finish Sending", numberOfIterations, bar_length=20)
        time.sleep(68)
        progressBar(65, 100, "Capturing Current Meshed Tree Topology Information", numberOfIterations, bar_length=20)

        ##### Collecting Meshed Tree Topology Info Before the Failure #####
        collectMTPTestOutput(remoteWorkingDirectory, networkTopology, clientNode, testName, currentIteration, "after")
        ###################################################################

        progressBar(70, 100, "Tearing Down Topology", numberOfIterations, bar_length=20)

        ##### Stop the MTP Implementation #####
        stopMTP = "screen -X quit"
        endTime = datetime.datetime.now()
        print("Time logging ends: {0}".format(endTime))

        for node in networkTopology:
            orchestrateRemoteCommands(node, networkTopology, stopMTP)
        #######################################

        progressBar(80, 100, "Fixing Topology", numberOfIterations, bar_length=20)

        ##### Fix Topology #####
        interfaceChange = ("sudo ifconfig {0} up").format(interfaceToBreak)

        if nodeToBreak in str(networkTopology):
            orchestrateRemoteCommands(nodeToBreak, networkTopology, interfaceChange)
        ########################

        progressBar(85, 100, "Collecting Test Results", numberOfIterations, bar_length=20)

        ##### Collect Test Results #####
        resultsDirectory = collectMTPTestResults(testName, endNodeTrafficSource, clientNode, codeDirectory, codeDestination, networkTopology, currentIteration)
        ################################

        progressBar(90, 100, "Analyzing Test Results", numberOfIterations, bar_length=20)

        ##### Analyize test results #####
        analyzeMTPTestResults(resultsDirectory, clientNode, endTime)
        #################################

        progressBar(100, 100, "Test Complete", numberOfIterations, bar_length=20)

        VIDFailureExplained[:] = []
        HATFailureExplained[:] = []
        connectedHosts.clear()


def startMTPImplementation(networkTopology, workingDirectory, clientNode, trafficToSend, endNodeTrafficSource):
    rootSwitch = getConfigInfo("MTP Utilities", "rootNode")
    OSVersion  = getConfigInfo("GENI Credentials", "OSVersion")

    cmdList = []
    numberOfNodes = len(networkTopology)

    # Supporting command(s)
    enterDirectory = "cd {0};".format(workingDirectory)

    # Meshed Tree Switch startup commands
    stopMTP         = "{0} sudo rm mtpd.log && sudo rm -r *_files*".format(enterDirectory)
    removingOldLogs = "{0} sudo rm *.txt; sudo rm screenlog.0".format(enterDirectory)
    compileMTP      = "{0} sudo sh install".format(enterDirectory)
    startMTP        = "{0} screen -dmS {1} -L{2}bash -c 'sudo bash MTP_nano_sleep {3} {4}; exec bash'"

    # End node startup commands
    captureSetup = "{0} sudo rm results.pcap; sudo touch results.pcap && sudo chmod 777 results.pcap".format(enterDirectory)
    captureStart = '{0} screen -dmS pktCapture sudo python TrafficGenerator.py -r {1}'.format(enterDirectory, trafficToSend)

    if(OSVersion == "18.04"):
        screenCompatability = " -Logfile screenlog.0 "
    else:
        screenCompatability = ""

    currentTime = datetime.datetime.now() # To or see format: currentTime.strftime("%H:%M:%S")
    timeToStartRootNode = currentTime + datetime.timedelta(seconds=(numberOfNodes * 5))
    timeToStartNonRootNodes = timeToStartRootNode + datetime.timedelta(seconds=5)

    for node in networkTopology:
        cmdList[:] = []

        if(clientNode not in node):
            cmdList.extend([stopMTP, removingOldLogs, compileMTP])

            if(node == rootSwitch):
                print("MTS Status: root node")
                rootStartMTP = startMTP.format(enterDirectory, "MTSroot", screenCompatability, "y", timeToStartRootNode.strftime("%H:%M:%S"))
                cmdList.append(rootStartMTP)

            else:
                print("MTS Status: nonroot node")
                nonrootStartMTP = startMTP.format(enterDirectory, "MTSnonroot", screenCompatability, "n", timeToStartNonRootNodes.strftime("%H:%M:%S"))
                cmdList.append(nonrootStartMTP)

        else:
            if(node == endNodeTrafficSource):
                print("MTS Status: client node (sending traffic)")

            else:
                print("MTS Status: client node (receiving traffic)")
                cmdList.extend([captureSetup, captureStart])

        orchestrateRemoteCommands(node, networkTopology, cmdList)

    return timeToStartNonRootNodes


def collectMTPTestOutput(remoteWorkingDirectory, networkTopology, clientNode, testName, currentIteration, description):
    runOutputScript = "cd {} && sudo python MTPOutputAnalyzer.py screenlog.0".format(remoteWorkingDirectory)
    consoleOutputFile = "MTP_Test_{0}-{1}_output_{2}.txt".format(testName, currentIteration, description)
    collectionFile = open(consoleOutputFile, "w+")

    for node in networkTopology:
        if(clientNode not in node):
            fileData = orchestrateRemoteCommands(node, networkTopology, runOutputScript, getOutput = True)
            collectionFile.write(node + ":\n")
            collectionFile.write(str(fileData))
            print("Retrieved MTP convergence data from {}".format(node))

    collectionFile.close()

    return


def collectMTPTestResults(testName, endNodeTrafficSource, clientNode, codeDirectory, codeDestination, networkTopology, currentIteration):
    cmdList = []

    remoteWorkingDirectory = os.path.join(codeDestination, os.path.basename(codeDirectory)).replace("\\", "/")

    # Create a new directory in which the test results will be stored (MTP_Test is added at the end of the directory name for consistency)
    fullTestName = "MTP_Test_{0}-{1}".format(testName, currentIteration)
    newDir = "./MTP_Test_{0}-{1}".format(testName, currentIteration)
    os.makedirs(newDir)

    # Support commands for other commands
    enterDirectory = "cd {0} &&".format(remoteWorkingDirectory)

    # Commands to run for a Meshed Tree Switch
    copyLogFile = "{0} cp mtpd.log {1}"
    createDir =  "{0} mkdir {1}_files"
    moveLogFile = "{0} mv {1} {2}_files/"
    zipFiles =  "{0} zip -r {1}_files.zip {1}_files/"

    # Commands to run for a client node
    createTrafficLog = "sudo python TrafficGenerator.py -a results.pcap"
    copyTrafficLog = "cp trafficResult.txt {0}"
    copyPacketLog = "cp results.pcap {0}"
    moveClientFiles = "mv -t {0}_files/ {1}"


    for currentRemoteNode in networkTopology:
        cmdList[:] = []
        needToCollectData = False

        if(clientNode not in currentRemoteNode):
            logFileName = "{0}.log".format(currentRemoteNode)
            updated_copyLogFile = copyLogFile.format(enterDirectory, logFileName)
            updated_createDir = createDir.format(enterDirectory, currentRemoteNode)
            updated_moveLogFile = moveLogFile.format(enterDirectory, logFileName, currentRemoteNode)
            updated_zipFiles = zipFiles.format(enterDirectory, currentRemoteNode)

            cmdList.extend([updated_copyLogFile, updated_createDir, updated_moveLogFile, updated_zipFiles])
            trafficFileLocation = str(os.path.join(remoteWorkingDirectory, currentRemoteNode + "_files.zip").replace("\\", "/"))
            needToCollectData = True

        elif(clientNode in currentRemoteNode and currentRemoteNode != endNodeTrafficSource):
            logFileName = "{0}_traffic.log".format(currentRemoteNode)
            packetFileName = "{0}_capture.pcap".format(currentRemoteNode)
            updated_copyTrafficLog = copyTrafficLog.format(logFileName)
            updated_copyPacketLog = copyPacketLog.format(packetFileName)
            updated_createDir = createDir.format("", currentRemoteNode)
            #updated_moveLogFile = moveLogFile.format("", logFileName, currentRemoteNode)
            updated_moveClientFiles = moveClientFiles.format(currentRemoteNode, "{0} {1}".format(logFileName, packetFileName))
            updated_zipFiles = zipFiles.format("", currentRemoteNode)

            cmdList.extend([createTrafficLog, updated_copyTrafficLog, updated_copyPacketLog, updated_createDir, updated_moveClientFiles, updated_zipFiles])
            trafficFileLocation = str(os.path.join(currentRemoteNode + "_files.zip").replace("\\", "/"))
            needToCollectData = True

        if(needToCollectData):
            localLocation = str(os.path.join(newDir, currentRemoteNode + "_files.zip").replace("\\", "/"))
            open(localLocation, 'a').close()

            orchestrateRemoteCommands(currentRemoteNode, networkTopology, cmdList) # Create the zip file
            getGENIFile(currentRemoteNode, networkTopology, trafficFileLocation, localLocation) # Grab the zip file


    # Extract everything in the newly-created directory and discard the zip files
    for root, dirs, files in os.walk(newDir):
        for filename in files:
            if(filename.endswith(".zip")):
                absFileLocation = os.path.join(os.path.abspath(newDir).replace("\\", "/"), filename).replace("\\", "/")
                unzip = zipfile.ZipFile(absFileLocation)
                unzip.extractall(newDir)
                unzip.close()
                os.remove(absFileLocation)

    return fullTestName


def analyzeMTPTestResults(resultsDirectory, clientNode, endTime):
    dirList = []
    VIDFailureConvergenceTimes = []
    HATFailureConvergenceTimes = []
    logEntries = defaultdict(list)
    clientTrafficEntries = {}

    fileName = "{0}.csv".format(resultsDirectory)
    outputFile = open(fileName, "w+")

    timeStampFormat = "%Y-%m-%d %H:%M:%S.%f"
    timeTestEnded = datetime.datetime.strptime(str(endTime), timeStampFormat)

    for root, dirs, files in os.walk(resultsDirectory):
        for name in dirs:
            dirList.append(os.path.join(root, name).replace("\\", "/"))

    for eachRoot in dirList:
        nodeName = re.search('(?<=/)(.*)(?=_files)', eachRoot).group(0)

        if(clientNode not in nodeName):
            for root, dirs, files in os.walk(eachRoot):
                for file in files:
                    if(".log" in file):
                        filterMTPLog(os.path.join(root, file).replace("\\", "/"), nodeName, logEntries, timeTestEnded)
        else:
            for root, dirs, files in os.walk(eachRoot):
                for file in files:
                    if(".log" in file):
                        filterClientLog(os.path.join(root, file).replace("\\", "/"), nodeName, clientTrafficEntries)

    outputLogInfo(outputFile, logEntries)

    VIDFailureConvergenceTimes = analyzeVIDFailures(logEntries)
    HATFailureConvergenceTimes = analyzeHATFailures(logEntries)
    outputConvergenceInfo(outputFile, VIDFailureConvergenceTimes, HATFailureConvergenceTimes)

    outputClientInfo(outputFile, clientTrafficEntries)
    outputOverviewInfo(outputFile)

    outputFile.close()

    return


def outputLogInfo(outputFile, logEntries):
    testSortList = []
    timeStampFormat = "%Y-%m-%d %H:%M:%S.%f"
    outputHeader = "Time Stamp,Log Source,Interface,Message Type,Action\n"
    outputFormat = "{0},{1},{2},{3},{4}"

    outputFile.write("==========LINK FAILURE INFO==========\n\n-LINK FAILURE LOGS-\n" + outputHeader)

    for messageType in logEntries:
        for entry in logEntries[messageType]:
            addMsgType = entry + "|{0}".format(messageType)
            entrySections = addMsgType.split("|")
            formattedEntry = outputFormat.format(entrySections[0], entrySections[5], entrySections[1], entrySections[6], entrySections[4])
            testSortList.append(formattedEntry + "\n")

    sortedList = sorted(testSortList, key=lambda line: datetime.datetime.strptime(line.split(",")[0][:-3], timeStampFormat))
    for item in sortedList:
        outputFile.write(item)

    return


def outputConvergenceInfo(outputFile, VIDFailureConvergenceTimes, HATFailureConvergenceTimes):
    linkFailureResultOutputHeader = "Failure,Interface Failure Time,Final Converged Stamp,Result"

    outputFile.write("\n-PVID TREE LINK FAILURE RESULTS-\n")
    outputFile.write(linkFailureResultOutputHeader + "\n")
    for individualInterfaceFailure in VIDFailureConvergenceTimes:
        convergenceTime =  individualInterfaceFailure[3] - individualInterfaceFailure[2]
        updatedStart = "'{0}'".format(individualInterfaceFailure[2])
        updatedEnd = "'{0}'".format(individualInterfaceFailure[3])
        outputFile.write("{0} failing on {1},{2},{3},{4} seconds\n".format(individualInterfaceFailure[1], individualInterfaceFailure[0], updatedStart, updatedEnd, convergenceTime.total_seconds()))

    outputFile.write("\n-HAT LINK FAILURE RESULTS-\n")
    outputFile.write(linkFailureResultOutputHeader + "\n")
    convergenceTime =  HATFailureConvergenceTimes[3] - HATFailureConvergenceTimes[2]
    updatedStart = "'{0}'".format(HATFailureConvergenceTimes[2])
    updatedEnd = "'{0}'".format(HATFailureConvergenceTimes[3])
    outputFile.write("{0} failing on {1},{2},{3},{4} seconds\n".format(HATFailureConvergenceTimes[1], HATFailureConvergenceTimes[0], updatedStart, updatedEnd, convergenceTime.total_seconds()))

    return


def outputClientInfo(outputFile, clientTrafficEntries):
    outputFile.write("\n-CLIENT TRAFFIC OVERVIEW-\nClient,Result\n")
    for message in clientTrafficEntries:
        outputFile.write("{0},{1}".format(message, clientTrafficEntries[message]))

    return


def outputOverviewInfo(outputFile):
    outputFile.write("\n-PVID TREE FAILURE OVERVIEW-\nMessage\n")
    for message in VIDFailureExplained:
        outputFile.write(message + "\n")

    outputFile.write("\n-HAT FAILURE OVERVIEW-\nMessage\n")
    for message in HATFailureExplained:
        outputFile.write(message + "\n")

    return


def filterMTPLog(logFile, nodeName, logCollection, timeTestEnded):
    timeStampFormat = "%Y-%m-%d %H:%M:%S.%f"
    VIDFailure  = "7"
    linkFailure = "8"
    HATUpdate   = "9"
    HATFailure  = "10"

    with open(logFile, "r") as readFile:
        for line in readFile:
            updatedLine = line.rstrip() + "|{}".format(nodeName)
            logSections = updatedLine.split("|")

            logTimeStamp   = datetime.datetime.strptime(logSections[0][:-3], timeStampFormat)
            logDirection   = logSections[2]
            logType        = logSections[3]
            logDescription = logSections[4]

            checkLogTime = timeTestEnded - logTimeStamp
            validLog = "-1 day" not in str(checkLogTime)

            if(validLog):
                if(logType == linkFailure):
                    logCollection["Link Failure"].append(updatedLine)

                elif(logType == VIDFailure):
                    if("Deleted From CPVID Table" in logDescription):
                        logCollection["CPVID Deletion"].append(updatedLine)

                    elif("Deleted From VID Table" in logDescription):
                        logCollection["VID Deletion"].append(updatedLine)

                    elif("Failed From VID Table [1MH]" in logDescription):
                        logCollection["Missed Hello's VID Failure"].append(updatedLine)

                    elif("Failed From CPVID Table [1MH]" in logDescription):
                        logCollection["Missed Hello's CPVID Failure"].append(updatedLine)

                    elif("Failed From VID Table [int]" in logDescription):
                        logCollection["Interface VID Failure"].append(updatedLine)

                    elif("Failed From CPVID Table [int]" in logDescription):
                        logCollection["Interface CPVID Failure"].append(updatedLine)

                elif(logType == HATFailure):
                    if("Failed From Main Host Table [int" in logDescription):
                        logCollection["Interface HAT Main Failure"].append(updatedLine)

                    elif("Failed From Main Host Table [1MH" in logDescription):
                        logCollection["Missed Hello's HAT Main Failure"].append(updatedLine)

                    elif("Deleted from Main Host Table" in logDescription):
                        logCollection["HAT Main Deletion"].append(updatedLine)

                elif(logType == HATUpdate):
                    if("updated main path cost to" in logDescription):
                        logCollection["HAT Update"].append(updatedLine)

                    elif("Added to Main Host Table [1] {1}" in logDescription):
                        connectedHosts[nodeName] = logDescription.split(" ")[0]

    return logCollection

def filterClientLog(logFile, nodeName, logCollection):
    with open(logFile, "r") as readFile:
        logCollection[nodeName] = readFile.read()

    return logCollection


def extractLogEntryInfo(logEntry):
    timeStampFormat = "%Y-%m-%d %H:%M:%S.%f"

    currentEntry = logEntry.split("|")
    entryTimeStamp = datetime.datetime.strptime(currentEntry[0][:-3], timeStampFormat)
    entryInterface = currentEntry[1]
    entryMessage = currentEntry[4]
    entryNode = currentEntry[5]

    return entryTimeStamp, entryInterface, entryMessage, entryNode


def analyzeHATFailures(logEntries):
    failureTimeStamps = []
    singleFailureInfo = []
    allFailuresInfo = []
    combinedList = []
    timeStampFormat = "%Y-%m-%d %H:%M:%S.%f"
    limit = datetime.timedelta(hours=0, minutes=0, seconds=8, microseconds=000000)

    for linkFailures in logEntries["Link Failure"]: # For each interface that was failed, we need to determine what happened in the topology
        singleFailureInfo[:] = []
        linkFailureTime, failedInterface, failureMsg, nodeWithFailure = extractLogEntryInfo(linkFailures)
        HATFailureExplained.append("{0} had an interface failure on {1}".format(nodeWithFailure, failedInterface))

        failureTimeStamps.append(linkFailureTime)

        failedHostEntries = checkInterfaceFailures(logEntries["Interface HAT Main Failure"], linkFailureTime, failedInterface, nodeWithFailure, isHATCheck = True)

        if(failedHostEntries):
            failureTimeStamps += failedHostEntries.values()

    combinedList += logEntries["Missed Hello's HAT Main Failure"] + logEntries["HAT Main Deletion"] + logEntries["HAT Update"]

    sortedList = sorted(combinedList, key=lambda line: datetime.datetime.strptime(line.split("|")[0][:-3], timeStampFormat))
    for item in sortedList[:]:
        timediff = datetime.datetime.strptime(item.split("|")[0][:-3], timeStampFormat) - failureTimeStamps[0]

        if(timediff > limit):
            sortedList.remove(item)

    for item in sortedList:
        logTime, logInterface, logMsg, logNode = extractLogEntryInfo(item)

        failureTimeStamps.append(logTime)

        if("Deleted from Main Host Table" in logMsg):
            HATFailureExplained.append("{2} deleted {0} from interface {1}".format(logMsg.split(" ")[0], logInterface, logNode))

        elif("Failed From Main Host Table [1MH" in logMsg):
            HATFailureExplained.append("{2} lost the primary host entry for {0} from interface {1} not receiving Hello messages".format(logMsg.split(" ")[0], logInterface, logNode))

        elif("updated" in logMsg):
            HATFailureExplained.append("{2} updated the cost for host {0} for interface {1}".format(logMsg.split(" ")[0], logInterface, logNode))

        else:
            HATFailureExplained.append("unknown log: {0}".format(logMsg))

    failureTimeStamps.sort()
    singleFailureInfo.extend([nodeWithFailure, failedInterface, linkFailureTime, failureTimeStamps[-1]])

    return singleFailureInfo


def analyzeVIDFailures(logEntries):
    failureTimeStamps = []
    singleFailureInfo = []
    allFailuresInfo = []
    timeStampFormat = "%Y-%m-%d %H:%M:%S.%f"

    for linkFailures in logEntries["Link Failure"]: # For each interface that was failed, we need to determine what happened in the topology
        singleFailureInfo[:] = []

        currentLinkFailure = linkFailures.split("|")
        linkFailureTime = datetime.datetime.strptime(currentLinkFailure[0][:-3], timeStampFormat)
        failedInterface = currentLinkFailure[1]
        nodeWithFailure = currentLinkFailure[5]
        VIDFailureExplained.append("{0} had an interface failure on {1}".format(nodeWithFailure, failedInterface))

        failureTimeStamps.append(linkFailureTime)

        # Due to the occurance of an interface failure or a node failure, find the PVID or CPVIDs that were lost as a result
        failedPVID, PVIDFailureTime = checkInterfaceFailures(logEntries["Interface VID Failure"], linkFailureTime, failedInterface, nodeWithFailure)
        failedCPVID, CPVIDFailureTime = checkInterfaceFailures(logEntries["Interface CPVID Failure"], linkFailureTime, failedInterface, nodeWithFailure)

        if(failedPVID):
            failureTimeStamps.append(PVIDFailureTime)

        if(failedCPVID):
            failureTimeStamps.append(CPVIDFailureTime)

        # On the other side of an interface failure or a node failure, find the VIDs CPVIDs that were lost as a result
        failedHellosPVID, PVIDHelloFailureTime = checkVIDHelloFailures(logEntries["Missed Hello's VID Failure"], linkFailureTime, failedPVID, failedCPVID = failedCPVID)
        failedHellosCPVID, CPVIDHelloFailureTime = checkVIDHelloFailures(logEntries["Missed Hello's CPVID Failure"], linkFailureTime, failedPVID, failedCPVID = failedCPVID)

        if(failedHellosPVID):
            failureTimeStamps.append(PVIDHelloFailureTime)

        if(failedHellosCPVID):
            failureTimeStamps.append(CPVIDHelloFailureTime)

        # When a link failure occurs, MTP Advertisment Deleltion messages will be sent to nearest neighbors, and those VIDs will be deleted
        timeStampsVID = checkVIDDeletions(logEntries["VID Deletion"], linkFailureTime, failedPVID, failedHellosPVID)
        timeStampsCPVID = checkCPVIDDeletions(logEntries["CPVID Deletion"], linkFailureTime, failedPVID, failedHellosPVID)

        if(timeStampsVID):
            failureTimeStamps += timeStampsVID

        if(timeStampsCPVID):
            failureTimeStamps += timeStampsCPVID

        failureTimeStamps.sort()
        singleFailureInfo.extend([nodeWithFailure, failedInterface, linkFailureTime, failureTimeStamps[-1]])
        allFailuresInfo.append(singleFailureInfo)

    return allFailuresInfo


def checkInterfaceFailures(logCategory, linkFailureTime, failedInterface, nodeWithFailure, isHATCheck = False):
    timeStampFormat = "%Y-%m-%d %H:%M:%S.%f"

    if(isHATCheck):
        failedEntry = {}
    else:
        failedEntry = ""
        entryFailureTime = ""

    for entry in logCategory:
        currentEntry = entry.split("|")
        entryTimeStamp = datetime.datetime.strptime(currentEntry[0][:-3], timeStampFormat)
        entryInterface = currentEntry[1]
        entryMessage = currentEntry[4]
        entryNode = currentEntry[5]

        timeStampDifference = entryTimeStamp - linkFailureTime

        # If the VID/CPVID has failed due to the carelessness of a failed interface (2/4 failed VID scenarios)
        if(nodeWithFailure == entryNode and failedInterface == entryInterface and "-1 day" not in str(timeStampDifference)):
            messageContent = entryMessage.split(" ")

            if("{1}" in messageContent[1]):
                failedEntry = messageContent[0]
                entryFailureTime = entryTimeStamp
                VIDFailureExplained.append("{2} lost PVID {0} from interface {1} failing".format(failedEntry, failedInterface, nodeWithFailure))

            elif("CPVID" in messageContent[3]):
                failedEntry = messageContent[0]
                entryFailureTime = entryTimeStamp
                VIDFailureExplained.append("{2} lost CPVID {0} from interface {1} failing".format(failedEntry, failedInterface, nodeWithFailure))

            elif("Main Host Table" in entryMessage):
                failedEntry[messageContent[0]] = entryTimeStamp
                HATFailureExplained.append("{2} lost the primary host entry for {0} from interface {1} failing".format(messageContent[0], failedInterface, nodeWithFailure))

    if(isHATCheck):
        return failedEntry
    else:
        return failedEntry, entryFailureTime


def checkVIDHelloFailures(logCategory, linkFailureTime, failedPrimaryEntry, failedCPVID = None, isHATCheck = False):
    timeStampFormat = "%Y-%m-%d %H:%M:%S.%f"
    failedVID = ""
    VIDfailureTime = ""

    for entry in logCategory:
        currentEntry = entry.split("|")
        entryTimeStamp = datetime.datetime.strptime(currentEntry[0][:-3], timeStampFormat)
        entryInterface = currentEntry[1]
        entryMessage = currentEntry[4]
        entryNode = currentEntry[5]

        timeStampDifference = entryTimeStamp - linkFailureTime
        validFailureLog = "-1 day" not in str(timeStampDifference)

        if(not isHATCheck):
            if(failedCPVID and validFailureLog):
                messageContent = entryMessage.split(" ")
                if("{1}" in messageContent[1] and failedCPVID == messageContent[0]):
                    failedVID = messageContent[0]
                    VIDfailureTime = entryTimeStamp
                    VIDFailureExplained.append("{2} lost PVID {0} from interface {1} not receiving Hello messages".format(failedVID, entryInterface, entryNode))

            if(failedPrimaryEntry and validFailureLog):
                messageContent = entryMessage.split(" ")
                if(failedPrimaryEntry == messageContent[0]):
                    failedVID = messageContent[0]
                    VIDfailureTime = entryTimeStamp
                    VIDFailureExplained.append("{2} lost CPVID {0} from interface {1} not receiving Hello messages".format(failedVID, entryInterface, entryNode))

    return failedVID, VIDfailureTime


def checkVIDDeletions(logCategory, linkFailureTime, failedPVID, failedHellosPVID):
    timeStampFormat = "%Y-%m-%d %H:%M:%S.%f"
    farthestTimeStamp = []

    for entry in logCategory:
        currentEntry = entry.split("|")
        entryTimeStamp = datetime.datetime.strptime(currentEntry[0][:-3], timeStampFormat)
        entryInterface = currentEntry[1]
        entryMessage = currentEntry[4]
        entryNode = currentEntry[5]

        timeStampDifference = entryTimeStamp - linkFailureTime
        validFailureLog = "-1 day" not in str(timeStampDifference)

        messageContent = entryMessage.split(" ")
        if("{1}" in messageContent[1]):
            if(failedPVID):
                formattedFailedPVID = "[{0}]".format(failedPVID)
                if(messageContent[6] == formattedFailedPVID):
                    farthestTimeStamp.append(entryTimeStamp)
                    VIDFailureExplained.append("{2} deleted PVID {0} from interface {1} because VID {3} failed".format(messageContent[0], entryInterface, entryNode, failedPVID))

            if(failedHellosPVID):
                formattedFailedHellosPVID = "[{0}]".format(failedHellosPVID)
                if(messageContent[6] == formattedFailedHellosPVID):
                    farthestTimeStamp.append(entryTimeStamp)
                    VIDFailureExplained.append("{2} deleted PVID {0} from interface {1} because VID {3} failed".format(messageContent[0], entryInterface, entryNode, failedHellosPVID))

    return farthestTimeStamp


def checkCPVIDDeletions(logCategory, linkFailureTime, failedPVID, failedHellosPVID):
    timeStampFormat = "%Y-%m-%d %H:%M:%S.%f"
    farthestTimeStamp = []

    for entry in logCategory:
        currentEntry = entry.split("|")
        entryTimeStamp = datetime.datetime.strptime(currentEntry[0][:-3], timeStampFormat)
        entryInterface = currentEntry[1]
        entryMessage = currentEntry[4]
        entryNode = currentEntry[5]

        timeStampDifference = entryTimeStamp - linkFailureTime
        validFailureLog = "-1 day" not in str(timeStampDifference)

        messageContent = entryMessage.split(" ")
        if(failedPVID):
            formattedFailedPVID = "[{0}]".format(failedPVID)
            if(messageContent[5] == formattedFailedPVID):
                farthestTimeStamp.append(entryTimeStamp)
                VIDFailureExplained.append("{2} deleted CPVID {0} from interface {1} because VID {3} failed".format(messageContent[0], entryInterface, entryNode, failedPVID))

        if(failedHellosPVID):
            formattedFailedHellosPVID = "[{0}]".format(failedHellosPVID)
            if(messageContent[5] == formattedFailedHellosPVID):
                farthestTimeStamp.append(entryTimeStamp)
                VIDFailureExplained.append("{2} deleted CPVID {0} from interface {1} because VID {3} failed".format(messageContent[0], entryInterface, entryNode, failedHellosPVID))

    return farthestTimeStamp


def progressBar(value, endvalue, message, iteration, bar_length=20):
        percent = float(value) / endvalue
        arrow = '-' * int(round(percent * bar_length)-1) + '>'
        spaces = ' ' * (bar_length - len(arrow))

        print("\r| MTP Test Iteration ({2}): [{0}] {1} % | Status: {3}".format(arrow + spaces, int(round(percent * 100)), iteration, message))


if __name__ == "__main__":
    main()
