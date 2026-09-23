"""
Constants and Enums for Network Infrastructure Audit Application.
"""
from enum import Enum

class DeviceFunction(str, Enum):
    L2 = "L2"
    L3 = "L3"
    L2_L3 = "L2/L3"
    WIRELESS_AP = "Wireless AP"
    FIREWALL = "Firewall"
    EDGE_WAN = "Edge/WAN"
    OTHER = "Other"

class DeviceRole(str, Enum):
    CORE = "Core"
    DISTRIBUTION = "Distribution"
    ACCESS = "Access"
    LEAF = "Leaf"
    SPINE = "Spine"
    FIREWALL = "Firewall"
    EDGE = "Edge"
    WIRELESS_AP = "Wireless AP"
    OTHER = "Other"

class AuditStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    NOT_APPLICABLE = "NOT APPLICABLE"
    UNKNOWN = "UNKNOWN"

class SeverityLevel(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFO = "Info"

class LifecycleStatus(str, Enum):
    ACTIVE = "Active"
    EOL = "EOL"
    EOS = "EOS"
    PLANNED = "Planned"

class PortSpeed(str, Enum):
    SPEED_100M = "100M"
    SPEED_1G = "1G"
    SPEED_10G = "10G"
    SPEED_25G = "25G"
    SPEED_40G = "40G"
    SPEED_100G = "100G"
    SPEED_400G = "400G"

class PortType(str, Enum):
    ETHERNET = "Ethernet"
    FAST_ETHERNET = "FastEthernet"
    GIGABIT_ETHERNET = "GigabitEthernet"
    TEN_GIGABIT = "TenGigabitEthernet"
    TWENTY_FIVE_GIG = "TwentyFiveGigE"
    FORTY_GIG = "FortyGigabitEthernet"
    HUNDRED_GIG = "HundredGigE"
    SFP = "SFP"
    SFP_PLUS = "SFP+"
    QSFP = "QSFP"
    QSFP28 = "QSFP28"

class TaskVerificationStatus(str, Enum):
    INCOMPLETE = "In-Complete"
    COMPLETED = "Completed"
    WARNING = "Warning"
    FAILED = "Failed"
    NOT_APPLICABLE = "N/A"

class AuditProtocol(str, Enum):
    RUNNING_CONFIG = "Running Config"
    BASIC_HEALTH = "Device Health"
    INTERFACES = "Interfaces"
    CDP = "CDP"
    LLDP = "LLDP"
    VLAN = "VLAN"
    ACCESS_PORT = "Access Port"
    TRUNK = "Trunk"
    STP = "STP"
    ETHERCHANNEL = "EtherChannel / LACP"
    PORT_SECURITY = "Port Security"
    DHCP_SNOOPING = "DHCP Snooping"
    DAI = "Dynamic ARP Inspection"
    IP_SOURCE_GUARD = "IP Source Guard"
    SVI = "SVI"
    STATIC_ROUTING = "Static Routing"
    OSPF = "OSPF"
    BGP = "BGP"
    EIGRP = "EIGRP"
    ISIS = "IS-IS"
    HSRP = "HSRP"
    VRRP = "VRRP"
    VRF = "VRF"
    BFD = "BFD"
    MPLS = "MPLS / LDP"
    QOS = "QoS"
    ACL = "ACL"
    NAT = "NAT"
    VPN = "VPN / IPsec"
    FIREWALL_POLICY = "Firewall Policy"
    FIREWALL_HA = "Firewall HA"
    FIREWALL_ZONES = "Security Zones"
    WIRELESS_WLC = "Wireless Controller"
    WIRELESS_AP = "AP Registration"
    WIRELESS_SSID = "SSID & WLAN"
    WIRELESS_RF = "RF Radio & Channels"
    WAN_UNDERLAY = "WAN Underlay / Overlay"
    WAN_SLA = "WAN SLA & Path Monitoring"
    MANAGEMENT_SECURITY = "Management Security (AAA/SSH/NTP/SNMP)"

# Function-aware & Role-aware Audit Module Activations
FUNCTION_AUDIT_MODULES = {
    DeviceFunction.L3: ["L3_Config", "L3_Routing", "L3_Design_Validation", "Connectivity", "Performance"],
    DeviceFunction.L2: ["L2_Switching", "L2_STP", "L2_VLAN", "L2_Design_Validation", "Connectivity"],
    DeviceFunction.L2_L3: ["L2_Switching", "L2_STP", "L2_VLAN", "L3_Config", "L3_Routing", "Port_Channel", "Connectivity"],
    DeviceFunction.WIRELESS_AP: ["Wireless_Config", "Wireless_Radio", "Wireless_Security", "Wireless_Health", "Connectivity"],
    DeviceFunction.FIREWALL: ["Firewall_Interface", "Firewall_Policy", "Firewall_NAT", "Firewall_HA", "Firewall_Health", "Connectivity"],
    DeviceFunction.EDGE_WAN: ["WAN_Interface", "WAN_BGP_OSPF", "WAN_VPN", "WAN_QoS", "WAN_Health", "Connectivity"],
    DeviceFunction.OTHER: ["Device_Health", "Connectivity"]
}

ROLE_AUDIT_DISPLAY_MAP = {
    DeviceRole.CORE: "L3 + Routing + Redundancy + Connectivity + Interface + Performance",
    DeviceRole.ACCESS: "L2 + VLAN + STP + Interface + Port Security + Connectivity",
    DeviceRole.SPINE: "L3 + Underlay + Routing + ECMP + BGP/OSPF + Connectivity",
    DeviceRole.LEAF: "L2/L3 + VLAN + VXLAN/EVPN + Routing + Port-Channel + Connectivity",
    DeviceRole.DISTRIBUTION: "L2/L3 + FHRP (HSRP/VRRP) + VLAN + Routing + Redundancy + Connectivity",
    DeviceRole.FIREWALL: "Security + Routing + NAT + HA + Interfaces + Policy + Connectivity",
    DeviceRole.WIRELESS_AP: "Wireless + Controller + Radio + SSID + VLAN + Client + Connectivity",
    DeviceRole.EDGE: "WAN Interfaces + ISP Peering + VPN + NAT + HA + QoS + Connectivity",
    DeviceRole.OTHER: "Device Health + Connectivity + Baseline Audit"
}

