# Custom Ping Utility Using ICMP
> Authors: CHIU, Lance, DESCALZO, Alberto, GONZAGA, Rainer | NSCOM02 S04

Python based tool that implements a simplified version of the standard `ping` utility using ICMP Echo Request and Reply messages via Raw Sockets. It measures the round-trip time (RTT) and packet loss between the client and a destination host. The tool also implements two bonus features: an end-of-session RTT summary (min/avg/max and packet loss rate) and parsing of ICMP error responses (e.g. Destination Unreachable, TTL Expired) when an Echo Reply is not received.

## Requirements & Usage
* Python 3.6+

1. Open a terminal (Command Prompt, PowerShell, or bash) with Administrator/root privileges.
2. Run the script:
   ```bash
   python ICMP.py [host] [-c COUNT] [-t TIMEOUT]
   ```

| Argument | Description | Default |
|---|---|---|
| `host` | Hostname or IP address to ping | `127.0.0.1` |
| `-c`, `--count` | Number of ping requests to send. Use `0` for infinite pinging. | `4` |
| `-t`, `--timeout` | Timeout per request in seconds | `2` |

## Sample Output

```text
Pinging 142.250.199.206 using Python:

Reply from 142.250.197.110: seq=1 time=29.206 ms
Reply from 142.250.197.110: seq=2 time=27.928 ms
Reply from 142.250.197.110: seq=3 time=27.853 ms
Reply from 142.250.197.110: seq=4 time=28.807 ms

--- google.com ping statistics ---
4 packets transmitted, 4 received, 0.0% packet loss
rtt min/avg/max = 27.853 / 28.448 / 29.206 ms
```

## Troubleshooting (Windows)

Windows is generally stateful about ICMP echo traffic, so replies to your own outbound Echo Requests are usually let back in without extra configuration. On more restrictive setups (public network profiles, certain VPNs/routers, or a locked-down Windows Defender Firewall policy), inbound ICMPv4 traffic may still be dropped, causing every request to time out.

If your pings are all timing out even against `127.0.0.1` or a known-reachable host, either temporarily disable the firewall or add an exception to allow inbound ICMPv4 traffic.

One can do this either through Control Panel or the ff. netsh command:
```cmd
netsh advfirewall firewall add rule name="Allow ICMPv4-In" protocol=icmpv4:any,any dir=in action=allow
```


## Declaration of Tools and AI Use

1. **Anthropic Claude**
2. **ChatGPT 5.5**

All LLMs used for providing step-by-step tutoring on network programming concepts, structuring the project workflow, explaining ICMP protocol mechanics, clarifying the RTT and ICMP error parsing requirements, and conducting iterative code reviews and debugging. All AI-generated outputs were reviewed, edited, and validated; we maintain full intellectual ownership and take complete responsibility for the final accuracy, functionality, and integrity of this submission.

### AI Prompts Used

1. *"Act as an Expert Network Programming Tutor and Senior Software Engineer... Guide me step-by-step through completing my 'Custom Ping Utility Using ICMP' project. I have a Python skeleton code file that I need to complete, but under no circumstances should you provide the complete, solved code. Instead, break the project down into a logical To-Do list and guide me through one specific `#Fill in start` block at a time, explaining the underlying networking logic and ICMP mechanics before we write any code."*
2. *"What is the 'latin-1' solution you suggested in the checksum function, and why should I use it to make my program work?"*
3. *"Why are originalCode and originalChecksum unused here? Can I safely remove them?"*
4. *"Would it be safer to calculate the IP header length instead of hard coding it to byte 20?"*
5. *"Can you run me down on the objectives for the RTT summary stats and ICMP error parsing?"*  