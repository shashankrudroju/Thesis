#!/usr/bin/env python
from GENIutils import *

def main():
    # One argument is necessary, the name of the test
    if(len(sys.argv) != 2):
        sys.exit("Incorrect Number of Arguments given (./RSTPCollection.py [TEST ID])")
    testName = str(sys.argv[1]) # grab the name of the test

    # Information from credentials file needed for operation
    clientTrafficSource = getConfigInfo("RSTP Utilities", "endNodeTrafficSource")
    endNodeNamingSyntax = getConfigInfo("RSTP Utilities", "endNodeName")
    remoteWorkingDirectory = getConfigInfo("RSTP Utilities", "remoteCodeDirectory")
    RSPEC = getConfigInfo("Local Utilities", "RSPEC")
    GENIDict = buildDictonary(RSPEC)

    # Create a new directory in which the test results will be stored (RSTP_Test is added at the end of the directory name for consistency)
    newDir = "./RSTP_Test_{}".format(testName)
    os.makedirs(newDir)

    centralizeSwitchFiles = ("mkdir {0}_files && "
                       "mergecap *.pcap -w {0}Merge.pcapng && "
                       "editcap -F pcap {0}Merge.pcapng {0}Merge.pcap && "
                       "cp /var/log/openvswitch/ovs-vswitchd.log {0}.log && "
                       "rm *.pcapng && "
                       "mv *.* {0}_files/ && "
                       "zip -r {0}_files.zip {0}_files/") # Might change the first "&&" to a ";" in the event the folder already exists

    centralizeClientFiles = ("mkdir {0}_files && "
                             "sudo python TrafficGenerator.py -a results.pcap && "
                             "mv *.txt {0}_files/ && "
                             "mv *.pcap {0}_files/ && "
                             "zip -r {0}_files.zip {0}_files/")

    for currentRemoteNode in GENIDict:
        updatedCentralizeFiles = ""

        if(endNodeNamingSyntax not in currentRemoteNode):
            updatedCentralizeFiles = centralizeSwitchFiles.format(currentRemoteNode)

        elif(endNodeNamingSyntax in currentRemoteNode and currentRemoteNode != clientTrafficSource):
            updatedCentralizeFiles = centralizeClientFiles.format(currentRemoteNode)

        if(updatedCentralizeFiles):
            trafficFileLocation = str(os.path.join(remoteWorkingDirectory, currentRemoteNode + "_files.zip").replace("\\", "/"))
            localLocation = str(os.path.join(newDir, currentRemoteNode + ".zip").replace("\\", "/"))
            open(localLocation, 'a').close()
            print(currentRemoteNode)
            orchestrateRemoteCommands(currentRemoteNode, GENIDict, updatedCentralizeFiles) # Create the zip file
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


if __name__ == "__main__":
    main()
