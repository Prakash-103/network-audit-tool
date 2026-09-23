"""
Multi-Vendor Network Device CLI Simulation Engine.
Provides authentic, high-fidelity CLI & API outputs for diverse enterprise network devices:
- Cisco 3850 & Catalyst switches (IOS-XE)
- Grandstream GWN 7803P Switches
- Grandstream Access Points (GWN 7662, 7660, 7660E)
- Meraki M44 & Cloud Dashboard API
- Sophos XGS Firewalls (SFOS)
- Arista EOS, Juniper JunOS, Fortinet FortiGate, Aruba CX, Mikrotik RouterOS
Used for serverless deployments (e.g. Vercel), sandbox demonstrations, and unreachable cloud environments.
"""
import re
from datetime import datetime
from typing import Optional, Dict, Any


class DeviceSimulationEngine:
    @staticmethod
    def generate_cli_output(
        vendor: str,
        model: str,
        hostname: str,
        command: str,
        management_ip: str = "10.254.1.1"
    ) -> str:
        v = (vendor or "cisco").lower()
        m = (model or "").lower()
        c = command.strip()
        c_low = c.lower()
        now_str = datetime.now().strftime("%b %d %H:%M:%S")

        # ── 1. CISCO 3850 / CATALYST (IOS-XE) ─────────────────────────────
        if "cisco" in v or "3850" in m or "catalyst" in m:
            if "running-config" in c_low or "run" == c_low or "show run" in c_low or c_low.startswith("show run"):
                return f"""!
! Last configuration change at {now_str} by admin
! NVRAM config last updated at {now_str} by admin
!
version 16.12
service timestamps debug datetime msec
service timestamps log datetime msec
service password-encryption
service call-home
platform punt-keepalive disable-kernel-core
!
hostname {hostname}
!
boot-start-marker
boot system flash:packages.conf
boot-end-marker
!
vrf definition Mgmt-vrf
 !
 address-family ipv4
 exit-address-family
!
aaa new-model
aaa authentication login default local
aaa authorization exec default local
!
spanning-tree mode rapid-pvst
spanning-tree extend system-id
spanning-tree vlan 1-4094 priority 24576
!
vlan internal allocation policy ascending
!
vlan 10
 name Corporate-Data
!
vlan 20
 name Voice-VLAN
!
vlan 30
 name Guest-Wireless
!
vlan 99
 name Management-VLAN
!
interface GigabitEthernet1/0/1
 description Uplink to Core Switch
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 channel-group 1 mode active
!
interface GigabitEthernet1/0/2
 description Uplink to Core Switch Redundant
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 channel-group 1 mode active
!
interface Port-channel1
 description LACP Core Uplink Trunk
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
!
interface Vlan99
 description Management IP SVI
 ip address {management_ip} 255.255.255.0
 no shutdown
!
ip default-gateway 10.254.1.1
ip forward-protocol nd
ip http server
ip http secure-server
!
ip ssh version 2
ip ssh time-out 60
ip ssh authentication-retries 3
!
line con 0
 stopbits 1
line vty 0 4
 transport input ssh
 login authentication default
line vty 5 15
 transport input ssh
 login authentication default
!
end
"""
            elif "version" in c_low:
                return f"""Cisco IOS Software, C3850 Software (CAT3K_CAA-UNIVERSALK9-M), Version 16.12.5b, RELEASE SOFTWARE (fc1)
Technical Support: http://www.cisco.com/techsupport
Copyright (c) 1986-2021 by Cisco Systems, Inc.
Compiled Wed 24-Feb-21 04:18 by prod_rel_team

ROM: IOS-XE ROMMON
{hostname} uptime is 42 weeks, 3 days, 14 hours, 28 minutes
Uptime for this control processor is 42 weeks, 3 days, 14 hours, 31 minutes
System returned to ROM by reload
System image file is "flash:cat3k_caa-universalk9.16.12.05b.SPA.bin"
Last reload reason: Reload Command

cisco WS-C3850-48P (APM86XXX) processor (revision A0) with 4194304K bytes of physical memory.
Processor board ID FOC2145ABCD
48 GigabitEthernet interfaces
4 Ten GigabitEthernet interfaces
2048K bytes of non-volatile configuration memory.
4194304K bytes of physical memory.
2097152K bytes of flash memory at bootflash:.
Base Ethernet MAC Address          : 70:69:79:AB:CD:01
Configuration register is 0x102
"""
            elif "env" in c_low:
                return f"""Switch 1 FAN 1 is OK
Switch 1 FAN 2 is OK
Switch 1 FAN 3 is OK
Switch 1 Power Supply 1 is OK (715W AC)
Switch 1 Power Supply 2 is OK (715W AC, Redundant)
System Temperature: 31 Celsius (NORMAL)
Internal Power Status: All Rails OK
PoE Status: Module 1 Total: 715W, Used: 142W, Available: 573W
"""
            elif "processes cpu" in c_low or "cpu" in c_low:
                return """CPU utilization for five seconds: 3%/0%; one minute: 4%; five minutes: 3%
 PID Runtime(ms)     Invoked      uSecs   5Sec   1Min   5Min TTY Process 
   1           0           2          0  0.00%  0.00%  0.00%   0 Chunk Manager    
   2        3140       89410         35  0.00%  0.01%  0.00%   0 Load Meter       
  89      184200     1492040        123  0.45%  0.38%  0.35%   0 IP Input         
 142       94810      584100        162  0.12%  0.10%  0.09%   0 Spanning Tree    
"""
            elif "ntp" in c_low:
                return f"""Clock is synchronized, stratum 2, reference is 10.254.0.5
nominal freq is 250.0000 Hz, actual freq is 249.9998 Hz, precision is 2**18
reference time is {now_str}.124 UTC
clock offset is 0.412 msec, root delay is 2.15 msec
root dispersion is 14.82 msec, peer dispersion is 1.12 msec
loopfilter state is 'SPIK' (Spike detected), offset 0.000412 s, interval 64 s
"""
            elif "logging" in c_low:
                return f"""Syslog logging: enabled (0 messages dropped, 0 messages rate-limited, 0 flushes)
    Console logging: level debugging, 1420 messages logged, xml disabled
    Monitor logging: level debugging, 0 messages logged, xml disabled
    Buffer logging:  level debugging, 4820 messages logged, xml disabled
    Logging Exception size (4096 bytes)
    Count and timestamp logging messages: enabled
    Trap logging: level informational, 1420 message lines logged
        Logging Source-Interface: Loopback0

*Sep 03 04:12:01.418: %SYS-5-CONFIG_I: Configured from console by admin on vty0 (10.254.100.5)
*Sep 03 04:15:22.891: %LINK-3-UPDOWN: Interface GigabitEthernet1/0/1, changed state to up
*Sep 03 04:15:23.892: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet1/0/1, changed state to up
"""
            elif "interfaces status" in c_low or "interface status" in c_low:
                return """Port      Name               Status       Vlan       Duplex  Speed Type
Gi1/0/1   Uplink-Core01      connected    trunk        a-full a-1000 10/100/1000BaseTX
Gi1/0/2   Uplink-Core02      connected    trunk        a-full a-1000 10/100/1000BaseTX
Gi1/0/3   GWN-AP-FL1-01      connected    10           a-full a-1000 10/100/1000BaseTX
Gi1/0/4   GWN-AP-FL1-02      connected    10           a-full a-1000 10/100/1000BaseTX
Gi1/0/5   User-Workstation   connected    20           a-full a-1000 10/100/1000BaseTX
Gi1/0/6   User-Workstation   connected    20           a-full a-1000 10/100/1000BaseTX
Gi1/0/47  Po1-Member         connected    trunk        a-full a-1000 10/100/1000BaseTX
Gi1/0/48  Po1-Member         connected    trunk        a-full a-1000 10/100/1000BaseTX
Te1/0/1   10G-Core-Link      connected    routed         full    10G SFP-10G-SR
Te1/0/2   10G-SAN-Link       connected    routed         full    10G SFP-10G-SR
"""
            elif "interfaces counters errors" in c_low:
                return """Port        Align-Err    FCS-Err   Xmit-Err    Rcv-Err UnderSize OutDiscards
Gi1/0/1             0          0          0          0         0           0
Gi1/0/2             0          0          0          0         0           0
Gi1/0/3             0          0          0          0         0           0
Gi1/0/47            0          0          0          0         0           0
Gi1/0/48            0          0          0          0         0           0
Te1/0/1             0          0          0          0         0           0
"""
            elif "vlan" in c_low:
                return """VLAN Name                             Status    Ports
---- -------------------------------- --------- -------------------------------
1    default                          active    Gi1/0/7, Gi1/0/8, Gi1/0/9
10   Data_VLAN                        active    Gi1/0/3, Gi1/0/4, Gi1/0/5
20   Voice_VLAN                       active    Gi1/0/6, Gi1/0/10, Gi1/0/11
30   Management                       active    Gi1/0/12, Gi1/0/13
99   Native_Transit                   active    
100  Server_Farm                      active    Gi1/0/14, Gi1/0/15
"""
            elif "trunk" in c_low:
                return """Port        Mode             Encapsulation  Status        Native vlan
Gi1/0/1     on               802.1q         trunking      99
Gi1/0/2     on               802.1q         trunking      99
Po1         on               802.1q         trunking      99

Port        Vlans allowed on trunk
Gi1/0/1     1-4094
Gi1/0/2     1-4094
Po1         10,20,30,99,100

Port        Vlans in spanning tree forwarding state and not pruned
Gi1/0/1     10,20,30,99,100
Gi1/0/2     10,20,30,99,100
Po1         10,20,30,99,100
"""
            elif "spanning-tree" in c_low or "stp" in c_low:
                return f"""Switch is in rapid-pvst mode
Root bridge for: VLAN0010, VLAN0020, VLAN0030, VLAN0099
EtherChannel misconfig guard is enabled
Extended system ID           is enabled
Portfast Default             is enabled
PortFast BPDU Guard Default  is enabled
Loopguard Default            is disabled
UplinkFast                   is disabled
BackboneFast                 is disabled

Name                   Blocking Listening Learning Forwarding STP Active
---------------------- -------- --------- -------- ---------- ----------
VLAN0010                      0         0        0          6          6
VLAN0020                      0         0        0          6          6
VLAN0030                      0         0        0          4          4
VLAN0099                      0         0        0          4          4
---------------------- -------- --------- -------- ---------- ----------
4 vlans                       0         0        0         20         20
"""
            elif "etherchannel" in c_low or "port-channel" in c_low or "lacp" in c_low:
                return """Flags:  D - down        P - bundled in port-channel
        I - stand-alone s - suspended
        H - Hot-standby (LACP only)
        R - Layer3      S - Layer2
        U - in use      N - not in use, no aggregation
        f - failed to allocate aggregator

Group  Port-channel  Protocol    Ports
------+-------------+-----------+-----------------------------------------------
1      Po1(SU)         LACP      Gi1/0/47(P)   Gi1/0/48(P)
2      Po2(RU)         LACP      Te1/0/1(P)    Te1/0/2(P)
"""
            elif "ospf" in c_low:
                return """Neighbor ID     Pri   State           Dead Time   Address         Interface
10.254.1.2        1   FULL/DR         00:00:34    10.254.1.2      GigabitEthernet1/0/1
10.254.1.3        1   FULL/BDR        00:00:36    10.254.1.3      GigabitEthernet1/0/2
10.254.0.254      1   FULL/DROTHER    00:00:38    10.254.0.254    Port-channel2
"""
            elif "bgp" in c_low:
                return """BGP router identifier 10.254.1.1, local AS number 65001
BGP table version is 48, main routing table version 48
3 network entries using 744 bytes of memory
3 path entries using 408 bytes of memory

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.254.1.2      4        65001    8412    8415       48    0    0 04:12:45        3
10.254.200.1    4        65002    4210    4208       48    0    0 02:18:12       12
"""
            elif "hsrp" in c_low or "standby" in c_low or "vrrp" in c_low:
                return """                     P indicates configured to preempt.
                     |
Interface   Grp  Pri P State   Active          Standby         Virtual IP
Vlan10      10   110 P Active  local           10.254.10.2     10.254.10.1
Vlan20      20   110 P Active  local           10.254.20.2     10.254.20.1
Vlan30      30   110 P Active  local           10.254.30.2     10.254.30.1
"""
            elif "cdp" in c_low or "lldp" in c_low:
                return f"""Device ID: SW-ACC-01.zenquix.local
Entry address(es): 
  IP address: 10.254.1.10
Platform: cisco WS-C2960X-48TD-L,  Capabilities: Switch IGMP 
Interface: GigabitEthernet1/0/1,  Port ID (outgoing port): GigabitEthernet1/0/49
Holdtime : 142 sec

Version :
Cisco IOS Software, C2960X Software (NSS-UNIVERSALK9-M), Version 15.2(7)E3

Native VLAN: 99
Duplex: full
Management address(es): 
  IP address: 10.254.1.10
"""
            elif "ip route" in c_low or "route" in c_low:
                return """Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 

Gateway of last resort is 10.254.0.1 to network 0.0.0.0

S*    0.0.0.0/0 [1/0] via 10.254.0.1
      10.0.0.0/8 is variably subnetted, 12 subnets, 3 masks
C        10.254.1.0/24 is directly connected, Vlan99
L        10.254.1.1/32 is directly connected, Vlan99
O        10.254.10.0/24 [110/2] via 10.254.1.2, 04:12:45, GigabitEthernet1/0/1
O        10.254.20.0/24 [110/2] via 10.254.1.2, 04:12:45, GigabitEthernet1/0/1
C        10.254.100.0/24 is directly connected, Loopback0
"""

        # ── 2. GRANDSTREAM GWN 7803P SWITCH ──────────────────────────────
        if "gwn" in v or "780" in m or "grandstream" in v:
            if "running-config" in c_low or "run" == c_low or "show run" in c_low or c_low.startswith("show run"):
                return f"""# GWN7803P Configuration Export
# Generated at {now_str}
# Device: {hostname} (MAC: C0:74:AD:44:88:01)
#
sysname {hostname}
#
vlan 1
#
vlan 10
 name Corporate-Data
#
vlan 20
 name Voice-Network
#
vlan 30
 name AP-Management
#
vlan 99
 name Management
#
interface gigabitethernet 1/0/1
 port link-type access
 port default vlan 10
#
interface gigabitethernet 1/0/2
 port link-type access
 port default vlan 10
#
interface ten-gigabitethernet 1/0/1
 port link-type trunk
 port trunk pvid 99
 port trunk allow-pass vlan 10 20 30 99
#
interface vlanif 99
 ip address {management_ip} 255.255.255.0
#
ip route-static 0.0.0.0 0.0.0.0 10.254.1.1
#
ssh server enable
user-interface vty 0 4
 authentication-mode scheme
 protocol inbound ssh
#
return
"""
            elif "version" in c_low or "system" in c_low:
                return f"""Grandstream Networks GWN7803P Layer 2+ Enterprise Managed Switch
Hardware Version : V1.0A
Boot Version     : V1.0.0.1
Software Version : V1.0.9.15 (Build 20230818)
System Object ID : 1.3.6.1.4.1.2620
MAC Address      : C0:74:AD:44:88:01
System Name      : {hostname}
System Up Time   : 38 days, 11 hours, 18 mins, 44 secs
Power Supply 1   : AC Active (PoE Budget: 360W, Output: 48W)
Fan 1 Status     : Normal (4800 RPM)
Internal Temp    : 34 C (Normal Threshold: < 75 C)
"""
            elif "vlan" in c_low:
                return """VLAN ID  VLAN Name        Type      Ports
-------  ---------------  --------  ----------------------------------------
1        default          Default   GE1/0/1-GE1/0/24, 10G1/0/1-10G1/0/4
10       Data_Network     Static    GE1/0/1-GE1/0/12
20       Voice_Network    Static    GE1/0/13-GE1/0/20
30       AP_Management    Static    GE1/0/21-GE1/0/24, 10G1/0/1(Tagged)
99       Native_Mgmt      Static    10G1/0/1(Tagged), 10G1/0/2(Tagged)
"""
            elif "interface" in c_low:
                return """Port      Link   Speed   Duplex  FlowCtrl  PVID  Type       Description
-------  -----  ------  ------  --------  ----  ---------  -----------------
GE1/0/1   Up     1000M   Full    Disable   10    Access     GWN7662-AP01
GE1/0/2   Up     1000M   Full    Disable   10    Access     GWN7660-AP02
GE1/0/3   Up     1000M   Full    Disable   20    Access     IP_Phone_Sales
10G1/0/1  Up     10G     Full    Disable   1     Trunk      Core_Switch_Uplink
10G1/0/2  Up     10G     Full    Disable   1     Trunk      Core_Switch_Uplink2
"""
            elif "mac" in c_low:
                return """VLAN ID  MAC Address        Port      Type     Aging
-------  -----------------  --------  -------  -----
10       C0:74:AD:AA:BB:01  GE1/0/1   Dynamic  300
10       C0:74:AD:AA:BB:02  GE1/0/2   Dynamic  300
20       00:0B:82:11:22:33  GE1/0/3   Dynamic  300
99       70:69:79:AB:CD:01  10G1/0/1  Dynamic  300
Total MAC Addresses: 4
"""
            elif "lldp" in c_low or "neighbor" in c_low:
                return """Chassis ID: C0:74:AD:12:34:56
Port ID: eth0
System Name: GWN7662-AP01
Port Description: Grandstream 802.11ax Wi-Fi 6 Access Point
Management Address: 10.254.30.11
Capabilities: WLAN Access Point, Bridge
Local Port: GE1/0/1
"""

        # ── 3. GRANDSTREAM ACCESS POINTS (GWN 7662, 7660, 7660E) ────────
        if "766" in m or ("ap" in m and "gwn" in v) or "wireless" in v:
            if "running-config" in c_low or "wireless" in c_low or "config" in c_low:
                return f"""# GWN7662 Configuration Snapshot
config system
    option hostname '{hostname}'
    option timezone 'UTC'

config wifi-device 'radio0'
    option type 'mac80211'
    option channel '6'
    option hwmode '11g'
    option htmode 'HT20'
    option disabled '0'

config wifi-device 'radio1'
    option type 'mac80211'
    option channel '149'
    option hwmode '11a'
    option htmode 'HE80'
    option disabled '0'

config wifi-iface 'default_radio0'
    option device 'radio0'
    option network 'lan'
    option mode 'ap'
    option ssid 'Zenquix-Corp'
    option encryption 'psk2+ccmp'
    option key 'EnterprisePass2026!'

config wifi-iface 'guest_radio0'
    option device 'radio0'
    option network 'guest'
    option mode 'ap'
    option ssid 'Zenquix-Guest'
    option encryption 'none'
    option isolate '1'
"""
            elif "system" in c_low or "info" in c_low or "ubus" in c_low:
                return f"""{{
  "uptime": 248912,
  "hostname": "{hostname}",
  "model": "{model.upper() or 'GWN7662'}",
  "firmware": "1.0.21.16",
  "mac": "C0:74:AD:66:77:88",
  "ip": "{management_ip}",
  "memory": {{
    "total": 524288,
    "free": 384192,
    "shared": 0,
    "buffered": 28416
  }},
  "load": [0.08, 0.04, 0.01],
  "wireless": {{
    "radio0_2g": {{ "channel": 6, "txpower": 20, "clients": 14, "ssid": "Zenquix-Corp" }},
    "radio1_5g": {{ "channel": 36, "txpower": 23, "clients": 28, "ssid": "Zenquix-Corp-5G" }}
  }}
}}"""
            elif "iwinfo" in c_low or "wlan" in c_low or "radio" in c_low or "ssid" in c_low:
                return """wlan0     ESSID: "Zenquix-Corp"
          Access Point: C0:74:AD:66:77:88
          Mode: Master  Channel: 6 (2.437 GHz)
          Tx-Power: 20 dBm  Link Quality: 70/70
          Signal: -38 dBm  Noise: -95 dBm
          Bit Rate: 573.5 MBit/s (802.11ax HE20)
          Encryption: WPA2/WPA3 Enterprise (802.1X, AES-CCMP)
          Associated Clients: 14

wlan1     ESSID: "Zenquix-Corp-5G"
          Access Point: C0:74:AD:66:77:89
          Mode: Master  Channel: 36 (5.180 GHz)
          Tx-Power: 23 dBm  Link Quality: 70/70
          Signal: -32 dBm  Noise: -98 dBm
          Bit Rate: 2402.0 MBit/s (802.11ax HE80)
          Encryption: WPA2/WPA3 Enterprise (802.1X, AES-CCMP)
          Associated Clients: 28
"""
            elif "dev" in c_low or "traffic" in c_low:
                return """Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo: 4821908   42104    0    0    0     0          0         0  4821908   42104    0    0    0     0       0          0
  eth0: 98412048 184201    0    0    0     0          0      8410 84102948 142014    0    0    0     0       0          0
 wlan0: 18420194  98412    0    0    0     0          0         0 24102948 114028    0    0    0     0       0          0
 wlan1: 64102948 312014    0    0    0     0          0         0 94102948 412094    0    0    0     0       0          0
"""

        # ── 4. SOPHOS XGS FIREWALL (SFOS) ─────────────────────────────────
        if "sophos" in v or "xgs" in m or "sfos" in m:
            if "status" in c_low or "system" in c_low or "diagnostics" in c_low:
                return f"""Sophos Firewall OS (SFOS) Version 20.0.1 MR-1-Build342
Device Model: Sophos XGS 2100 Next-Gen Firewall
Serial Number: C21008ABCD12345
Appliance Mode: Gateway / Router
HA Status: Active-Passive (Standalone Primary, Node ID: 1)
System Uptime: 52 days 4 hours 12 minutes
CPU Utilization: 6% (Quad-Core NPU Accelerated)
Memory Usage: 41% (3.28 GB / 8.00 GB)
Disk Usage: /var (14%), /tmp (2%), /content (28%)
Secure Boot: Enabled
Firmware Active: SFOS 20.0.1 MR-1 (Backup: SFOS 19.5.3 MR-3)
"""
            elif "route" in c_low or "routing" in c_low:
                return """Kernel IP routing table
Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
0.0.0.0         198.51.100.1    0.0.0.0         UG    0      0        0 Port2 (WAN)
10.254.0.0      0.0.0.0         255.255.0.0     U     0      0        0 Port1 (LAN)
198.51.100.0    0.0.0.0         255.255.255.248 U     0      0        0 Port2 (WAN)
172.16.1.0      10.254.1.254    255.255.255.0   UG    10     0        0 Port1 (LAN)
"""
            elif "firewall" in c_low or "rule" in c_low or "policy" in c_low:
                return """Rule ID: 1 | Name: Default_LAN_to_WAN | Status: ENABLED | Action: ACCEPT
  Source Zones: LAN, DMZ | Networks: Any
  Destination Zones: WAN | Networks: Any
  Services: HTTP, HTTPS, DNS, NTP, ICMP
  NAT: Masquerade (Port2 IPv4)
  Security Profiles: IPS (High-Protection), WebFilter (Default-Workplace), Antivirus (Dual Engine)
  Matched Traffic: 1,842,910 Packets (4.18 GB)

Rule ID: 2 | Name: Inbound_HTTPS_DMZ | Status: ENABLED | Action: ACCEPT
  Source Zones: WAN | Networks: Any
  Destination Zones: DMZ | Networks: 10.254.100.10
  Services: HTTPS (TCP 443)
  NAT: DNAT -> 10.254.100.10:443
"""
            elif "vpn" in c_low or "ipsec" in c_low:
                return """IPsec Connection Status:
Connection Name: Tunnel_DC_to_Branch01 | Status: ESTABLISHED (Phase 2 UP)
  Local Gateway: 198.51.100.2 (Port2) | Local Subnet: 10.254.0.0/16
  Remote Gateway: 203.0.113.5 | Remote Subnet: 10.100.0.0/16
  Encryption: AES-256-GCM | Authentication: SHA2-384 | DH Group: 19 (ECP256)
  Tunnel Uptime: 14 days, 22 hours | Bytes In: 412 MB | Bytes Out: 894 MB
"""

        # ── 5. MERAKI M44 / REST API ──────────────────────────────────────
        if "meraki" in v or "rest" in m:
            return f"""HTTP/1.1 200 OK
Content-Type: application/json

{{
  "id": "{hostname}",
  "networkId": "N_14820148",
  "name": "{hostname}",
  "serial": "Q2QN-ABCD-1234",
  "mac": "0c:8d:db:11:22:33",
  "model": "MX44-HW",
  "status": "online",
  "publicIp": "198.51.100.25",
  "wan1": {{
    "ip": "198.51.100.25",
    "gateway": "198.51.100.1",
    "status": "active"
  }},
  "firmware": "wired-18-211",
  "vlans": [
    {{ "id": 10, "name": "Corporate-Data", "subnet": "10.254.10.0/24", "applianceIp": "10.254.10.1" }},
    {{ "id": 20, "name": "Voice-VLAN", "subnet": "10.254.20.0/24", "applianceIp": "10.254.20.1" }},
    {{ "id": 99, "name": "Management", "subnet": "10.254.99.0/24", "applianceIp": "10.254.99.1" }}
  ]
}}"""

        # ── 6. GENERIC FALLBACK ──────────────────────────────────────────
        if "running-config" in c_low or "configuration" in c_low or "show run" in c_low or c_low == "run":
            return f"""# Running Configuration Snapshot: {hostname}
# Vendor: {vendor} | Model: {model}
# Captured: {now_str}
# Management IP: {management_ip}
hostname {hostname}
interface Management1
 ip address {management_ip}/24
 no shutdown
service ssh enabled
end
"""

        return f"""Command '{c}' executed successfully on {hostname} ({vendor} {model}).
Output timestamp: {now_str}
Status: OK (200)
Response: All parameters verified within nominal operational thresholds.
"""
