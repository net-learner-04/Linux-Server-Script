from scapy.all import ARP, Ether, srp


def scan_network(subnet):
    '''Send ARP requests across the given subnet 
    and return a list of responding devices (ip, mac).'''
    return_list = []

    arp_req = ARP(pdst=subnet)
    # Broadcast Mac Address
    pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / arp_req

    # For the network interface name, enter the name of your NIC. (iface)
    ans_list, unans_list = srp(pkt, timeout=2, verbose=False, iface="eth0")

    for tx, rx in ans_list:
        return_list.append(dict(ip=rx.psrc, mac=rx.hwsrc))
    
    return return_list
