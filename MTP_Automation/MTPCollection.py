#!/usr/bin/env python
#Grabs MTP convergence time information from specified nodes
#Author: Peter Willis (pjw7904@rit.edu)
from GENIutils import *

def main():
    argParser = argparse.ArgumentParser(description = "Collects and analyizes MTP Metrics from the files remote GENI nodes generates")
    argParser.add_argument("-i", "--MSTC", action = "store_true")
    argParser.add_argument("-l", "--log", action = "store_true")
    argParser.add_argument("-o", "--output", action = "store_true")
    argParser.add_argument("-n", "--new", action = "store_true") # For mtpd.log for now, quick and dirty inclusion
    argParser.add_argument("-f", "--failure")
    argParser.add_argument("-a", "--all")
    args = argParser.parse_args()

    RSPEC = getConfigInfo("Local Utilities", "RSPEC")
    codeDirectory = getConfigInfo("MTP Utilities", "localCodeDirectory")
    codeDestination = getConfigInfo("GENI Credentials", "remoteCodeDirectory")
    endNodeNamingSyntax = getConfigInfo("MTP Utilities", "endNodeName")
    GENIDict = buildDictonary(RSPEC)
    remoteWorkingDirectory = os.path.join(codeDestination, os.path.basename(codeDirectory)).replace("\\", "/") # Windows POSIX change

    if(args.all):
        #testName = args.all
        args.MSTC = True
        args.failure = args.all
        args.log = True
        args.output = True
        #dataDir = retrieveAllData(GENIDict, endNodeNamingSyntax, remoteWorkingDirectory, testName)
        #getConvergenceData(dataDir)

    if(args.MSTC):
        fileName = setCollectionFile("MSTC", "convergenceTime.txt", remoteWorkingDirectory, GENIDict, endNodeNamingSyntax)
        retrieveMSTCData(endNodeNamingSyntax, fileName)

    if(args.failure):
        nodeWhoBroke = args.failure
        fileName = setCollectionFile("LinkFailure", "linkFail.txt", remoteWorkingDirectory, GENIDict, endNodeNamingSyntax)
        retrieveLinkFailureData(nodeWhoBroke, fileName)

    if(args.log):
        fileName = setCollectionFile("Traffic", "MSTC.txt", remoteWorkingDirectory, GENIDict, endNodeNamingSyntax)

    if(args.output):
        runOutputScript = "cd {} && sudo python MTPOutputAnalyzer.py screenlog.0" # custom command due to a script having to be run
        fileName = setCollectionFile("Console", runOutputScript, remoteWorkingDirectory, GENIDict, endNodeNamingSyntax, customCmd=True)

    if(args.new):
        fileName = setCollectionFile("Events", "mtpd.log", remoteWorkingDirectory, GENIDict, endNodeNamingSyntax)

    return None


def setCollectionFile(collectionType, fileToCollect, remoteWorkingDirectory, GENIDict, endNodeNamingSyntax, customCmd=False):
    # Setting up file for aggregated collection
    currentTime = time.strftime("%Y%m%d%H%M%S")
    fileName = 'MTP_{0}Log_{1}'.format(collectionType, currentTime)
    collectionFile = open(fileName, "w+")

    if(customCmd):
        grabbingFileContent = fileToCollect.format(remoteWorkingDirectory)
    else:
        grabbingFileContent = "sudo cat {0}/{1}".format(remoteWorkingDirectory, fileToCollect)

    print("\n+---------Number of Nodes to Collect Data From: {0}--------+".format(len(GENIDict)))
    for currentRemoteNode in GENIDict:
        if(endNodeNamingSyntax not in currentRemoteNode):
            fileData = orchestrateRemoteCommands(currentRemoteNode, GENIDict, grabbingFileContent, getOutput = True)
            collectionFile.write(currentRemoteNode + ":\n")
            collectionFile.write(str(fileData))
            print("Retrieved MTP convergence data from {}".format(currentRemoteNode))

    collectionFile.close()

    return fileName


def retrieveMSTCData(endNodeNamingSyntax, fileName):
    MSTC = []
    MSTCvalue = 0
    with open(fileName, "r") as readFile, open(fileName, "a") as writeFile:
        for line in readFile:
            #change based on who is root
            if "node-" in line and "node-0" not in line and "endnode-" not in line:
                MSTCvalue = 1
                continue

            if(MSTCvalue == 1):
                MSTC.append(int(line.rstrip("\n")))
                MSTCvalue = 0

        MSTCtime = 0
        for eachTime in MSTC:
            if(eachTime > MSTCtime):
                MSTCtime = eachTime

        writeFile.write("\n\nMSTC time: " + str(MSTCtime))

    print("\nMTP initial convergence information collection completed")

    return None


def retrieveLinkFailureData(nodeWhoBroke, fileName):
    startingValue = "NULL"
    brokenNodeSection = False
    newNodeSection = "node-"
    BrokenNode = nodeWhoBroke + ":"
    LinkFailureConvergence = []
    brokenVIDs = []

    with open(fileName, "r") as readFile, open(fileName, "a") as writeFile:
        for line in readFile:
            if(newNodeSection in line):
                if(BrokenNode in line):
                    brokenNodeSection = True
                else:
                    brokenNodeSection = False

            if(brokenNodeSection == True and newNodeSection not in line):
                if("A LINK FAILURE WAS FOUND AT" in line):
                    startingValue = line[line.find("[")+1:line.find("]")]
                    brokenNodeSection = False

                elif("FAILED VID'S WERE REMOVED AT" in line):
                    brokenVIDs.append(line[line.rfind("[")+1:line.rfind("]")])

                brokenNodeSection = True

            elif(brokenNodeSection == False and newNodeSection not in line and "FAILED VID'S WERE REMOVED AT" not in line and "WAS TAKEN DOWN AT" not in line):
                failureEntry = re.findall(r'\[(.*?)\]', line)
                LinkFailureConvergence.append(failureEntry)

        writeFile.write("\nTime when link failure was first found: {0}\n".format(startingValue))
        writeFile.write("VIDs lost from source of link failure: {0}\n\n".format(brokenVIDs))

        timeFormat = '%H:%M:%S:%f'
        d2 = datetime.datetime.strptime(startingValue, timeFormat)
        convergenceTime = timedelta(seconds=0)

        for element in LinkFailureConvergence:
            for VID in brokenVIDs:

                if(element[1][:len(VID)] == VID):
                    d1 = datetime.datetime.strptime(element[0], timeFormat)
                    timeDiff = d1 - d2

                    if "-1 day" not in str(timeDiff):
                        writeFile.write(element[1] + "\n")
                        writeFile.write(str(timeDiff) + "\n\n")

                        if(timeDiff > convergenceTime):
                            convergenceTime = timeDiff

        writeFile.write("PVID Tree Re-Convergence Time: " + str(convergenceTime))

    print("\nMTP link failure convergence information collection completed")

    return None


def retrieveAllData(GENIDict, endNodeNamingSyntax, remoteWorkingDirectory, testName):
    newDir = "./MTP_Test_{}".format(testName)
    os.makedirs(newDir)

    centralizeFiles = ("cd {0} && mkdir {1}_files && "
                       "cp screenlog.0 console.txt && "
                       "cp *.txt {1}_files && "
                       "rm console.txt && "
                       "zip -r {1}_files.zip {1}_files/")

    for currentRemoteNode in GENIDict:
        if(endNodeNamingSyntax not in currentRemoteNode):
            updatedCentralizeFiles = centralizeFiles.format(remoteWorkingDirectory, currentRemoteNode)
            trafficFileLocation = str(os.path.join(remoteWorkingDirectory, currentRemoteNode + "_files.zip").replace("\\", "/"))
            localLocation = str(os.path.join(newDir, currentRemoteNode + ".zip").replace("\\", "/"))
            open(localLocation, 'a').close()

            orchestrateRemoteCommands(currentRemoteNode, GENIDict, updatedCentralizeFiles) # Create the zip file
            getGENIFile(currentRemoteNode, GENIDict, trafficFileLocation, localLocation) # Grab the zip file

        else:
            print("nothing to do for {}".format(currentRemoteNode))

    # Extract everything in the newly-created directory and discard the zip files
    for root, dirs, files in os.walk(newDir):
        for filename in files:
            if(filename.endswith(".zip")):
                absFileLocation = os.path.join(os.path.abspath(newDir).replace("\\", "/"), filename).replace("\\", "/")
                unzip = zipfile.ZipFile(absFileLocation)
                unzip.extractall(newDir)
                unzip.close()
                os.remove(absFileLocation)

    return newDir


if __name__ == "__main__":
    main()
