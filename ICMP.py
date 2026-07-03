from socket import *
import argparse
import os
import sys
import struct
import time
import select

ICMP_ECHO_REPLY = 0
ICMP_ECHO_REQUEST = 8
ICMP_DEST_UNREACHABLE = 3
ICMP_TIME_EXCEEDED = 11

sequence_number = 0

# Source:
# https://www.iana.org/assignments/icmp-parameters/icmp-parameters.xhtml#icmp-parameters-codes-11
# https://www.iana.org/assignments/icmp-parameters/icmp-parameters.xhtml#icmp-parameters-codes-3
ICMP_ERROR_CODES = {
    ICMP_DEST_UNREACHABLE: {
        0: "Destination Network Unreachable",
        1: "Destination Host Unreachable",
        2: "Destination Protocol Unreachable",
        3: "Destination Port Unreachable",
        4: "Fragmentation Needed and DF Set",
        5: "Source Route Failed",
        6: "Destination Network Unknown",
        7: "Destination Host Unknown",
        9: "Destination Network Administratively Prohibited",
        10: "Destination Host Administratively Prohibited",
        13: "Communication Administratively Prohibited",
    },
    ICMP_TIME_EXCEEDED: {
        0: "TTL Expired in Transit",
        1: "Fragment Reassembly Time Exceeded",
    },
}


def getICMPErrorMessage(icmpType, code):
    if icmpType in ICMP_ERROR_CODES:
        return ICMP_ERROR_CODES[icmpType].get(code, "Unknown ICMP error")
    return "Unknown ICMP error"


# Error packets include the original IP header + the first 8 bytes of the original packet.
# This lets us check if the error comes from one of our Echo Requests by checking the ID field in the original packet.
def originalPacketMatchesID(recPacket, icmpStart, ID):
    originalIPStart = icmpStart + 8

    if len(recPacket) < originalIPStart + 20:
        return False, None
    
    originalIPHeaderLength = (recPacket[originalIPStart] & 0x0F) * 4
    originalICMPStart = originalIPStart + originalIPHeaderLength

    if len(recPacket) < originalICMPStart + 8:
        return False, None
    
    originalICMPHeader = recPacket[originalICMPStart:originalICMPStart + 8]
    originalType, _originalCode, _originalChecksum, originalID, originalSequence = struct.unpack("bbHHh", originalICMPHeader)

    if originalType == ICMP_ECHO_REQUEST and originalID == ID:
        return True, originalSequence
    
    return False, None


def checksum(string):
    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0

    while count < countTo:
        thisVal = ord(string[count+1]) * 256 + ord(string[count])
        csum = csum + thisVal
        csum = csum & 0xffffffff
        count = count + 2
    if countTo < len(string):
        csum = csum + ord(string[len(string) - 1])
        csum = csum & 0xffffffff
    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer
    
    
def receiveOnePing(mySocket, ID, timeout, destAddr, sentSequence):
    timeLeft = timeout
    while 1:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if whatReady[0] == []:  # Timeout
            return {
                "message": "Request timed out for seq=%d." % sentSequence,
                "rtt": None
            }
        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)
        
        #Fill in start
        # refactored to avoid assuming header always starts at byte 20, a little unnecessary but no harm being safe.
        ipHeaderLength = (recPacket[0] & 0x0F) * 4
        icmpHeader = recPacket[ipHeaderLength:ipHeaderLength + 8]
        type, code, checksum, packetID, sequence = struct.unpack("bbHHh", icmpHeader)

        #Fetch the ICMP header from the IP packet
        if packetID == ID and type == ICMP_ECHO_REPLY:
            timeData = recPacket[ipHeaderLength + 8:ipHeaderLength + 16] # safety
            timeSent = struct.unpack("d", timeData)[0]
            rtt = (timeReceived - timeSent) * 1000

            return {
                "message": "Reply from %s: seq=%d time=%.3f ms" % (addr[0], sequence, rtt),
                "rtt": rtt
            }

        #Fill in end

        # BONUS: ICMP error response
        if type in ICMP_ERROR_CODES:
            matchesID, originalSequence = originalPacketMatchesID(recPacket, ipHeaderLength, ID)

            if matchesID:
                errorMessage = getICMPErrorMessage(type, code)
                return {
                    "message": "ICMP error from %s: %s for seq=%d [type=%d, code=%d]" %
                               (addr[0], errorMessage, originalSequence, type, code),
                    "rtt": None
                }
        
        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return {
                "message": "Request timed out for seq=%d." % sentSequence,
                "rtt": None
            }


def sendOnePing(mySocket, destAddr, ID):
    
    global sequence_number
    sequence_number += 1  # increment so each ping has a unique sequence number
    
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)
    myChecksum = 0
    
    # Make a dummy header with a 0 checksum
    # struct -- Interpret strings as packed binary data
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, sequence_number)
    data = struct.pack("d", time.time())
    # Calculate the checksum on the data and the dummy header.
    myChecksum = checksum(str(header + data, 'latin-1')) #latin 1 mapss each byte directly to its matching char

    # Get the right checksum, and put in the header
    if sys.platform == 'darwin':
        # Convert 16-bit integers from host to network byte order
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)
    
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, sequence_number)
    packet = header + data
    mySocket.sendto(packet, (destAddr, 1)) # AF_INET address must be tuple, not str
    # Both LISTS and TUPLES consist of a number of objects
    # which can be referenced by their position number within the object.


def doOnePing(destAddr, timeout):
    icmp = getprotobyname("icmp")
    # SOCK_RAW is a powerful socket type. For more details: http://sockraw.org/papers/sock_raw
    
    #Fill in start
    #create socket
    mySocket = socket(AF_INET, SOCK_RAW, icmp)
    #Fill in end
   
    myID = os.getpid() & 0xFFFF # Return the current process 
    
    #send a single ping using the socket, dst addr and ID
    #add delay using timeout
    #close socket
   
    #Fill in start
    try:
        sentSequence = sendOnePing(mySocket, destAddr, myID)
        delay = receiveOnePing(mySocket, myID, timeout, destAddr, sentSequence)
    finally:
        mySocket.close()
    #Fill in end
    
    return delay
    

def printSummary(host, packetsSent, packetsReceived, rtts):
    packetsLost = packetsSent - packetsReceived
    packetLossRate = (packetsLost / packetsSent) * 100 if packetsSent > 0 else 0

    print("")
    print("--- %s ping statistics ---" % host)
    print("%d packets transmitted, %d received, %.1f%% packet loss" %
          (packetsSent, packetsReceived, packetLossRate))

    if rtts:
        minRTT = min(rtts)
        maxRTT = max(rtts)
        avgRTT = sum(rtts) / len(rtts)
        print("rtt min/avg/max = %.3f / %.3f / %.3f ms" % (minRTT, avgRTT, maxRTT))
    else:
        print("rtt min/avg/max = N/A")


def ping(host, timeout=2, count=4): # specs 5 Assume the packet is lost if no reply is received within 2000 ms.
    # timeout=1 means: If one second goes by without a reply from the server,
    # the client assumes that either the client's ping or the server's pong is lost
    
    try:
        dest = gethostbyname(host)
    except gaierror:
        print("Could not resolve host: %s" % host)
        return []

    dataSize = struct.calcsize("d")
    countDisplay = "continuous" if count is None else str(count)

    if host == dest:
        print("Pinging %s with %d bytes of data:" % (dest, dataSize))
    else:
        print("Pinging %s [%s] with %d bytes of data:" % (host, dest, dataSize))
    print("Count: %s | Timeout: %.1f seconds" % (countDisplay, timeout))
    print("")

    packetsSent = 0
    packetsRcvd = 0
    rtts = []

    try:
        while count is None or packetsSent < count:
            result = doOnePing(dest, timeout)
            packetsSent += 1
            print(result["message"])

            if result["rtt"] is not None:
                packetsRcvd += 1
                rtts.append(result["rtt"])

            if count is None or packetsSent < count:
                time.sleep(1) # one second
    except KeyboardInterrupt: # Lets stats print even if pinging is stopped
        print("\nPing interrupted by user.")
        pass
    
    printSummary(host, packetsSent, packetsRcvd, rtts)
    return rtts


def main():
    parser = argparse.ArgumentParser(
        description="Custom ICMP ping utility with RTT summary and ICMP error parsing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  py ICMP.py google.com\n"
            "  py ICMP.py 8.8.8.8 -c 5\n"
            "  py ICMP.py 127.0.0.1 -c 0 -t 1\n\n"
            "Use -c 0 for continuous pinging until Ctrl+C."
        )
    )
    parser.add_argument(
        "host",
        nargs="?",
        default="127.0.0.1",
        help="Host or IP address to ping. Default: 127.0.0.1"
    )
    parser.add_argument(
        "-c", "--count",
        type=int,
        default=4,
        help="Number of requests to send. Default: 4. Use 0 for continuous."
    )
    parser.add_argument(
        "-t", "--timeout",
        type=float,
        default=2,
        help="Timeout per request in seconds. Default: 2."
    )

    args = parser.parse_args()

    if args.count < 0:
        parser.error("count must be 0 or greater")
    if args.timeout <= 0:
        parser.error("timeout must be greater than 0")

    count = None if args.count == 0 else args.count
    ping(args.host, timeout=args.timeout, count=count)


if __name__ == "__main__":
    main()