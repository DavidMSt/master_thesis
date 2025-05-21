import getpass
import re
import socket
import os
import subprocess
import sys
import platform


def getInterfaceIP(interface_name):
    """
    Retrieves the IP address of a specified interface.
    Args:
    - interface_name (str): The name of the interface.
    Returns:
    - str or None: The IP address of the interface, or None if not found.
    """
    os_name = platform.system()

    try:
        if os_name == "Windows":
            result = subprocess.run(
                ["ipconfig"],
                capture_output=True,
                text=True,
                check=True
            )
            output = result.stdout
            interface_section = re.search(
                rf"{interface_name}.*?(\n\s+[^\n]+)+", output, re.DOTALL)

            if interface_section:
                interface_info = interface_section.group(0)
                match_ip = re.search(
                    r"Autoconfiguration IPv4 Address\\. .*: (\d+\.\d+\.\d+\.\d+)", interface_info)
                if match_ip:
                    return match_ip.group(1)

        elif os_name == "Darwin":  # MacOS
            result = subprocess.run(
                ["ifconfig", interface_name],
                capture_output=True,
                text=True,
                check=True
            )
            output = result.stdout
            match_ip = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", output)
            if match_ip:
                return match_ip.group(1)

        elif os_name == "Linux":  # Linux (Ubuntu)
            result = subprocess.run(
                ["ip", "addr", "show", interface_name],
                capture_output=True,
                text=True,
                check=True
            )
            output = result.stdout
            match_ip = re.search(r"inet (\d+\.\d+\.\d+\.\d+)/", output)
            if match_ip:
                return match_ip.group(1)

    except subprocess.CalledProcessError as e:
        print(f"Failed to retrieve IP address: {e}")

    return None

def splitServerAddress(address: str):
    server_address = None
    server_port = None
    try:
        server_address = re.search(r'[0-9.]*(?=:)', address)[0]
    except:
        ...
    try:
        server_port = int(re.search(r'(?<=:)[0-9]*', address)[0])
    except:
        ...

    return server_address, server_port


def getAllIPAdresses():
    """

    :param debug:
    :return:
    """

    local_ip = None
    usb_ip = None

    if os.name == 'nt':

        hostname = socket.gethostname()
        ip_addresses = socket.gethostbyname_ex(hostname)[2]
        local_ips = [ip for ip in ip_addresses if ip.startswith("192.168.0")]
        if len(local_ips) == 0:
            return None

        local_ip = [ip for ip in ip_addresses if ip.startswith("192.168.0")][:1][0]
        usb_ip = ''
        server_address = socket.gethostbyname_ex(socket.gethostname())

    elif os.name == 'posix':
        hostname = socket.gethostname()
        ip_addresses = socket.gethostbyname_ex(hostname)[2]
        local_ips = [ip for ip in ip_addresses if ip.startswith("192.168.")]
        if len(local_ips) == 0:
            return None
        local_ip = [ip for ip in ip_addresses if ip.startswith("192.168.")][:1][0]
        usb_ip = ''
        server_address = socket.gethostbyname_ex(socket.gethostname())

    output = {'hostname': hostname, 'local': local_ip, 'usb': usb_ip, 'all': server_address[2]}

    for i, add in enumerate(server_address[2]):
        if add is not local_ip and add is not usb_ip:
            ...
    return output


def getLocalIP():
    """

        :param debug:
        :return:
        """

    local_ip = None
    usb_ip = None

    if os.name == 'nt':

        hostname = socket.gethostname()
        ip_addresses = socket.gethostbyname_ex(hostname)[2]
        local_ips = [ip for ip in ip_addresses if ip.startswith("192.168.0")]
        if len(local_ips) == 0:
            return None

        local_ip = [ip for ip in ip_addresses if ip.startswith("192.168.0")][:1][0]
        usb_ip = ''
        server_address = socket.gethostbyname_ex(socket.gethostname())

    elif os.name == 'posix':
        hostname = socket.gethostname()
        ip_addresses = socket.gethostbyname_ex(hostname)[2]
        local_ips = [ip for ip in ip_addresses if ip.startswith("192.168.")]
        if len(local_ips) == 0:
            return None
        local_ip = [ip for ip in ip_addresses if ip.startswith("192.168.")][:1][0]
        usb_ip = ''
        server_address = socket.gethostbyname_ex(socket.gethostname())

    return local_ip


def is_ipv4(address):
    """Check if the provided address is a valid IPv4 address."""
    try:
        socket.inet_aton(address)
        return True
    except socket.error:
        return False


def ipv4_to_bytes(ipv4_str):
    """Encode an IPv4 string into 4 bytes."""
    if not is_ipv4(ipv4_str):
        raise ValueError("Invalid IPv4 address.")
    # Use socket library to pack the IPv4 string into 4 bytes
    return socket.inet_aton(ipv4_str)


def bytes_to_ipv4(byte_data):
    """Decode 4 bytes back into an IPv4 string."""
    if len(byte_data) != 4:
        raise ValueError("Invalid byte length for IPv4 address.")
    # Use socket library to unpack the bytes back into a string
    return socket.inet_ntoa(byte_data)


def resolve_hostname(hostname, check_availability=False):
    """Resolve a hostname to an IP address and check its network availability.

    Args:
        hostname (str): The hostname to resolve.
        check_availability (bool): Whether to check if the host is reachable on the network.

    Returns:
        str: The IP address of the hostname, or an error message if unreachable.
    """
    try:
        # Step 1: Resolve the hostname to an IP address
        ip_address = socket.gethostbyname(hostname)

        # Step 2: Optionally check if the host is available on the network
        if check_availability:
            if is_host_reachable(ip_address):
                return f"{hostname} is available at IP: {ip_address}"
            else:
                return f"{hostname} resolved to {ip_address}, but is not reachable on the network."

        return ip_address

    except socket.gaierror:
        return None


def is_host_reachable(ip_address):
    """Ping the IP address to check if it is reachable on the network."""
    # Use different commands depending on the operating system
    param = "-n" if platform.system().lower() == "windows" else "-c"
    command = ["ping", param, "1", ip_address]

    try:
        # Send the ping command and check for a successful response
        response = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return response.returncode == 0
    except Exception as e:
        print(f"An error occurred while pinging: {e}")
        return False


def get_hostname(ip_address):
    # hostname, _, _ = socket.gethostbyaddr(ip_address)
    # return hostname
    # """Resolve an IP address to a hostname.
    #
    # Args:
    #     ip_address (str): The IP address to resolve.
    #
    # Returns:
    #     str: The hostname associated with the IP address, or an error message if not found.
    # """
    try:
        # Perform a reverse DNS lookup
        hostname, _, _ = socket.gethostbyaddr(ip_address)
        return hostname
    except socket.herror:
        return None
    except socket.gaierror:
        return None
    except Exception as e:
        return None


def getIPAdress(address):
    # Check if the address is a valid IPv4 String:
    if is_ipv4(address):
        return address
    else:
        return resolve_hostname(address)


def getLocalIP_RPi():
    network_information = getNetworkInformation()

    if network_information['local_ip'] is not None:
        return network_information['local_ip']
    elif network_information['usb_ip'] is not None:
        return network_information['usb_ip']
    else:
        return None


def get_current_user():
    """
    Returns the name of the currently logged-in user.
    """
    return getpass.getuser()


def get_own_hostname():
    hostname = socket.gethostname()
    return hostname


def get_wifi_ssid():
    try:
        # Get the SSID of the current Wi-Fi network
        ssid = subprocess.check_output(['/sbin/iwgetid', '-r']).decode().rstrip()
        if ssid == '':
            ssid = None
    except Exception:
        ssid = None

    return ssid


def check_internet(timeout=0.25):
    """
    Checks if the device has internet connectivity by pinging 8.8.8.8.

    :param timeout: Timeout in seconds for the ping command.
    :return: True if the device can ping 8.8.8.8, False otherwise.
    """
    try:
        # Use subprocess to ping 8.8.8.8 with a single packet and specified timeout
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout), "8.8.8.8"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0  # Return True if ping was successful (returncode 0)
    except Exception as e:
        print(f"Error while checking internet connectivity: {e}")
        return False


def getNetworkInformation():
    try:
        # Get the username from the /home directory
        usernames = os.listdir('/home/')
        username = usernames[0] if usernames else None
    except Exception:
        username = None

    try:
        # Get the hostname of the device
        hostname = socket.gethostname()
    except Exception:
        hostname = None

    try:
        # Get the SSID of the current Wi-Fi network
        ssid = subprocess.check_output(['/sbin/iwgetid', '-r']).decode().rstrip()
        if ssid == '':
            ssid = None
    except Exception:
        ssid = None

    try:
        # Get the list of IP addresses
        ip_string = subprocess.check_output(['hostname', '-I']).decode()
        ips = re.findall(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', ip_string)

        # Separate IPs into local and USB IPs
        local_ips = [ip for ip in ips if ip.startswith('192.')]
        usb_ips = [ip for ip in ips if ip.startswith('169.')]

        # Use the first local IP or set to None if not found
        local_ip = local_ips[0] if local_ips else None

        usb_ips = usb_ips[0] if usb_ips else None

    except Exception:
        local_ip = None
        usb_ips = None

    return {
        "username": username,
        "hostname": hostname,
        "ssid": ssid,
        "local_ip": local_ip,
        "usb_ip": usb_ips
    }
