#!/usr/bin/env python
from scapy.all import *
from subprocess import call
from time import sleep
from itertools import groupby
from operator import itemgetter
import datetime
import time
import os
import subprocess
import tempfile
import ConfigParser
import argparse

frameCounter = {} # Global dictionary to hold frame/packet payload content for analysis on the receiving end


def main():
    # ArgumentParser object to read in command line arguments
    argParser = argparse.ArgumentParser(description = "Traffic generator (IEEE 802.3 and TCP/IP Protocol Suite) for switch testing purposes")

    # Determine where the traffic is going
    argParser.add_argument("-n", "--node") # Use the node argument for ease of use or...
    # ... use the MAC and IPv4 arguments
    argParser.add_argument("-m", "--MAC")
    argParser.add_argument("-i", "--IPv4")

    # Determine what type of traffic needs to be sent
    argParser.add_argument("-u", "--unicast")                            # argument of protocol needed
    argParser.add_argument("-r", "--receive")                            # argument of protocol needed
    argParser.add_argument("-b", "--broadcast")                          # argument of protocol needed
    argParser.add_argument("-p", "--performance", action = "store_true") # no arguments needed
    argParser.add_argument("-a", "--analyze")                            # argument of capture needed

    # Determine factors supporting the traffic
    argParser.add_argument("-c", "--count", type = int) # argument of the number of frames to send or loops in the performance function)
    argParser.add_argument("-e", "--port", type = int) # By default it's eth1 for GENI nodes, but if for some reason it needs to change, use this argument
    argParser.add_argument("-d", "--delay", type = float)

    # Parse the arguments
    args = argParser.parse_args()

    # Gather the necessary info that is generic across all functions
    count = args.count
    port = args.port
    delay = args.delay

    # Boolean statements describing what action the user would like to take
    analyzingTraffic = args.analyze and not (args.unicast or args.broadcast or args.performance or args.receive)
    receivingTraffic = args.receive and not (args.unicast or args.broadcast or args.performance)
    sendingBroadcastTraffic = args.broadcast and not (args.unicast or args.receive or args.performance)
    sendingUnicastTraffic = args.unicast and not (args.broadcast or args.receive or args.performance)
    sendingPerformanceTraffic = args.performance and not (args.unicast or args.broadcast or args.receive)
    conflictingArguments = (args.node and (args.MAC or args.IPv4)) or (not args.node and not (args.MAC and args.IPv4))

    if(receivingTraffic):
        trafficToRecv = args.receive # Argument is the protocol traffic to receive
        recvTraffic(trafficToRecv)

    elif(sendingBroadcastTraffic):
        dstPhysicalAddr, dstLogicalAddr = "ff:ff:ff:ff:ff:ff", "4.3.2.1"
        protocol = args.broadcast
        sendTraffic(dstPhysicalAddr, dstLogicalAddr, protocol, count, delay)

    elif(sendingUnicastTraffic):
        if(conflictingArguments):
            sys.exit('Either enter a node name, or use the -m and -i flags, not both')
        dstPhysicalAddr, dstLogicalAddr = getTrafficInfo(args) # Grab L2 + L3 destination address info from the node name or manual inputs
        protocol = args.unicast # Argument is the protocol traffic to receive
        sendTraffic(dstPhysicalAddr, dstLogicalAddr, protocol, count, delay)

    elif(sendingPerformanceTraffic): # THIS PROB DOESN'T WORK ATM, NEED TO FIGURE OUT WHAT IS MISSING FROM UNICAST STUFF WHEN IT WAS MOVED
        # Build the PDU before sending it off to the function to send it
        testPDU = Ether(dst = dstPhysicalAddr)/IP(dst = dstLogicalAddr)/UDP(dport = [65000, 65001, 65002])/Raw(RandString(size = 1458))
        sendPerfTaffic(testPDU, iface = "eth1", loop = 100000, parse_results = True) # Utilizes tcpreply for performance and metrics

    elif(analyzingTraffic):
        captureFile = args.analyze
        analyzeTraffic(captureFile)

    else:
        sys.exit("Syntax error: incorrect arguments (use -h for help)") # Error out if the arguments are bad or missing

    return None


def sendTraffic(dstPhysicalAddr, dstLogicalAddr, protocol, count, delay):
    # Information needed to generate a custom payload and build protocol headers
    srcPhysicalAddr = get_if_hwaddr("eth1")
    seqNum = 0
    complete = False

    if(protocol == "ICMP"):
        PDUToSend = Ether(dst = dstPhysicalAddr)/IP(dst = dstLogicalAddr)/ICMP()
        generatePingPongTraffic(PDUToSend, count)

    elif(protocol == "MTP_ucast"):
        PDUToSend = Ether(src = srcPhysicalAddr, dst = dstPhysicalAddr, type = 0xff00)
        generatePingPongTraffic(PDUToSend, count)

    elif(protocol == "MTP_ucast_test"):
        PDUToSend = Ether(src = srcPhysicalAddr, dst = dstPhysicalAddr, type = 0xff00)
        generateContinousTraffic(PDUToSend, count, srcPhysicalAddr, delay)

    elif(protocol == "ARP"):
        fakePhysicalSourceAddr, fakeLogicalSourceAddr = "CA:FE:F0:0D:BE:EF", "1.2.3.4"
        PDUToSend = Ether(src = srcPhysicalAddr, dst = dstPhysicalAddr)/ARP(hwsrc = fakePhysicalSourceAddr, psrc = fakeLogicalSourceAddr, pdst = dstLogicalAddr)
        generateContinousTraffic(PDUToSend, count, srcPhysicalAddr, delay)

    elif(protocol == "MTP_bcast"):
        PDUToSend = Ether(src = srcPhysicalAddr, dst = dstPhysicalAddr, type = 0xff00)
        generateContinousTraffic(PDUToSend, count, srcPhysicalAddr, delay)

    else:
        print("error, unknown protocol (supported arugments: ICMP, ARP, MTP_ucast [unicast], MTP_bcast [broadcast])")

    return None


def generateContinousTraffic(PDUToSend, numberOfFramesToSend, srcPhysicalAddr, delay):
    seqNum = 0
    payloadDelimiterSize = 2
    maxPayloadLength = 1514
    payloadPadding = 0
    complete = False

    if(numberOfFramesToSend is None):
        numberOfFramesToSend = -1

    while(not complete):
        try:
            seqNum += 1

            frameLength = len(str(seqNum) + srcPhysicalAddr) + len(PDUToSend) + payloadDelimiterSize
            if(frameLength < maxPayloadLength):
                payloadPadding = maxPayloadLength - frameLength
            else:
                payloadPadding = 0

            frameWithCustomPayload = PDUToSend/Raw(load = "{0}|{1}|{2}".format(srcPhysicalAddr, seqNum, RandString(size=payloadPadding)))
            sendp(frameWithCustomPayload, iface="eth1", count = 1, verbose = False)

            sys.stdout.write("\rSent {0} frames".format(seqNum))
            sys.stdout.flush()

            if(seqNum == numberOfFramesToSend):
                complete = True
                print("\nFinished\n")

            if(delay is not None):
                time.sleep(delay)

        except KeyboardInterrupt:
            complete = True
            print("\nFinished\n")

    return None


def generatePingPongTraffic(PDUToSend, numberOfFramesToSend):
    srploop(PDUToSend, iface="eth1", count = numberOfFramesToSend)

    return None


def sendPerfTaffic(x, pps=None, mbps=None, realtime=None, loop=0, file_cache=False, iface=None, replay_args=None, parse_results=False):
    """Send packets at layer 2 using tcpreplay for performance
    pps:  packets per second
    mpbs: MBits per second
    realtime: use packet's timestamp, bending time with real-time value
    loop: number of times to process the packet list
    file_cache: cache packets in RAM instead of reading from disk at each iteration  # noqa: E501
    iface: output interface
    replay_args: List of additional tcpreplay args (List[str])
    parse_results: Return a dictionary of information outputted by tcpreplay (default=False)  # noqa: E501
    :returns stdout, stderr, command used
    """

    if iface is None:
        iface = conf.iface

    perfCmd = "sudo tcpreplay --intf1={}".format(iface)

    # TCPReply arguments that could be added to the final command
    if pps is not None:
        perfCmd += " --pps=" + str(pps)
    elif mbps is not None:
        perfCmd += " --mbps=" + str(mbps)
    elif realtime is not None:
        perfCmd += " --multiplier=" + str(realtime)
    else:
        perfCmd += " --topspeed" # As fast as possible for the software or the hardware (almost never the hardware in our test cases)
    if loop:
        perfCmd += " --loop=" + str(loop)
    if file_cache:
        perfCmd += " --preload-pcap"

    # Check for any additional arguemnts we didn't cover.
    if replay_args is not None:
        perfCmd += str(replay_args)

    testFile = open("perfCap","w+b")
    #args.append(testFile.name)
    perfCmd += " perfCap"
    wrpcap(testFile, x)

    results = None
    print(perfCmd)

    try:
        proc = subprocess.Popen(perfCmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell = True)
        output, err = proc.communicate()
            #log_runtime.info(stdout)
            #log_runtime.warning(stderr)

        print(output)

        #if parse_results:
            #results = _parse_tcpreplay_result(stdout, stderr, perfCmd)

    except KeyboardInterrupt:
        log_interactive.info("Interrupted by user")

    except Exception:
        if conf.interactive:
            log_interactive.error("Cannot execute [%s]", perfCmd[0], exc_info=True)

        else:
            raise

    finally:
        os.unlink(testFile.name)

    return results


def recvTraffic(trafficToRecv):
    global frameCounter
    srcPhysicalAddr = get_if_hwaddr("eth1")
    filterToUse = "ether src not {} and {}" # example full cmd: tcpdump -i eth1 ether src not 02:de:3a:3f:a2:fd and icmp
    commandToUse = 'sudo tshark -i eth1 -w results.pcap {}'

    try:
        if(trafficToRecv == "ICMP"):
            filterToUse = filterToUse.format(srcPhysicalAddr, trafficToRecv.lower())
            recvdPDUs = sniff(iface = "eth1", filter = filterToUse, prn = replyToTraffic)

        elif(trafficToRecv == "ARP"):
            filterToUse = filterToUse.format(srcPhysicalAddr, trafficToRecv.lower())
            commandToUse = commandToUse.format(filterToUse)
            call(commandToUse, shell=True)

        elif(trafficToRecv == "MTP_ucast"):
            filterForMTPTraffic = "ether proto 0xff00"
            filterToUse = filterToUse.format(srcPhysicalAddr, filterForMTPTraffic)
            recvdPDUs = sniff(iface = "eth1", filter = filterToUse, prn = replyToTraffic)

        elif(trafficToRecv == "MTP_ucast_test"):
            filterForMTPTraffic = "ether proto 0xff00 and ether dst {0}".format(srcPhysicalAddr)
            filterToUse = filterToUse.format(srcPhysicalAddr, filterForMTPTraffic)
            commandToUse = commandToUse.format(filterToUse)
            call(commandToUse, shell=True)

        elif(trafficToRecv == "MTP_bcast"):
            filterForMTPTraffic = "ether proto 0xff00 and ether dst {0}".format("ff:ff:ff:ff:ff:ff")
            filterToUse = filterToUse.format(srcPhysicalAddr, filterForMTPTraffic)
            commandToUse = commandToUse.format(filterToUse)
            call(commandToUse, shell=True)

        else:
            sys.exit("error, unknown protocol (supported arugments: ICMP, ARP, MTP [Test Unicast Traffic Ethertype = 0xff00])")

    except KeyboardInterrupt:
        print("\nExited program")

    return None


def replyToTraffic(frame):
    replyPDU = Ether() # Empty PDU which will be overwritten to build a proper response

    if(hex(frame[Ether].type) == "0xff00"): # Have to stop MTP control messages from MTS' from being a reply as well
        replyPDU = Ether(src = frame[Ether].dst, dst = frame[Ether].src, type = frame[Ether].type)/Raw(load = "test") # Build a response by flipping the L2 src/dst addresses
        print("Replying to an incoming MTP Unicast Message from {} with a reply".format(str(frame[Ether].src)))

    elif(frame.haslayer(ICMP)):             # If the frame contains an ICMP header (Should be an ICMP Echo Request)
        replyPDU = Ether(dst = frame[Ether].src)/IP(dst = frame[IP].src)/ICMP(type = 0) # Build an ICMP Echo Response
        print("Replying to an incoming ICMP Echo Request from {} with an ICMP Echo Reply".format(str(frame[IP].src)))

    sendp(replyPDU, iface="eth1", count = 1, verbose = False) # Send the reply back to the source of the traffic

    return None

# Not used right now, prob just going to stay a function for sanity checks, morphed into analyzeTraffic
def getPayload(frame):
    global frameCounter

    if(hex(frame[Ether].type) == "0xff00"):   # MTP (data)
        payload = frame[Raw].load

    elif(hex(frame[Ether].type) == "0x806"): # ARP (leading zero in ethertype removed by Scapy [0x0806])
        payload = frame[Padding].load

    else:
        sys.exit("Can't find a payload")

    payloadContent = payload.split("|")
    source = payloadContent[0]
    newSeqNum = int(payloadContent[1])

    if source not in frameCounter:
        frameCounter[source] = [newSeqNum, [], 1] # Updated Sequence Number, List of missed frames, Total number of frames sent

    else:
        currentSeqNum = frameCounter[source][0]          # The current sequence number for the source address
        expectedNextSeqNum = frameCounter[source][0] + 1 # The next expected sequence number for the source address

        missedFrames = newSeqNum - expectedNextSeqNum # get frames 1-5, get frame 10, missing 6-9
        while(missedFrames != 0):
            missingSeqNum = currentSeqNum + missedFrames
            frameCounter[source][1].append(missingSeqNum)
            missedFrames -= 1

        frameCounter[source][0] = newSeqNum # Update the current sequence number
        frameCounter[source][2] += 1        # Update how many frames we have recieved from this source in total

    return None


def analyzeTraffic(capture):
    frameCounter = {}

    capture = rdpcap(capture)

    for frame in capture:
        if(hex(frame[Ether].type) == "0xff00"):   # MTP (data)
            payload = frame[Raw].load

        elif(hex(frame[Ether].type) == "0x806"): # ARP (leading zero in ethertype removed by Scapy [0x0806])
            payload = frame[Padding].load

        else:
            sys.exit("Can't find a payload")

        payloadContent = payload.split("|")
        source = payloadContent[0]
        newSeqNum = int(payloadContent[1])

        if source not in frameCounter:
            # Updated Sequence Number, List of missed frames, Total number of frames sent, list of out of order frames, lost of duplicate frames
            frameCounter[source] = [newSeqNum, [], 1, [], []]

        else:
            currentSeqNum = frameCounter[source][0]          # The current sequence number for the source address
            expectedNextSeqNum = frameCounter[source][0] + 1 # The next expected sequence number for the source address

            if(currentSeqNum == newSeqNum and newSeqNum == 1): # NEW STUFF TO STOP ONE OFFS
                continue

            if(newSeqNum in frameCounter[source][1]):          # NEW STUFF TO LOOK FOR OUT OF ORDER FRAMES
                frameCounter[source][1].remove(newSeqNum)
                frameCounter[source][3].append(newSeqNum)
                frameCounter[source][2] += 1
                continue

            if(newSeqNum not in frameCounter[source][1] and (newSeqNum < currentSeqNum or newSeqNum == currentSeqNum)): # NEW STUF TO LOOK FOR DUPLICATES
                frameCounter[source][4].append(newSeqNum)
                frameCounter[source][2] += 1
                continue

            missedFrames = newSeqNum - expectedNextSeqNum # get frames 1-5, get frame 10, missing 6-9
            #print("current seq num: {0} | expected next seq num: {1} | new seq num: {2} |missing frames: {3}".format(currentSeqNum, expectedNextSeqNum, newSeqNum, missedFrames))
            # good:       new seq num: 1292 | current seq num: 1274 | expected next seq num: 1275 | missing frames: 17
            # bad:        new seq num: 2026 | current seq num: 2025 | expected next seq num: 2026 | missing frames: 0 - new seq num is the problem here
            # bad part 2: new seq num: 3243 | current seq num: 3242 | expected next seq num: 3243 | missing frames: 0
            while(missedFrames != 0):
                missingSeqNum = currentSeqNum + missedFrames
                frameCounter[source][1].append(missingSeqNum)
                missedFrames -= 1

            frameCounter[source][0] = newSeqNum # Update the current sequence number
            frameCounter[source][2] += 1        # Update how many frames we have received from this source in total

    f = open("trafficResult.txt", "w+")
    for source in frameCounter:
        endStatement = "{0} frames lost from source {1} {2} | {3} received | {4} Not sequential {5} | {6} duplicates {7}\n"
        outputMissingFrames = ""
        outputUnorderedFrames = ""
        outputDuplicateFrames = ""

        if(frameCounter[source][1]):
            frameCounter[source][1].sort()
            outputMissingFrames = frameCounter[source][1]

        if(frameCounter[source][3]):
            frameCounter[source][3].sort()
            outputUnorderedFrames = frameCounter[source][3]

        if(frameCounter[source][4]):
            frameCounter[source][4].sort()
            outputDuplicateFrames = frameCounter[source][4]

        f.write(endStatement.format(len(frameCounter[source][1]), source, outputMissingFrames, frameCounter[source][2], len(frameCounter[source][3]), outputUnorderedFrames, len(frameCounter[source][4]), outputDuplicateFrames))

    f.close()

    return None


def getTrafficInfo(args):
    dstPhysicalAddr = "None" # Data-Link Layer destination address (almost always 802.3 MAC address)
    dstLogicalAddr = "None"  # Network Layer destination address (almost always IPv4 address)

    if(args.node):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'addrInfo.cnf').replace("\\", "/")) as fp:
            config = ConfigParser.ConfigParser()
            config.readfp(fp)
            dstPhysicalAddr = config.get(args.node, "l2address")
            dstLogicalAddr = config.get(args.node, "l3address")
    else:
        dstPhysicalAddr = args.MAC
        dstLogicalAddr = args.IPv4

    return dstPhysicalAddr, dstLogicalAddr

if __name__ == "__main__":
    main()
