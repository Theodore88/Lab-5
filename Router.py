import sys
import threading
import time
from socket import *
import json
import copy

routerID = sys.argv[1]
routerID = int(routerID)
routerPort = sys.argv[2]
configFile = sys.argv[3]

lines_list = []
with open(configFile, 'r') as file:
    for line in file:
        if line.strip() != '':
            lines_list.append(line.strip())

numNodes = int(lines_list[0])

sendRouterPorts = [] # array of ports to send to (neighbor ports)
linkState = [999] * numNodes # linkstate for current router, init all costs to 999 for now
linkState[int(routerID)] = 0 # cost to itself is 0
for line in lines_list[1:]:
    sendRouterPorts.append(int(line.split()[-1]))
    linkState[int(line.split()[1])] = int(line.split()[2]) # update cost based on config file

# Now have linkstate of current node and all the ports of neighboring nodes


routerInfo = {} # dictionary, key = router label, value = cost to neighbors

def sendLinkStateInfo(): # Every second send link state information 
    while True:
        sendSocket = socket(AF_INET, SOCK_DGRAM)
        for port in sendRouterPorts:
            data_to_send = json.dumps(linkState)
            sendSocket.sendto(data_to_send.encode(),('localhost', port))

        time.sleep(1)  # send every second


def receiveLinkStateInfo(routerPort):# Upon receiving a link state brodcast from a neighbor, router record info and forward copy of received info to neighbors
    receiveSocket = socket(AF_INET, SOCK_DGRAM)
    # Assign IP address and port number to socket
    receiveSocket.bind(("", routerPort))
    while True:
        message, address = receiveSocket.recvfrom(1024)
        received_data = json.loads(message.decode('utf-8')) # recived data is link state for a router
        
        # record info
        for inx, element in enumerate(received_data): # find which router this is link state for
            if element == 0: # now have index/node ID of the sending router
                if inx not in routerInfo: # if I have NOT already received link state for this router than add to dictionary
                    # Take linkstate for sending router and put in dictionary
                    routerInfo[inx] = received_data

        # brodcast link state from sending routers to neighbors
        sendSocket = socket(AF_INET, SOCK_DGRAM)
        for port in sendRouterPorts:
            data_to_send = json.dumps(received_data)
            sendSocket.sendto(data_to_send.encode(),('localhost', port))
        

def computePathAndTable():
    """
    Every 10 sec compute least cost paths based on dijstra algorithm using whole network topology, wait 10 sec if don't 
    have whole network topology.Each time after execution of dijkstra, build forwarding table for router  
    """
    while True:    # check if have entire topology
        if len(routerInfo)!=numNodes-1:
            print("Do not have all link state information")
            
        else:
            # implementing Dijkstra
            linkStateCopy = linkState.copy() # create copy of link state that will only be used in dijkstra. Don't want to manipulate link state cause still sending to other instances
            LCPKnown = {(routerID,routerID):0} # list of nodes that have least cost path definitively figured out, also store cost to get there
            # In LCPKnown store the current router
            linkStateCopy[routerID] = 9999 # no longer want to consider this router

            indexMin =  linkStateCopy.index(min(linkStateCopy)) # provide the id of neighbor router with lowest cost
            LCPKnown[(indexMin,routerID)] = (min(linkStateCopy)) # for current router append smallest value in link state
            linkState[indexMin] = 9999 # no longer want to consider this router in algorithm
           
           # currently have router itself and least cost neighbor added to LCPKnown
            while len(LCPKnown)<numNodes:
                nextLinkState = routerInfo[indexMin] # look at link state of last min node
                result = [] # has min for all routers between direct route and route through previous min router
                
                for i in range(numNodes): # look at all nodes and find least cost path to them. considering direct path and path through min router
                    
                    # id is dest, indexMin is ID of last lowest cost node to travel to 
                    if linkStateCopy[i] < 9999: # if this node is still one we are considering

                        leastCost = min(linkStateCopy[i], linkStateCopy[indexMin] + nextLinkState[i]) # check if shortest path is direct or through min router
                        if leastCost == linkStateCopy[i]: # least cost path is direct
                            result.append((linkStateCopy[i], i)) # store cost then ID of predecessor node 
                        
                        else: # least cost path is from previous min node
                            result.append((linkStateCopy[indexMin] + nextLinkState[i], indexMin))

                    else:
                        result.append((9999,9999))

                resultCosts = [t[0] for t in result]
                previousNodes = [t[1] for t in result]
                indexMin = resultCosts.index(min(resultCosts))
                LCPKnown[(indexMin, previousNodes[indexMin])] = min(resultCosts)
                linkStateCopy[indexMin] = 9999 # no longer consider calculating least cost path for router

            # print result of Dijksta
            print('Destination Router ID\t Distance\t Previous Node ID')
            for key, value in LCPKnown.items():
                print(f'{key[0]}\t {value}\t {key[1]}')
            
            # print forwarding
            print("Destination Route ID\t Next Hop Router Label")
            print(LCPKnown)
            for key, value in LCPKnown.items():
                if value != 0:
                    nextHopId = key[1] # predeccesor node
                    while linkState[nextHopId] != 999: # next hop is not direct neighbor with current router
                        # find predeccesor node of next hop
                        keys = LCPKnown.keys()
                        for key in keys:
                            if len(key) > 1 and key[0] == nextHopId:
                                nextHopId = key[1]
                                break

                        
                    nextHopLabel = chr(ord('a') + nextHopId[0])
                    print(f'{key[0]}\t {nextHopLabel}')

        time.sleep(10)

# sendLinkStateInfo()
# receiveLinkStateInfo(int(routerPort))

if True:
    # Create threads
    thread1 = threading.Thread(target=sendLinkStateInfo)
    thread2 = threading.Thread(target=receiveLinkStateInfo, args=(int(routerPort), ))
    thread3 = threading.Thread(target=computePathAndTable)


    # Start threads
    thread1.start()
    thread2.start()
    thread3.start()

    # Wait for all threads to finish
    thread1.join()
    thread2.join()
    thread3.join()

