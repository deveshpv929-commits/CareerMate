SET NAMES utf8mb4;

-- CareerMate: knowledge-base seed content for mentor_knowledge_base
-- Safe to re-run: a row is skipped if an entry with the same title already exists.
-- Requires: mentor_tables_migration.py has been run (table + `keywords` column).

INSERT INTO mentor_knowledge_base (category, title, keywords, answer_text)
SELECT category, title, keywords, answer_text FROM (
-- [Cybersecurity Fundamentals] What is the CIA triad in cybersecurity
SELECT 'Cybersecurity Fundamentals' AS category, 'What is the CIA triad in cybersecurity' AS title, 'cia triad, confidentiality integrity availability, confidentiality, integrity, availability, core principles of cybersecurity, infosec principles, cia goals, cia model' AS keywords, 'The CIA triad is the foundation model of information security. Every security control, and every attack, can be described by which of its three goals it protects or breaks.

1. Confidentiality - only authorised people can read the data (encryption, access control, multi-factor authentication).
2. Integrity - data is accurate and has not been changed without authorisation (hashing, digital signatures, file integrity monitoring).
3. Availability - systems and data can be used when needed (backups, redundancy, DDoS protection, patching).

Example: ransomware attacks availability, a data leak attacks confidentiality, and silently editing a bank record attacks integrity. When you analyse any incident, ask which of the three was affected.' AS answer_text
UNION ALL
-- [Cybersecurity Fundamentals] What is the difference between a threat, a vulnerability and a risk
SELECT 'Cybersecurity Fundamentals', 'What is the difference between a threat, a vulnerability and a risk', 'threat vs vulnerability, difference between threat vulnerability risk, vulnerability, threat, risk, exploit, cve, cvss, risk assessment, risk formula, likelihood and impact, risk calculated, how risk is calculated', '- Threat: anything that could cause harm, such as an attacker, malware or a natural disaster.
- Vulnerability: a weakness a threat can use, such as unpatched software, a default password or a misconfigured server.
- Exploit: the code or technique that takes advantage of a vulnerability.
- Risk: the chance that a threat uses a vulnerability, combined with the impact if it does (risk = likelihood x impact).

Example: an outdated web server (vulnerability) plus attackers scanning the internet (threat) creates the risk of a data breach.

Known vulnerabilities are catalogued with CVE IDs and scored with CVSS from 0 to 10. Teams reduce risk by patching, hardening configurations, limiting access and monitoring for abuse.'
UNION ALL
-- [Cybersecurity Fundamentals] What are the common types of cyber attacks
SELECT 'Cybersecurity Fundamentals', 'What are the common types of cyber attacks', 'types of cyber attacks, common cyber attacks, common attacks, phishing, social engineering, malware, ransomware, brute force attack, credential stuffing, sql injection, xss, cross site scripting, man in the middle, mitm, ddos, denial of service, owasp top 10', 'Common attacks you should be able to recognise:

1. Phishing and social engineering - tricking people into giving up credentials or running malware, usually through email, SMS or fake websites.
2. Malware and ransomware - malicious software; ransomware encrypts files and demands payment.
3. Brute force and credential stuffing - guessing passwords or reusing leaked ones.
4. SQL injection - sending SQL through input fields to read or change a database. Prevent it with parameterised queries.
5. Cross-site scripting (XSS) - injecting JavaScript into pages that other users view.
6. Man-in-the-middle (MITM) - intercepting traffic between two parties. HTTPS/TLS protects against it.
7. Denial of service (DoS/DDoS) - flooding a service so real users cannot reach it.

The OWASP Top 10 is the best next resource for web application attacks.'
UNION ALL
-- [Cybersecurity Fundamentals] What is the difference between encryption and hashing
SELECT 'Cybersecurity Fundamentals', 'What is the difference between encryption and hashing', 'encryption vs hashing, difference between encryption and hashing, encryption, hashing, hash, symmetric encryption, asymmetric encryption, public key, private key, aes, rsa, sha256, md5, salt, bcrypt, password hashing, store passwords, passwords stored, how passwords are stored', 'Encryption is two-way: data is scrambled with a key and can be recovered by anyone holding the right key. Hashing is one-way: data is turned into a fixed-length fingerprint that cannot be reversed.

- Symmetric encryption uses one shared key (for example AES). It is fast and used for bulk data.
- Asymmetric encryption uses a public/private key pair (RSA, ECC). It is used for key exchange, TLS and digital signatures.
- Hashing (SHA-256 and similar) verifies integrity, such as checking a downloaded file. For passwords use slow, salted algorithms like bcrypt, scrypt or Argon2, never plain MD5 or SHA-1.

Rule of thumb: if you need the original data back, encrypt it. If you only need to compare or verify it, hash it.'
UNION ALL
-- [Core Networking] What is the OSI model and what are its seven layers
SELECT 'Core Networking', 'What is the OSI model and what are its seven layers', 'osi model, osi layers, seven layers, 7 layers of osi, network layers, tcp ip model, layer 1, layer 2, layer 3, layer 4, application layer, transport layer, network layer, data link layer, physical layer', 'The OSI model splits network communication into seven layers, from top to bottom:

7. Application - what users and programs use (HTTP, DNS, SMTP)
6. Presentation - encoding and encryption (TLS, JPEG)
5. Session - starting, maintaining and ending sessions
4. Transport - end-to-end delivery and ports (TCP, UDP)
3. Network - addressing and routing (IP, routers)
2. Data Link - local delivery (Ethernet, MAC addresses, switches)
1. Physical - cables and radio signals (Wi-Fi)

Memory aid for 7 to 1: All People Seem To Need Data Processing.

Troubleshooting tip: start at layer 1 (is it plugged in?) and work upward. In practice the simpler four-layer TCP/IP model is used (Link, Internet, Transport, Application). Security tools map to layers too: ordinary firewalls work mainly at layers 3-4, web application firewalls at layer 7.'
UNION ALL
-- [Core Networking] What is the difference between TCP and UDP
SELECT 'Core Networking', 'What is the difference between TCP and UDP', 'tcp vs udp, difference between tcp and udp, tcp, udp, three way handshake, syn ack, reliable transport, connectionless, transport protocols', 'Both are transport-layer protocols that carry data between applications using ports, but they make different trade-offs.

| Feature | TCP | UDP |
|---|---|---|
| Connection | Connection-oriented (three-way handshake: SYN, SYN-ACK, ACK) | Connectionless |
| Reliability | Acknowledges data, retransmits losses, keeps order | No guarantees |
| Speed | Slower, more overhead | Faster, low overhead |
| Typical uses | Web (HTTP/HTTPS), email, SSH, file transfer | DNS queries, video calls, streaming, online games |

Use TCP when every byte must arrive correctly. Use UDP when speed matters more than perfect delivery. In security, SYN floods abuse the TCP handshake, while UDP is often abused for amplification DDoS attacks.'
UNION ALL
-- [Core Networking] What is DNS and how does it work
SELECT 'Core Networking', 'What is DNS and how does it work', 'dns, what is dns, how dns works, dns resolution, domain name system, dns records, a record, aaaa record, cname, mx record, ns record, txt record, nslookup, dig, name server, dns server', 'DNS (Domain Name System) translates human-friendly names such as example.com into IP addresses, like a phone book for the internet.

How a lookup works:
1. Your device checks its own cache, then asks its configured recursive resolver (from your ISP, router or a public one).
2. If the resolver does not know the answer it asks a root server, then the TLD server (.com), then the domain''s authoritative name server.
3. The IP address is returned and cached for the record''s TTL.

Common record types: A (IPv4 address), AAAA (IPv6 address), CNAME (alias), MX (mail server), NS (name server), TXT (text, often used for SPF and verification).

Try it with `nslookup example.com` or `dig example.com`. Security note: DNS spoofing, cache poisoning and DNS tunnelling are real attack techniques, so DNS logs are valuable in investigations.'
UNION ALL
-- [Core Networking] What are IP addresses, subnets and CIDR notation
SELECT 'Core Networking', 'What are IP addresses, subnets and CIDR notation', 'ip address, ip addressing, ipv4, ipv6, subnet, subnetting, subnet mask, cidr, cidr notation, slash 24, private ip, public ip, private ip ranges, gateway, network address, broadcast address', 'An IP address identifies a device on a network. IPv4 uses 32 bits written as four numbers (192.168.1.10). IPv6 uses 128 bits.

A subnet mask (or CIDR prefix) splits an address into a network part and a host part. CIDR writes this as a slash number: 192.168.1.0/24 means the first 24 bits are the network, which equals the mask 255.255.255.0 and gives 256 addresses (254 usable hosts, because the first is the network address and the last is the broadcast address). Each extra bit halves the size: /25 gives 128 addresses, /26 gives 64.

Private ranges (not routable on the internet): 10.0.0.0/8, 172.16.0.0/12 and 192.168.0.0/16. Everything else is public. Your default gateway is the router that sends traffic to other networks.

Check your own settings with `ip a` on Linux or `ipconfig` on Windows.'
UNION ALL
-- [Core Networking] What are common network ports and protocols
SELECT 'Core Networking', 'What are common network ports and protocols', 'common ports, network ports, port numbers, well known ports, protocols, http port, https port 443, ssh port 22, ftp, smtp, rdp port 3389, port 80, port 53, port 445, smb, telnet, port scanning, nmap', 'A port is a number (0-65535) that tells the operating system which application should receive incoming traffic. Ports you should memorise:

| Port | Protocol | Purpose |
|---|---|---|
| 20/21 | FTP | File transfer (unencrypted) |
| 22 | SSH / SFTP | Secure remote login and file transfer |
| 23 | Telnet | Remote login (unencrypted, avoid) |
| 25 | SMTP | Sending email |
| 53 | DNS | Name resolution |
| 67/68 | DHCP | Automatic IP assignment |
| 80 | HTTP | Web traffic |
| 110 / 143 | POP3 / IMAP | Receiving email |
| 443 | HTTPS | Encrypted web traffic |
| 445 | SMB | Windows file sharing |
| 3306 | MySQL | Database |
| 3389 | RDP | Windows remote desktop |

Security relevance: every open port is a possible entry point. Admins close unused ports with a firewall, and testers use tools like Nmap to discover which ports are open. Only scan systems you own or have written permission to test.'
UNION ALL
-- [Linux Commands] What are the essential Linux commands for navigating and managing files
SELECT 'Linux Commands', 'What are the essential Linux commands for navigating and managing files', 'linux commands, basic linux commands, essential linux commands, ls, cd, pwd, cp, mv, rm, mkdir, touch, cat, less, head, tail, navigate files, file management, linux terminal, command line basics', 'Core commands for moving around and managing files:

- `pwd` - show the current directory
- `ls -la` - list files, including hidden ones, with details
- `cd /path`, `cd ..`, `cd ~` - change directory (absolute path, up one level, home)
- `mkdir dir` / `touch file` - create a directory / an empty file
- `cp src dest` - copy (`-r` for directories)
- `mv src dest` - move or rename
- `rm file` / `rm -r dir` - delete (there is no recycle bin, so double-check before using `-r`)
- `cat file` - print a file; `less file` - scroll through it
- `head -n 20 file` / `tail -n 20 file` - first / last lines; `tail -f file` follows a log live
- `man command` or `command --help` - read the manual

Practice in a safe folder and avoid running `rm -rf` as root. Use Tab to auto-complete and the Up arrow to repeat commands.'
UNION ALL
-- [Linux Commands] How do Linux file permissions work with chmod and chown
SELECT 'Linux Commands', 'How do Linux file permissions work with chmod and chown', 'linux permissions, file permissions, chmod, chown, chgrp, rwx, read write execute, permission 755, permission 644, numeric permissions, octal permissions, sudo, root user, owner group others, ls -l', 'Run `ls -l` and you will see something like `-rwxr-xr-- 1 alice dev 120 Jan 5 notes.sh`. The first column has three groups of rwx for the owner, the group and everyone else (others): r = read (4), w = write (2), x = execute (1).

Numeric modes add the values per group:
- `chmod 755 file` - owner rwx, group r-x, others r-x (typical for scripts and programs)
- `chmod 644 file` - owner rw-, group r--, others r-- (typical for documents)
- `chmod 600 file` - owner only (use for SSH private keys)
- `chmod +x script.sh` - make a file executable
- `chown user:group file` - change owner and group

`sudo` runs one command with administrator (root) rights. Follow least privilege: give only the access that is actually needed, and avoid `chmod 777`, which lets everyone modify the file.'
UNION ALL
-- [Linux Commands] How do I search for files and text in Linux using grep and find
SELECT 'Linux Commands', 'How do I search for files and text in Linux using grep and find', 'grep, find, search files linux, search text in files, grep command, find command, locate, egrep, pipe, pipes, redirect, awk, sed, sort, uniq, wc, text processing, filter output', 'Searching files and filtering output is the most useful Linux skill for security work.

- `grep "text" file` - lines containing the text
- `grep -i` ignore case, `-n` show line numbers, `-r` search folders recursively, `-v` invert (lines NOT matching), `-c` count matches
- `grep -E "error|fail" file` - match either word using extended regex
- `find /path -name "*.log"` - find files by name
- `find /path -type f -mtime -1` - files changed in the last day
- `locate name` - fast filename search using an index

Combine commands with the pipe `|`, which feeds one command''s output into the next:
`cat access.log | grep "404" | sort | uniq -c | sort -nr | head`

That filters 404 lines, counts identical ones and shows the most frequent first. Use `>` to save output to a file and `>>` to append. `wc -l` counts lines, `awk` picks columns and `sed` edits text.'
UNION ALL
-- [Linux Commands] How do I check running processes and network connections in Linux
SELECT 'Linux Commands', 'How do I check running processes and network connections in Linux', 'linux processes, running processes, ps aux, top, htop, kill, killall, pid, process management, netstat, ss, listening ports, open ports, network connections linux, ip a, ping, curl, systemctl, check services', 'Processes:
- `ps aux` - list every running process (add `| grep name` to find one)
- `top` or `htop` - live view of CPU and memory use (press `q` to quit)
- `kill PID` - ask a process to stop; `kill -9 PID` forces it as a last resort

Network:
- `ip a` - show your interfaces and IP addresses
- `ss -tulnp` - show listening TCP/UDP ports and which program owns them (`netstat -tulnp` is the older equivalent)
- `ss -tn` - show established TCP connections
- `ping host` - test reachability
- `curl -I https://example.com` - fetch HTTP headers

Services: `systemctl status ssh`, `systemctl start|stop|restart ssh`.

Security use: an unknown process or an unexpected listening port can be a sign of compromise, so these commands are a first step when investigating a suspicious Linux machine.'
UNION ALL
-- [Python Basics] What are the basic data types and data structures in Python
SELECT 'Python Basics', 'What are the basic data types and data structures in Python', 'python data types, python basics, data structures, list, tuple, dictionary, dict, set, string, int, float, bool, python variables, mutable immutable, python lists, python dictionaries', 'Basic types: `int` (42), `float` (3.14), `str` ("text"), `bool` (True/False) and `None`.

Built-in collections:
- `list` - ordered and changeable: `skills = ["python", "sql"]`; use `skills.append("linux")`, `skills[0]`
- `tuple` - ordered and fixed: `point = (3, 4)`
- `dict` - key to value pairs: `student = {"name": "Asha", "level": 3}`; read with `student["name"]` or `student.get("age")`
- `set` - unique items only: `{1, 2, 2, 3}` becomes `{1, 2, 3}`

Python is dynamically typed, so you do not declare types. Lists, dicts and sets are mutable (changeable in place), while strings and tuples are immutable. Check a type with `type(x)`.

Dictionaries and lists are the structures you will use most when handling JSON, API responses and log data.'
UNION ALL
-- [Python Basics] How do loops and conditionals work in Python
SELECT 'Python Basics', 'How do loops and conditionals work in Python', 'python loops, for loop, while loop, if else, if else statement, if statement, if elif else, conditionals, range, enumerate, break, continue, python control flow, loop through list, iterate', 'Conditionals:
```python
score = 72
if score >= 75:
    print("Strong")
elif score >= 50:
    print("Promising")
else:
    print("Keep practising")
```
Python uses indentation (4 spaces) to mark blocks, and a colon after the condition.

Loops:
```python
for skill in ["python", "linux", "sql"]:
    print(skill)

for i in range(3):      # 0, 1, 2
    print(i)

count = 0
while count < 3:
    count += 1
```
Useful tools: `enumerate(items)` gives index and value, `break` exits a loop, `continue` skips to the next item, and a list comprehension such as `[x * 2 for x in numbers]` builds a list in one line.'
UNION ALL
-- [Python Basics] How do I define functions and handle errors in Python
SELECT 'Python Basics', 'How do I define functions and handle errors in Python', 'python functions, define function, def, return, parameters, arguments, default arguments, try except, exception handling, error handling, finally, raise, python errors, python exceptions', 'Functions:
```python
def percentage(correct, total=10):
    return round(correct / total * 100, 2)

print(percentage(7))        # 70.0
```
`def` defines the function, parameters go in brackets, `total=10` is a default value and `return` sends back a result. Good functions do one job and have clear names.

Error handling:
```python
try:
    value = int(input("Enter a number: "))
    result = 100 / value
except ValueError:
    print("That was not a number")
except ZeroDivisionError:
    print("Cannot divide by zero")
finally:
    print("Always runs")
```
Catch specific exceptions rather than a bare `except:`, so you do not hide real bugs. Use `raise ValueError("message")` to signal a problem yourself. Reading files is a common place to expect `FileNotFoundError`.'
UNION ALL
-- [Log Analysis] What is log analysis and why is it important in cybersecurity
SELECT 'Log Analysis', 'What is log analysis and why is it important in cybersecurity', 'log analysis, what is log analysis, logs, system logs, syslog, siem, event logs, windows event logs, event id 4625, event id 4624, indicators of compromise, ioc, incident investigation, log monitoring, timeline, splunk', 'Log analysis is reading and correlating the records that systems produce (who did what, when and from where) to spot problems and attacks.

Typical sources: Linux auth and syslog files, web server access logs, firewall and DNS logs, cloud audit logs and Windows Event Logs. Useful Windows event IDs include 4624 (successful logon) and 4625 (failed logon).

A basic workflow:
1. Collect logs centrally (a SIEM such as Splunk or Elastic does this at scale).
2. Normalise timestamps and fields so events can be compared.
3. Search for indicators of compromise: repeated failed logins, logins at odd hours, unexpected admin actions, unusual outbound traffic.
4. Build a timeline of events, find the earliest sign and decide on the response.

Logs are also evidence, so protect them from tampering and keep them long enough for investigations.'
UNION ALL
-- [Log Analysis] How do I detect brute force attempts in Linux authentication logs
SELECT 'Log Analysis', 'How do I detect brute force attempts in Linux authentication logs', 'auth log, auth.log, var log auth.log, var log secure, failed password, failed login attempts, brute force detection, detect brute force, ssh brute force, journalctl, lastb, last, linux authentication logs, sort uniq, failed ssh logins', 'On Debian/Ubuntu, SSH and sudo activity goes to `/var/log/auth.log`. On RHEL/CentOS it is `/var/log/secure`. A failed SSH login looks like:
`Failed password for root from 203.0.113.5 port 52114 ssh2`

Count failed attempts per source IP:
`grep "Failed password" /var/log/auth.log | awk ''{print $(NF-3)}'' | sort | uniq -c | sort -nr | head`

The IP is the fourth field from the end of that line format. Other helpful commands:
- `grep "Accepted" /var/log/auth.log` - successful logins (check these after many failures from one IP)
- `sudo lastb` - recent failed logins; `last` - successful logins
- `journalctl -u ssh --since "1 hour ago"` - systemd journal for the SSH service (the unit is `sshd` on RHEL)

Many failures from one IP in a short time suggests brute forcing. A success after many failures is a red flag. Common responses are blocking the IP, enabling fail2ban, disabling password login in favour of SSH keys and turning off direct root login.'
UNION ALL
-- [Log Analysis] How do I parse and analyse log files with Python
SELECT 'Log Analysis', 'How do I parse and analyse log files with Python', 'parse log files python, python log analysis, python regex, re module, regular expressions, counter, collections counter, read log file, parse logs, python script logs, extract ip addresses, log parsing script, automate log analysis, count failed logins with python, python failed logins', 'Python is ideal for automating log analysis: read each line, extract fields with a regular expression and count patterns.

```python
import re
from collections import Counter

pattern = re.compile(
    r"Failed password for (?:invalid user )?(\\S+) from (\\d+\\.\\d+\\.\\d+\\.\\d+)"
)
failures = Counter()

with open("/var/log/auth.log") as log_file:
    for line in log_file:
        match = pattern.search(line)
        if match:
            failures[match.group(2)] += 1

for ip, count in failures.most_common(5):
    print(ip, count)
```
How it works: `re.compile` builds the pattern once, the capture groups pull out the username and IP, and `Counter` tallies attempts per IP.

Good habits: handle `FileNotFoundError` and `PermissionError`, read line by line so large files do not fill memory, and test your regex on a few sample lines first. Next steps: parse timestamps with `datetime`, flag IPs above a threshold, and write results to CSV for reports.'
) AS new_rows
WHERE NOT EXISTS (
    SELECT 1 FROM mentor_knowledge_base kb WHERE kb.title = new_rows.title
);
