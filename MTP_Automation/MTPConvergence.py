#!/usr/bin/env python
from GENIutils import *
from operator import attrgetter

VIDFailureExplained = []
HATFailureExplained = []

def main():
    userInput = raw_input("Collection (1) | Convergence (2): ")

    if(userInput == "1"):
        collectData()

    elif(userInput == "2"):
        getConvergence()


def collectData():
    userInput = raw_input("Test name: ")
    testName = str(userInput)
    cmdList = []

    # Information from credentials file needed for operation
    clientTrafficSource = getConfigInfo("MTP Utilities", "endNodeTrafficSource")
    endNodeNamingSyntax = getConfigInfo("MTP Utilities", "endNodeName")
    codeDirectory = getConfigInfo("MTP Utilities", "localCodeDirectory")
    codeDestination = getConfigInfo("GENI Credentials", "remoteCodeDirectory")
    RSPEC = getConfigInfo("Local Utilities", "RSPEC")
    GENIDict = buildDictonary(RSPEC)
    remoteWorkingDirectory = os.path.join(codeDestination, os.path.basename(codeDirectory)).replace("\\", "/")

    # Create a new directory in which the test results will be stored (MTP_Test is added at the end of the directory name for consistency)
    newDir = "./{}".format(testName)
    os.makedirs(newDir)

    # Support commands for other commands
    enterDirectory = "cd {0} &&".format(remoteWorkingDirectory)

    # Commands to run for a Meshed Tree Switch
    copyLogFile = "{0} cp mtpd_1.log {1} && cp mtpd_2.log {2}"
    createDir =  "{0} mkdir {1}_files"
    moveLogFile = "{0} mv *.log {1}_files/"
    zipFiles =  "{0} zip -r {1}_files.zip {1}_files/"

    # Commands to run for a client node
    createTrafficLog = "sudo python TrafficGenerator.py -a results.pcap"
    copyTrafficLog = "cp trafficResult.txt {1}"

    for currentRemoteNode in GENIDict:
        cmdList[:] = []
        needToCollectData = False

        if(endNodeNamingSyntax not in currentRemoteNode):
            logFileName = "{0}.log".format(currentRemoteNode)
            removeMtpdFiles = "{0} sudo rm mtpd*.log".format(enterDirectory)
            logFileName_tree2 = "{0}_tree2.log".format(currentRemoteNode)
            updated_copyLogFile = copyLogFile.format(enterDirectory, logFileName, logFileName_tree2)
            updated_createDir = createDir.format(enterDirectory, currentRemoteNode)
            updated_moveLogFile = moveLogFile.format(enterDirectory, currentRemoteNode)
            updated_zipFiles = zipFiles.format(enterDirectory, currentRemoteNode)

            cmdList.extend([updated_copyLogFile, removeMtpdFiles, updated_createDir, updated_moveLogFile, updated_zipFiles])
            trafficFileLocation = str(os.path.join(remoteWorkingDirectory, currentRemoteNode + "_files.zip").replace("\\", "/"))
            needToCollectData = True

        elif(endNodeNamingSyntax in currentRemoteNode and currentRemoteNode != clientTrafficSource):
            logFileName = "{0}_traffic.log".format(currentRemoteNode)
            updated_copyTrafficLog = copyTrafficLog.format(enterDirectory, logFileName)
            updated_createDir = createDir.format("", currentRemoteNode)
            updated_moveLogFile = moveLogFile.format("", logFileName, currentRemoteNode)
            updated_zipFiles = zipFiles.format("", currentRemoteNode)

            cmdList.extend([createTrafficLog, updated_copyTrafficLog, updated_createDir, updated_moveLogFile, updated_zipFiles])
            trafficFileLocation = str(os.path.join(currentRemoteNode + "_files.zip").replace("\\", "/"))
            needToCollectData = True

        if(needToCollectData):
            localLocation = str(os.path.join(newDir, currentRemoteNode + "_files.zip").replace("\\", "/"))
            open(localLocation, 'a').close()

            orchestrateRemoteCommands(currentRemoteNode, GENIDict, cmdList) # Create the zip file
            getGENIFile(currentRemoteNode, GENIDict, trafficFileLocation, localLocation) # Grab the zip file


    # Extract everything in the newly-created directory and discard the zip files
    for root, dirs, files in os.walk(newDir):
        for filename in files:
            if(filename.endswith(".zip")):
                absFileLocation = os.path.join(os.path.abspath(newDir).replace("\\", "/"), filename).replace("\\", "/")
                unzip = zipfile.ZipFile(absFileLocation)
                unzip.extractall(newDir)
                unzip.close()
                os.remove(absFileLocation)

    return


def getConvergence():
    dirList = []
    VIDFailureConvergenceTimes = []
    HATFailureConvergenceTimes = []
    logEntries = defaultdict(list)
    clientTrafficEntries = {}

    endNodeNamingSyntax = getConfigInfo("MTP Utilities", "endNodeName")

    userInput = raw_input("Test name: ")
    testDir = str(userInput)
    fileName = "{0}.csv".format(testDir)
    outputFile = open(fileName, "w+")

    for root, dirs, files in os.walk(testDir):
        for name in dirs:
            dirList.append(os.path.join(root, name).replace("\\", "/"))

    for eachRoot in dirList:
        nodeName = re.search('(?<=/)(.*)(?=_files)', eachRoot).group(0)

        if(endNodeNamingSyntax not in nodeName):
            for root, dirs, files in os.walk(eachRoot):
                for file in files:
                    if(".log" in file):
                        filterMTPLog(os.path.join(root, file).replace("\\", "/"), nodeName, logEntries)
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
    failureWritten = False

    outputFile.write("==========LINK FAILURE INFO==========\n\n-LINK FAILURE LOGS-\n" + outputHeader)

    for messageType in logEntries:
        for entry in logEntries[messageType]:
            addMsgType = entry + "|{0}".format(messageType)
            entrySections = addMsgType.split("|")
            formattedEntry = outputFormat.format(entrySections[0], entrySections[5], entrySections[1], entrySections[6], entrySections[4])
            testSortList.append(formattedEntry + "\n")

    sortedList = sorted(testSortList, key=lambda line: datetime.datetime.strptime(line.split(",")[0][:-3], timeStampFormat))

    for item in sortedList:
        if("Link Failure" in item):
            failureWritten = True

        if(failureWritten):
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


def filterMTPLog(logFile, nodeName, logCollection):
    VIDFailure  = "7"
    linkFailure = "8"
    HATUpdate   = "9"
    HATFailure  = "10"

    with open(logFile, "r") as readFile:
        for line in readFile:
            updatedLine = line.rstrip() + "|{}".format(nodeName)
            logSections = updatedLine.split("|")

            logDirection   = logSections[2]
            logType        = logSections[3]
            logDescription = logSections[4]

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

                elif("Upgraded to PVID" in logDescription):
                    logCollection["New PVID"].append(updatedLine)

            elif(logType == "3" and "Added to CPVID Table" in logDescription):
                logCollection["CPVID Addition"].append(updatedLine)

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
        print(item)
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

        # When a link failure occurs, MTP Advertisment Deletion messages will be sent to nearest neighbors, and those VIDs will be deleted
        timeStampsVID = checkVIDDeletions(logEntries["VID Deletion"], linkFailureTime, failedPVID, failedHellosPVID)
        timeStampsCPVID = checkCPVIDDeletions(logEntries["CPVID Deletion"], linkFailureTime, failedPVID, failedHellosPVID)

        if(timeStampsVID):
            failureTimeStamps += timeStampsVID

        if(timeStampsCPVID):
            failureTimeStamps += timeStampsCPVID

        VIDAdditionTimestamps = checkVIDAdditions(logEntries["New PVID"], logEntries["CPVID Addition"], linkFailureTime, failedPVID, failedHellosPVID)

        if(VIDAdditionTimestamps):
            failureTimeStamps += VIDAdditionTimestamps

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


def checkVIDAdditions(newPVIDs, newCPVIDs, linkFailureTime, failedPVID, failedHellosPVID):
    timeStampFormat = "%Y-%m-%d %H:%M:%S.%f"
    farthestTimeStamp = []
    upgradedVIDs = []

    for entry in newPVIDs:
        entryTimeStamp, entryInterface, entryMessage, entryNode = extractLogEntryInfo(entry)

        timeStampDifference = entryTimeStamp - linkFailureTime
        validFailureLog = "-1 day" not in str(timeStampDifference)

        messageContent = entryMessage.split(" ")
        if(failedPVID):
            formattedFailedPVID = "[{0}]".format(failedPVID)
            if(messageContent[4] == formattedFailedPVID):
                farthestTimeStamp.append(entryTimeStamp)
                upgradedVIDs.append((messageContent[0], entryNode))
                VIDFailureExplained.append("{2} Upgraded VID {0} from interface {1} to PVID because VID {3} failed".format(messageContent[0], entryInterface, entryNode, failedPVID))

        if(failedHellosPVID):
            formattedFailedHellosPVID = "[{0}]".format(failedHellosPVID)
            if(messageContent[5] == formattedFailedHellosPVID):
                farthestTimeStamp.append(entryTimeStamp)
                upgradedVIDs.append((messageContent[0], entryNode))
                VIDFailureExplained.append("{2} Upgraded VID {0} from interface {1} to PVID because VID {3} failed".format(messageContent[0], entryInterface, entryNode, failedHellosPVID))

    for entry in newCPVIDs:
        entryTimeStamp, entryInterface, entryMessage, entryNode = extractLogEntryInfo(entry)

        timeStampDifference = entryTimeStamp - linkFailureTime
        validFailureLog = "-1 day" not in str(timeStampDifference)
        messageContent = entryMessage.split(" ")

        for VIDs in upgradedVIDs:
            if(messageContent[0] == VIDs[0] and validFailureLog):
                farthestTimeStamp.append(entryTimeStamp)
                VIDFailureExplained.append("{2} Added CPVID {0} from interface {1} because {3} upgraded its PVID".format(messageContent[0], entryInterface, entryNode, VIDs[1]))

    return farthestTimeStamp


if __name__ == "__main__":
    main()
