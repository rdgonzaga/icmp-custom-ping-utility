# icmp-custom-ping-utility
## Usage

```bash
py ICMP.py [host] [-c COUNT] [-t TIMEOUT]
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