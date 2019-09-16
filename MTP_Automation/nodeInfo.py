#!/usr/bin/env python
import ConfigParser
from xml.dom import minidom
from GENIutils import *

def main():
    getMACAddrs("MTP_RSPEC.xml")
    test = buildDictonary("MTP_RSPEC.xml")
    print(test)

    return None

def getMACAddrs(rspec):
    endNodeNamingSyntax = getConfigInfo("MTP Utilities", "endNodeName")
    rspec = minidom.parse(rspec)
    listOfNodes = rspec.getElementsByTagName("node")
    nodeStuff = {}

    for node in listOfNodes:
        nodeName = (node.attributes["client_id"]).value
        listOfNodes = rspec.getElementsByTagName("node")

        if(endNodeNamingSyntax in nodeName):
            nodeStuff[nodeName] = []
            nodeContent = node.childNodes

            for nodeTest in nodeContent:
                if(str(nodeTest.nodeName) == "interface"):
                    nodeStuff[nodeName].append(nodeTest.attributes["mac_address"].value)

                    ipContent = nodeTest.childNodes
                    for ipTest in ipContent:
                        if(str(ipTest.nodeName) == "ip"):
                            nodeStuff[nodeName].append(ipTest.attributes["address"].value)


    config = ConfigParser.ConfigParser()

    for key in nodeStuff:
        macAddr = ':'.join(s.encode('hex') for s in nodeStuff[key][0].decode('hex')) # first index postion is the MAC address, adding ":"
        ipAddr = nodeStuff[key][1]  # second index position is the IP address

        config.add_section(key)
        config.set(key, "L2Address", macAddr)
        config.set(key, "L3Address", ipAddr)

    # Making a dummy one so everyone can get the clients going
    config.add_section("endnode-generic")
    config.set("endnode-generic", "L2Address", "01:02:03:04:05:06")
    config.set("endnode-generic", "L3Address", "10.10.100.1")

    with open('addrInfo.cnf', 'wb') as configfile:
        config.write(configfile)

    return None


if __name__ == "__main__":
    main()
