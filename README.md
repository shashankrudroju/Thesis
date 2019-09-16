# Automating Meshed Tree Protocol (MTP) Research Functions
*For more info on MTP, see IEEE Project 1910.1 - Standard for Meshed Tree Bridging with Loop Free Forwarding*

For the purposes of researching into the effectiveness of the Meshed Tree Protocol on the GENI Testbed, automation/orchestration is utilized to create repeatability in testing. These automation techniques also significantly speed up the process of getting the protocol implementation up and running on a large topology within GENI. All of the scripts are currently written in Python and take advantage of the Paramiko SSH library.

Current testing is being done to port these scripts to Ansible, stay tuned for more information on that development!

### Requirements to Run the Automation Scripts
1. A local Linux distribution (Has been tested on Ubuntu 16.04 and 18.04)
2. Python 2.7
3. Python Pip and the Paramiko library
4. A valid GENI slice with multiple nodes
5. The GENIutils module in the same directory as the scripts (contains functions written to interact with GENI nodes)

### To Install the Dependencies Needed to Run the MTP Automation Scripts
1. Install Python via your package manager if it isn't already there (example for Debian systems using APT: sudo apt-get install python2.7)
2. Grab the files needed to install Pip if it isn't already there (curl -O https://bootstrap.pypa.io/get-pip.py)
3. Install Pip (python get-pip.py --user)
4. Make sure your PATH environment is updated for Pip (export PATH="/[your home path]/.local/bin:$PATH")
5. Install Paramiko via Pip (pip install --user paramiko --upgrade --ignore-installed)

### MTP_RSPEC.xml: Contains Information about the GENI nodes
This file needs to be updated with the current GENI topology whenever a new topology is being used. You can grab the content needed for this file by going to the slice in the GENI GUI, hitting the *View Rspec* button, and copying what is in there into the *MTP_RSPEC.xml* file.

## Running the MTP Automation Scripts

### MTPConfig.py: Getting a GENI slice ready for the Meshed Tree Protocol
Just run the script and relax (because you'll be waiting a while for everything to finish). This installs necessary dependencies for proper MTP testing.
  1. Packages are updated
  2. Python Pip is installed
  3. Chrony (a time server) is installed and configured. Google's time servers (time.google.com) are used for synchronization.
  4. TShark is installed (packet capture software)
  5. Scapy is installed (raw packet creation and collection software)

### MTPStart.py: Starting the MTP Implementation on GENI Nodes
This is the script that transfer all of the MTP implementation code as well as support scripts and then allows the MTP implementation to begin running on the node. When it is first started, a prompt will appear with three options: transfer the MTP implementation source code to the bridge nodes (1), transfer the Traffic Generator code to the client nodes (2), or start the MTP implementation on the GENI nodes (3).

If (3) is selected, two prompts will appear that ask what time MTP should start. For testing purposes, you should start the root MTS ~5 seconds before the other MTS' to make sure that the root idles and the non-root MTS' are forced to initiate the joining process. This is more akin to what would actually be happening and gives us a better idea of convergence timing. What follows will be the commands to be processed on each node, and if they were successful or not. A failure doesn't always mean something is wrong or the test failed, just look at the command and if the failure makes sense.

A major part of this script is the utilization of the **GNU Screen** software. GNU Screen is a terminal multiplexer that allows users to define additional virtual consoles within a single SSH session (and terminal window, as a result). It is a separate entity from the main terminal information, so everything inside of a GNU Screen session happens independently of what is occurring otherwise. The MTP implementation is run inside of a GNU Screen so that it has its own environment to output to the console, which allows the user to do other tasks on the system while it runs and also allows anything printed on the GNU Screen to be recorded.

To check to see what is happening on the MTS', connect to one of your GENI nodes via SSH and get into its GNU Screen session (see description above). A couple of commands can be used to interact with the MTP screen session (more can be used in the script to modify its behavior from the beginning):
  1. **screen -list** - outputs the list of screens created. If the script was successful, you should see one that mentions an MTS/whatever you modified the name to be in the script. If there is more than one MTP screen, **you have a problem**. Run **pkill screen** to kill all of the screens and rerun the script once all nodes have had their screens stopped.
  2. **screen -r** - Places you inside of the screen, which should contain MTP info. If multiple screens are present, this will require the screen name via the *-S* argument, but that may mean you have too many screens right now.
  3. Once you are inside of the screen, you can return back to the main console via **Ctrl + A and then D**. If you need to scroll up on the screen window, use **Ctrl + A and then Esc**. **Do not use Ctrl + C while in the screen, it will kill the screen and your MTP implementation will stop**.

### MTPStop.py: Stopping the MTP Implementation on GENI Nodes
This script simply connects to each GENI node and runs a screen command (*screen -X quit*) to stop the screen, thus stopping the MTP implementation.

### MTPCollection.py: Grabbing Information About the MTP Implementation on the GENI Nodes (old)
A legacy script for the older method of collecting convergence and/or logging information. It should only be used now for outputting the MTP implementation console output. use the "-help" argument to get a list of options.

 The output log file for "*--MSTC*" will contain the MSTC convergence time (in microseconds) at the bottom. Above that will be a microsecond timestamp for each VID that was received and then an absolute time it was received. The first entry from each node is what goes into the initial convergence calculation, as the creation of first tree will enable frame forwarding.

 The output log file for "*--failure [node name]*" will contain information regarding the removal of VIDs from each node, and then more specific information for the node where a link was broken. Below that will be the starting time, which is the time that the link was broken, and then a collection of VIDs, along with the time (in microseconds) it took to remove that VID. The time farthest from the start is the re-convergence time. Utilized with this is the **faillink** script in the Code directory, which is used to break a link on a node and record the timing information in the link failure log file. To use this file, simply run *sudo faillink ethX*, where X is the interface number you wish to break.

 The log file for *--output* will contain the last MTP table printouts found when running the protocol.

### MTPConvergence.py: Grabbing Information About the MTP Implementation on the GENI Nodes (new)
The current method of determining MTP implementation functionality. An MTP implementation will produce a log file called **mtpd.log**, which contains information about table additions/deletions, failures, etc. When it is first started, a prompt will appear with two options: collect the logged data (1) or use log data to analyze performance (2).

If (1) is selected, simply give a name to the test (example: Node1Eth3Down) and a directory will be created in your local directory with the name **MTP_Test_[test-name]**. Inside will be a directory for each node, and inside each node directory will be logging files. If (2) is selected, give the name of the test (**MTP_Test_[test-name]**) and observe that a comma-separated variable file (.csv) is created in the local directory with the analysis results. You may view it as is, or open it in spreadsheet software for a more clean look.


## Running the RSTP Automation Scripts

### RSTPConfig.py: Getting a GENI slice ready for the Rapid Spanning Tree Protocol
**See the MTPConfig.py section above for an explaination**. Open vSwitch (OVS) is installed on bridge nodes in addition to the other tasks.

### RSTPTopologyInfo.py: Get the status of the RSTP topology
A script that outputs a file (RSTPTopology.txt) with the current port status and role of each bridge node in the slice. Good for comparing before and after a failure.

### RSTPStart.py + RSTPStop.py: Starting and Stopping the RSTP Implementation
Same idea as the MTP start and stop scripts, except you just run them as is. OVS is always running on the bridge nodes, so you just have to start and stop the logging process

### RSTPBreakLink.py: Fail/bring back a bridge interface remotely
Remotely takes down or brings back up an interface on a GENI node. To run: **RSTPBreakLink.py [UP/DOWN][NODE][INTERFACE]**

### RSTPCollection.py: Grabbing Information About the RSTP Implementation on the GENI Nodes
**See the MTPConvergence.py section, option 1, above for an explanation of the collection script**. Instead of waiting for a prompt, argument the script with the test name.
**See the MTPConvergence.py section, option 2, above for an explanation of the convergence script**. Instead of waiting for a prompt, argument the script with the test directory name.


## Client Traffic Generation

### trafficgenerator.py: Traffic generator (IEEE 802.3 and TCP/IP Protocol Suite) for switch testing purposes
This script is dense with a bunch of features, use **-help** to show all of the argument options. Traffic is created and sent or received and analyzed. To summarize:
  1. Sending Broadcast Traffic: -b [ARP/MTP_bcast]
  2. Sending Unicast Traffic: use -n [node-name] or -m [MAC] -i [IPv4] along with -u [ICMP/MTP_ucast] **See the nodeInfo.py section for -n option**
  3. Receiving Traffic: -r [ARP/ICMP/MTP_bcast/MTP_ucast]
  4. Analyzing Traffic Loss: -a [results.pcap]

### nodeInfo.py: Node name to L2 + L3 addressing generator
To make using trafficgenerator.py easier for client nodes, this script creates a configuration file of each client node in the topology and their address information at the Data-Link and Network layer. The resulting file is sent along with trafficgenerator.py to clients so that the **-n** argument in trafficgenerator.py can be used by just inputting a name. For example: **-n endnode-1**
