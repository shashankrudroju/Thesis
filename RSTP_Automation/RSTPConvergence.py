#!/usr/bin/env python
from GENIutils import *

def main():
    dirList = []
    resultsList = []
    trafficList = []
    finalBreakTime = 0
    convergenceTime = 0
    endNodeNamingSyntax = getConfigInfo("RSTP Utilities", "endNodeName")

    if(len(sys.argv) != 2):
        sys.exit("Incorrect Number of Arguments given (./RSTPConvergence.py [RSTP TEST NAME])")
    testDir = str(sys.argv[1])
    fileName = "{0}.csv".format(testDir)

    f = open(fileName, "w+")
    f.write("Time Stamp,Message Type,Log Source,Traffic Source,Action,Change\n")

    for root, dirs, files in os.walk(testDir):
        for name in dirs:
            dirList.append(os.path.join(root, name).replace("\\", "/"))

    for eachRoot in dirList:
        nodeName = re.search('(?<=/)(.*)(?=_files)', eachRoot).group(0)

        if(endNodeNamingSyntax not in nodeName):
            for root, dirs, files in os.walk(eachRoot):
                for file in files:
                    if("Merge" in file):
                        capTimestamps = analyzeRSTPCap(os.path.join(root, file).replace("\\", "/"), nodeName)

                    elif(".log" in file):
                        logTimestamps, breakTime = analyzeRSTPLog(os.path.join(root, file).replace("\\", "/"), nodeName)

                        for key in breakTime:
                            if(key == "-1:"):
                                finalBreakTime = breakTime[key][0]

            resultsList.append(breakTime)

            nodeTimestamps = capTimestamps + logTimestamps
            nodeTimestamps.sort()
            for stamp in nodeTimestamps:
                f.write(stamp + "\n")

            nodeTimestamps[:] = []

        else:
            for root, dirs, files in os.walk(eachRoot):
                for file in files:
                    if("trafficResult" in file):
                        result = analyzeClientLog(os.path.join(root, file).replace("\\", "/"))
                        clientEntry = "{0}: {1}\n".format(nodeName, result).replace(",", "")
                        trafficList.append(clientEntry)

    lastConvergedStamp = 0
    if(finalBreakTime != 0):
        f.write("\nLink Break Time: " + str(finalBreakTime) + "\n")
        for convergeUpdates in resultsList: # for each nodes dictonary (result) with a key of a port, and a value of a list with convergence timestamps
            for port in convergeUpdates: # for each key (port) in the dictionaries
                for stamp in convergeUpdates[port]: # for each state or role change timestamp for each port on the RSTP node
                    if(stamp > lastConvergedStamp): # if the timestamp is greater that the current largest timestamp
                        lastConvergedStamp = stamp
        f.write("Final converged stamp: " + str(lastConvergedStamp) + "\n")

        start = datetime.datetime.strptime(finalBreakTime, '%H:%M:%S.%f')
        end = datetime.datetime.strptime(lastConvergedStamp, '%H:%M:%S.%f')
        diff = end - start
        convergenceTime = diff.total_seconds() * 1000
        f.write("Convergence Time: " + str(convergenceTime) + "\n")

    for entry in trafficList:
        f.write(entry)

    f.close()
    print("Convergence process completed ({0} file created in current directory)".format(fileName))

    return None


###########END NODE FUNCTIONS###########
def analyzeClientLog(logFile):
    with open(logFile, "r") as readFile:
        trafficResult = readFile.read()

    return trafficResult


###########OVS LOG FUNCTIONS###########
def analyzeRSTPLog(logFile, nodeName):
    fileToParse = logFile

    #0 = Timestamp (UTC), 1 = OVS port #, 2 = before state, 3 = after state
    outputFormat = "{0},log update,{1},port {2},{3} ---> {4}"

    changeLog = 0
    timestamps = []
    testChange = defaultdict(list) #A dictonary where each key is a port #, and each value is a list containing matched log entries for convergence changes via their time stamp

    with open(fileToParse, "r") as readFile:
        for line in readFile:
            #look for port role changes from other nodes that aren't the breaking node for convergence
            #(1/2) Root/Designated ---> Disabling_Exec would be a link down event. The state wouldn't work because Forwarding ---> Discarding
            #(2/2) could be for a number of reasons that don't involve a manual/unexpected link/node failure
            if("Port_role_transition_sm" in line):
                result = getPortRoleTransistion(line)

                if(result):
                    test = re.split("T|Z", result[0])
                    logEntry = outputFormat.format(test[1], nodeName, result[1].rstrip(":"), result[2], result[3])

                    if(result[3] == "Disabling_Exec"):
                        changeLog = test[1]
                        testChange["-1:"].append(test[1]) #-1 port is just a made up entry for broken link (broken node as well?)
                        logEntry += ",Interface failed"

                    else:
                        majorRoles = ["root", "designated", "alternate"]
                        for role in majorRoles:
                            if(not role in result[2].lower() and role in result[3].lower()):
                                testChange[result[1]].append(test[1])
                                logEntry += ",Port role changed"

                    if(len(logEntry.split(",")) != 6):
                        logEntry += ",N/A"

                    timestamps.append(logEntry)


            #look for Learning ---> Forwarding or Forwarding ---> Discarding for convergence, as that means a port state has changed
            #as a result of a prior change
            elif("set RSTP port state" in line):
                otherResult = getPortStateTransition(line)

                if(otherResult):
                    otherTest = re.split("T|Z", otherResult[0])
                    logEntry = outputFormat.format(otherTest[1], nodeName, otherResult[1].rstrip(":"), otherResult[2], otherResult[3])

                    if(otherResult[3] == "Forwarding" or otherResult[3] == "Discarding"):
                        changeLog = otherTest[1]
                        testChange[otherResult[1]].append(otherTest[1])
                        logEntry += ",Port state changed"

                    else:
                        logEntry += ",N/A"

                    timestamps.append(logEntry)

    return timestamps, testChange # changeLog otherwise for just break time


def getPortStateTransition(transitionLog):
    transitionSymbol = "->"
    result = []

    #splits on both "|" and whitespace characters (\s)
    logContent = re.split("\s|\|", transitionLog)
    position = logContent.index(transitionSymbol)

    timeStamp = logContent[0]
    portNum = logContent[6]
    beforeState = logContent[position - 1]
    afterState = logContent[position + 1]

    if(beforeState not in afterState):
        result.extend([timeStamp, portNum, beforeState, afterState])

    return result


def getPortRoleTransistion(transitionLog):
    transitionSymbol = "->"
    result = []

    #Exec states in the port role transition state machine dictionary are not defined per 802.1D-2004, they are an OVS implementation for switch
    #statement fall-throughs when transitioning between legitamite roles.
    port_role_transition_state_machine = {
        0: "Init", #PORT_ROLE_TRANSITION_SM_INIT
        1: "Init_Exec", #PORT_ROLE_TRANSITION_SM_INIT_PORT_EXEC
        2: "Disabling_Exec", #PORT_ROLE_TRANSITION_SM_DISABLE_PORT_EXEC
        3: "Disabling", #PORT_ROLE_TRANSITION_SM_DISABLE_PORT
        4: "Disabled_Exec", #PORT_ROLE_TRANSITION_SM_DISABLED_PORT_EXEC
        5: "Disabled", # PORT_ROLE_TRANSITION_SM_DISABLED_PORT
        6: "Root_Exec",# PORT_ROLE_TRANSITION_SM_ROOT_PORT_EXEC
        7: "Root", #PORT_ROLE_TRANSITION_SM_ROOT_PORT
        8: "Reroot_Exec",  #PORT_ROLE_TRANSITION_SM_REROOT_EXEC
        9: "Root_Agreed_Exec", #PORT_ROLE_TRANSITION_SM_ROOT_AGREED_EXEC
        10: "Root_Proposed_Exec", #PORT_ROLE_TRANSITION_SM_ROOT_PROPOSED_EXEC
        11: "Root_Forward_Exec", #PORT_ROLE_TRANSITION_SM_ROOT_FORWARD_EXEC
        12: "Root_Learn_Exec", #PORT_ROLE_TRANSITION_SM_ROOT_LEARN_EXEC
        13: "Root_Rerooted_Exec", #PORT_ROLE_TRANSITION_SM_REROOTED_EXEC
        14: "Designated_Exec", #PORT_ROLE_TRANSITION_SM_DESIGNATED_PORT_EXEC
        15: "Designated", #PORT_ROLE_TRANSITION_SM_DESIGNATED_PORT
        16: "Designated_Retired_Exec", #PORT_ROLE_TRANSITION_SM_DESIGNATED_RETIRED_EXEC
        17: "Designated_Synced_Exec", #PORT_ROLE_TRANSITION_SM_DESIGNATED_SYNCED_EXEC
        18: "Designated_Propose_Exec", #PORT_ROLE_TRANSITION_SM_DESIGNATED_PROPOSE_EXEC
        19: "Designated_Forward_Exec", #PORT_ROLE_TRANSITION_SM_DESIGNATED_FORWARD_EXEC
        20: "Designated_Learn_Exec", #PORT_ROLE_TRANSITION_SM_DESIGNATED_LEARN_EXEC
        21: "Designated_Discard_Exec", #PORT_ROLE_TRANSITION_SM_DESIGNATED_DISCARD_EXEC
        22: "Alternate_Exec", #PORT_ROLE_TRANSITION_SM_ALTERNATE_PORT_EXEC
        23: "Alternate", #PORT_ROLE_TRANSITION_SM_ALTERNATE_PORT
        24: "Alternate_Agreed_Exec", #PORT_ROLE_TRANSITION_SM_ALTERNATE_AGREED_EXEC
        25: "Alternate_Proposed_Exec", #PORT_ROLE_TRANSITION_SM_ALTERNATE_PROPOSED_EXEC
        26: "Block_Exec", #PORT_ROLE_TRANSITION_SM_BLOCK_PORT_EXEC
        27: "Block", #PORT_ROLE_TRANSITION_SM_BLOCK_PORT
        28: "Backup_Exec" #PORT_ROLE_TRANSITION_SM_BACKUP_PORT_EXEC
    }

    #splits on both "|" and whitespace characters (\s)
    logContent = re.split("\s|\|", transitionLog)
    position = logContent.index(transitionSymbol)

    timeStamp = logContent[0]
    portNum = logContent[6]
    beforeState = port_role_transition_state_machine[int(logContent[position - 1])]
    afterState = port_role_transition_state_machine[int(logContent[position + 1])]

    if(beforeState not in afterState and afterState not in beforeState):
        result.extend([timeStamp, portNum, beforeState, afterState])

    return result


###########CAPTURE FILE FUNCTIONS###########
def analyzeRSTPCap(captureFile, nodeName):
    timestamps = []

    RSPEC = getConfigInfo("Local Utilities", "RSPEC")
    addrs = getMACAddrs(RSPEC)
    packets = rdpcap(captureFile)

    outputFormat = "{0},cap update,{1},{2} [{3}],{summary},{4}"

    for packet in packets:
        if(packet.haslayer(Dot3) and packet.haslayer(STP)):
            srcAddr = packet[Dot3].src.replace(':', '')
            flags = "{0:08b}".format(packet[STP].bpduflags)
            agreementFlag = flags[1]
            proposalFlag = flags[6]
            TCNFlag = flags[7] # TCN flag (index 7, first bit) = LSB
            portRoleFlag = flags[4] + flags[5]
            roleName = {"00":"Unknown", "01":"Alternate/Backup", "10":"Root", "11":"Designated"}

            if("1" in {agreementFlag, proposalFlag, TCNFlag}):
                flagsSummary = ""
                trafficSource = findMatch(addrs, srcAddr)
                test = datetime.datetime.fromtimestamp(packet.time).strftime('%H:%M:%S.%f')
                test2 = str(datetime.datetime.utcfromtimestamp(packet.time)).split(" ")

                if(nodeName == trafficSource):
                    flagsSummary += "Sent | "
                else:
                    flagsSummary += "Received | "

                flagsSummary += "{role} Role |".format(role=roleName[portRoleFlag])

                if(proposalFlag == "1"):
                    flagsSummary += " Proposal"

                if(agreementFlag == "1"):
                    flagsSummary += " Agreement"

                if(TCNFlag == "1"):
                    flagsSummary += " TCN"

                logEntry = outputFormat.format(str(test2[1][:-3]), nodeName, trafficSource, packet[Dot3].src, "N/A", summary=flagsSummary)
                timestamps.append(logEntry)

    return timestamps


def getMACAddrs(rspec):
    nodeIntAddrs = {}
    rspec = minidom.parse(rspec)
    listOfNodes = rspec.getElementsByTagName("node")

    for node in listOfNodes:
        nodeName = (node.attributes["client_id"]).value
        nodeIntAddrs[nodeName] = []

        children = node.childNodes
        for child in children:
            if(str(child.nodeName) == "interface"):
                nodeIntAddrs[nodeName].append(child.attributes["mac_address"].value)

    return nodeIntAddrs


def findMatch(addrs, dictValue):
    result = ""
    for node in addrs.keys():
        for address in addrs[node]:
            if(dictValue == address):
                result = node
                break

    return result


if __name__ == "__main__":
    main()


"""
#test = datetime.datetime.strptime(result[0],"H:%M:%S.%fZ") - was in part of the main() code, old way of printing? Keeping just in case.

>>> from datetime import datetime, time
>>> start = datetime.striptime('15:10:18.874', '%H:%M:%S.%f')
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
AttributeError: type object 'datetime.datetime' has no attribute 'striptime'
>>> start = datetime.strptime('15:10:18.874', '%H:%M:%S.%f')
>>> end = datetime.strptime('15:10:20.391', '%H:%M:%S.%f')
>>> end - start
datetime.timedelta(0, 1, 517000)
>>> diff = end - start
>>> diff.total_seconds() * 1000
1517.0 = miliseconds of different


defautls for the three node topology with a node on each switch:
node-0:
eth1         : {rstp_designated_bridge_id="8.000.6691b6eb8540", rstp_designated_path_cost="0", rstp_designated_port_id="8003", rstp_port_id="8003", rstp_port_role=Designated, rstp_port_state=Forwarding}
eth2         : {rstp_designated_bridge_id="8.000.6691b6eb8540", rstp_designated_path_cost="0", rstp_designated_port_id="8002", rstp_port_id="8002", rstp_port_role=Designated, rstp_port_state=Forwarding}
eth3         : {rstp_designated_bridge_id="8.000.6691b6eb8540", rstp_designated_path_cost="0", rstp_designated_port_id="8001", rstp_port_id="8001", rstp_port_role=Designated, rstp_port_state=Forwarding}

OFPT_FEATURES_REPLY (xid=0x2): dpid:00006691b6eb8540
n_tables:254, n_buffers:256
capabilities: FLOW_STATS TABLE_STATS PORT_STATS QUEUE_STATS ARP_MATCH_IP
actions: output enqueue set_vlan_vid set_vlan_pcp strip_vlan mod_dl_src mod_dl_dst mod_nw_src mod_nw_dst mod_nw_tos mod_tp_src mod_tp_dst
 1(eth1): addr:02:58:50:db:98:f4
     config:     0
     state:      STP_FORWARD
     speed: 0 Mbps now, 0 Mbps max
 2(eth2): addr:02:09:54:ec:f2:11
     config:     0
     state:      STP_FORWARD
     speed: 0 Mbps now, 0 Mbps max
 3(eth3): addr:02:d2:a2:d1:b2:fb
     config:     0
     state:      STP_FORWARD
     speed: 0 Mbps now, 0 Mbps max
 LOCAL(br0): addr:66:91:b6:eb:85:40
     config:     PORT_DOWN
     state:      LINK_DOWN
     speed: 0 Mbps now, 0 Mbps max
OFPT_GET_CONFIG_REPLY (xid=0x4): frags=normal miss_send_len=0


node-1:
eth1         : {rstp_designated_bridge_id="8.000.9e247a1f9146", rstp_designated_path_cost="200000", rstp_designated_port_id="8003", rstp_port_id="8003", rstp_port_role=Designated, rstp_port_state=Forwarding}
eth2         : {rstp_designated_bridge_id="8.000.6691b6eb8540", rstp_designated_path_cost="0", rstp_designated_port_id="8002", rstp_port_id="8002", rstp_port_role=Root, rstp_port_state=Forwarding}
eth3         : {rstp_designated_bridge_id="8.000.9e247a1f9146", rstp_designated_path_cost="200000", rstp_designated_port_id="8001", rstp_port_id="8001", rstp_port_role=Designated, rstp_port_state=Forwarding}

OFPT_FEATURES_REPLY (xid=0x2): dpid:00009e247a1f9146
n_tables:254, n_buffers:256
capabilities: FLOW_STATS TABLE_STATS PORT_STATS QUEUE_STATS ARP_MATCH_IP
actions: output enqueue set_vlan_vid set_vlan_pcp strip_vlan mod_dl_src mod_dl_dst mod_nw_src mod_nw_dst mod_nw_tos mod_tp_src mod_tp_dst
 1(eth1): addr:02:f1:96:cd:90:6b
     config:     0
     state:      STP_FORWARD
     speed: 0 Mbps now, 0 Mbps max
 2(eth2): addr:02:95:19:e6:f6:04
     config:     0
     state:      STP_FORWARD
     speed: 0 Mbps now, 0 Mbps max
 3(eth3): addr:02:6e:46:f1:a4:8f
     config:     0
     state:      STP_FORWARD
     speed: 0 Mbps now, 0 Mbps max
 LOCAL(br1): addr:9e:24:7a:1f:91:46
     config:     PORT_DOWN
     state:      LINK_DOWN
     speed: 0 Mbps now, 0 Mbps max
OFPT_GET_CONFIG_REPLY (xid=0x4): frags=normal miss_send_len=0


node-2:
pjw7904@node-2:~$ sudo ovs-vsctl list p eth1 | grep rstp_status
eth1         : {rstp_designated_bridge_id="8.000.fee02b9a4848", rstp_designated_path_cost="200000", rstp_designated_port_id="8003", rstp_port_id="8003", rstp_port_role=Designated, rstp_port_state=Forwarding}
eth2         : {rstp_designated_bridge_id="8.000.9e247a1f9146", rstp_designated_path_cost="200000", rstp_designated_port_id="8001", rstp_port_id="8002", rstp_port_role=Alternate, rstp_port_state=Discarding}
eth3         : {rstp_designated_bridge_id="8.000.6691b6eb8540", rstp_designated_path_cost="0", rstp_designated_port_id="8001", rstp_port_id="8001", rstp_port_role=Root, rstp_port_state=Forwarding}

OFPT_FEATURES_REPLY (xid=0x2): dpid:0000fee02b9a4848
n_tables:254, n_buffers:256
capabilities: FLOW_STATS TABLE_STATS PORT_STATS QUEUE_STATS ARP_MATCH_IP
actions: output enqueue set_vlan_vid set_vlan_pcp strip_vlan mod_dl_src mod_dl_dst mod_nw_src mod_nw_dst mod_nw_tos mod_tp_src mod_tp_dst
 1(eth1): addr:02:b5:13:65:ac:76
     config:     0
     state:      STP_FORWARD
     speed: 0 Mbps now, 0 Mbps max
 2(eth2): addr:02:3e:a1:91:a1:51
     config:     0
     state:      0
     speed: 0 Mbps now, 0 Mbps max
 3(eth3): addr:02:22:b9:0e:db:6d
     config:     0
     state:      STP_FORWARD
     speed: 0 Mbps now, 0 Mbps max
 LOCAL(br2): addr:fe:e0:2b:9a:48:48
     config:     PORT_DOWN
     state:      LINK_DOWN
     speed: 0 Mbps now, 0 Mbps max
OFPT_GET_CONFIG_REPLY (xid=0x4): frags=normal miss_send_len=0
"""
