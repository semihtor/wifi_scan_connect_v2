# network_operations.py

import subprocess
import re
import time
import config

def get_wlx_interface():
    """Finds the wireless network interface starting with WIFI_INTERFACE_PREFIX."""
    try:
        result = subprocess.check_output("ls /sys/class/net/", shell=True).decode("utf-8")
        interfaces = result.split()
        for iface in interfaces:
            if iface.startswith(config.WIFI_INTERFACE_PREFIX):
                print(f"USB WiFi interface to be used: {iface}")
                return iface
    except Exception as e:
        print(f"ERROR: WiFi interface not found: {e}")
    return None

def set_hostname_on_system(wlx_interface_val):
    """Sets the device hostname based on the wlx interface."""
    if wlx_interface_val:
        last_chars = re.sub(r'[^a-zA-Z0-9]', '', wlx_interface_val)[-4:]
        new_hostname = f"{config.HOSTNAME_PREFIX}{last_chars}"
        try:
            subprocess.run(f"sudo hostnamectl set-hostname {new_hostname}", shell=True, check=True)
            print(f"Hostname set to: {new_hostname}")
            return new_hostname
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to set hostname: {e}")
            return f"{config.HOSTNAME_PREFIX}ERR"
    else:
        print("WARNING: Could not set hostname because wlx interface was not found.")
        return f"{config.HOSTNAME_PREFIX}NOIF"

def clear_existing_wifi_connections(wlx_interface_val):
    """Removes all existing WiFi connections from NetworkManager."""
    if not wlx_interface_val:
        print("WARNING: Cannot clear connections without a WiFi interface.")
        return
    try:
        print("Clearing existing WiFi connections...")
        active_result = subprocess.check_output(f"nmcli -t -f NAME,DEVICE c show --active", shell=True).decode("utf-8")
        for line in active_result.splitlines():
            parts = line.split(':')
            if len(parts) == 2 and parts[1] == wlx_interface_val:
                print(f"Deactivating connection '{parts[0]}'...")
                subprocess.run(f"nmcli c down '{parts[0]}'", shell=True, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        all_connections_result = subprocess.check_output("nmcli -t -f UUID,TYPE c", shell=True).decode("utf-8")
        for line in all_connections_result.splitlines():
            uuid, conn_type = line.split(':')
            if conn_type == "802-11-wireless":
                print(f"Deleting WiFi connection with UUID '{uuid}'...")
                subprocess.run(f"nmcli c delete uuid {uuid}", shell=True, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("WiFi connections cleared.")
    except Exception as e:
        print(f"ERROR: An issue occurred while clearing WiFi connections: {e}")

def scan_wifi_networks(wlx_interface_val):
    """Scans for nearby WiFi networks."""
    if not wlx_interface_val:
        print("WARNING: Cannot scan without a WiFi interface.")
        return ["No Interface"]

    print("Scanning WiFi networks...")
    scanned_ap_list = []
    try:
        subprocess.run(f"nmcli dev wifi rescan ifname {wlx_interface_val}", shell=True, check=True, timeout=config.NMCLI_RESCAN_TIMEOUT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2) # Give some time for the scan results to populate
        result = subprocess.check_output(f"nmcli --escape no -t -f SSID dev wifi list ifname {wlx_interface_val} --rescan no", shell=True, timeout=config.NMCLI_LIST_TIMEOUT).decode("utf-8")
        raw_ssids = result.strip().split('\n')
        
        unique_filtered_ssids = []
        seen_ssids = set()
        for ssid in raw_ssids:
            ssid = ssid.strip()
            if ssid and ssid.startswith(config.WIFI_SSID_PREFIX_FILTER) and ssid not in seen_ssids:
                unique_filtered_ssids.append(ssid)
                seen_ssids.add(ssid)
        scanned_ap_list = unique_filtered_ssids
        print(f"Found and filtered APs: {scanned_ap_list}")

    except subprocess.TimeoutExpired:
        print("ERROR: WiFi scan timed out.")
        return ["Scan Error"]
    except subprocess.CalledProcessError as e:
        print(f"ERROR: nmcli command failed during scan: {e}")
        return ["Scan Error"]
    except Exception as e:
        print(f"ERROR: An issue occurred during WiFi scan: {e}")
        return ["Scan Error"]
    
    if not scanned_ap_list:
        return [f"No {config.WIFI_SSID_PREFIX_FILTER} APs"]
    return scanned_ap_list

def connect_to_wifi(ssid, wlx_interface_val):
    """Attempts to connect to the specified SSID."""
    if not wlx_interface_val:
        print("WARNING: Cannot connect without a WiFi interface.")
        return "No Interface"

    print(f"Connecting to network '{ssid}'...")
    
    try:
        # Ensure device is active, otherwise 'nmcli dev connect' might fail or hang
        subprocess.run(f"nmcli dev set {wlx_interface_val} managed yes", shell=True, check=False, timeout=5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Disconnect if already connected to something else or to ensure a clean state
        subprocess.run(f"nmcli dev disconnect {wlx_interface_val}", shell=True, check=False, timeout=10, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)

        connect_command = f"nmcli dev wifi connect \"{ssid}\" password \"{config.WIFI_PASSWORD}\" ifname {wlx_interface_val}"
        process = subprocess.Popen(connect_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(timeout=config.NMCLI_CONNECT_TIMEOUT)
        stdout_str = stdout.decode('utf-8', errors='ignore').strip()
        stderr_str = stderr.decode('utf-8', errors='ignore').strip()

        if process.returncode == 0 and ("successfully activated" in stdout_str or "Secrets were required" in stdout_str): # "Secrets were required" can indicate an existing successful connection profile was used
            print(f"Successfully initiated connection to '{ssid}'. Verifying IP...")
            time.sleep(5) # Wait for IP address to be assigned
            ip_result_cmd = f"nmcli -g IP4.ADDRESS dev show {wlx_interface_val}"
            ip_result = subprocess.check_output(ip_result_cmd, shell=True, timeout=5).decode("utf-8").strip()
            
            ip_address = ip_result.split('/')[0] if '/' in ip_result else ip_result
            
            if ip_address:
                print(f"IP Address acquired: {ip_address}")
                return ip_address
            else:
                print("WARN: Connected but no IP Address acquired.")
                return "No IP Acquired" # Connected but no IP
        else:
            print(f"ERROR: Failed to connect to '{ssid}'. Return code: {process.returncode}")
            if stdout_str: print(f"nmcli stdout: {stdout_str}")
            if stderr_str: print(f"nmcli stderr: {stderr_str}")
            # Check specific errors if possible
            if "Timeout" in stderr_str or "timeout" in stdout_str :
                 return "Timeout"
            return "Not Connected" # General connection failure
    except subprocess.TimeoutExpired:
        print(f"ERROR: Connection to '{ssid}' command timed out.")
        return "Timeout"
    except subprocess.CalledProcessError as e:
        print(f"ERROR: nmcli command failed during connection attempt: {e}")
        return "Error Occurred"
    except Exception as e:
        print(f"ERROR: During WiFi connection: {e}")
        return "Error Occurred"

def disconnect_wifi(wlx_interface_val, current_connection_status):
    """Disconnects the current WiFi connection."""
    if not wlx_interface_val:
        print("WARNING: Cannot disconnect without a WiFi interface.")
        return "No Interface"
    
    # Check if actually connected or trying to connect based on status
    # (IP address, "Connected", "No IP Acquired" are considered connected states)
    connected_states = ["Connected", "No IP Acquired"]
    is_likely_connected = current_connection_status not in ["Not Connected", "Not Started", "Scanned/Select", "No Interface", "Scanning...", "Timeout", "Error Occurred"] or \
                          any(state == current_connection_status for state in connected_states)


    if is_likely_connected:
        print(f"Disconnecting WiFi from {wlx_interface_val} (current status: {current_connection_status})...")
        try:
            subprocess.run(f"nmcli dev disconnect {wlx_interface_val}", shell=True, check=False, timeout=10, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("WiFi disconnected command issued.")
        except Exception as e:
            print(f"ERROR: While trying to disconnect WiFi: {e}")
    else:
        print(f"No active connection perceived on {wlx_interface_val} to disconnect (status: {current_connection_status}).")
        
    return "Not Connected" # Always return "Not Connected" after a disconnect attempt
