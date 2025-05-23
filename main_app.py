# main_app.py

import time
import signal
# import os 

import config 
import oled_manager
import network_operations
import gpio_input_handler

# --- Application State ---
app_state = {
    "project_running": False,
    "current_page_title": "APs",
    "ap_list": [],
    "selected_ap_index": 0,
    "scroll_offset_ap": 0,
    "connection_status": "Not Started", 
    "ip_address": None, 
    "connected_ssid": None,
    "device_hostname": f"{config.HOSTNAME_PREFIX}XXXX", 
    "wlx_interface": None, 
    "oled_instance": None,
    "encoder_instance": None
}

# --- GPIO Callback Functions (Interacting with App State) ---
def handle_app_rotation(delta):
    """Handles rotary encoder rotation for the application."""
    if not app_state["project_running"] or not app_state["oled_instance"]:
        return

    if app_state["current_page_title"] == "APs":
        if not app_state["ap_list"] or \
           (app_state["ap_list"] and app_state["ap_list"][0] and \
            any(msg in app_state["ap_list"][0] for msg in ["No APs found", "No Interface", "Scan Error", "Scanning...", "Initial Scan..."])):
            return 
        
        max_index = len(app_state["ap_list"]) - 1
        if max_index < 0: return 

        new_index = app_state["selected_ap_index"] + delta
        app_state["selected_ap_index"] = max(0, min(new_index, max_index))
        
        if app_state["selected_ap_index"] < app_state["scroll_offset_ap"]:
            app_state["scroll_offset_ap"] = app_state["selected_ap_index"]
        elif app_state["selected_ap_index"] >= app_state["scroll_offset_ap"] + 4: 
            app_state["scroll_offset_ap"] = app_state["selected_ap_index"] - 3
        
        app_state["scroll_offset_ap"] = max(0, min(app_state["scroll_offset_ap"], len(app_state["ap_list"]) - 4 if len(app_state["ap_list"]) > 4 else 0))
        
        oled_manager.display_ap_page(app_state["current_page_title"], app_state["ap_list"], app_state["selected_ap_index"], app_state["scroll_offset_ap"])

def handle_app_click():
    """Handles rotary encoder button click for the application."""
    if not app_state["project_running"] or not app_state["oled_instance"]:
        return

    if app_state["current_page_title"] == "APs":
        if app_state["ap_list"] and \
           not (app_state["ap_list"][0] and any(msg in app_state["ap_list"][0] for msg in ["No APs found", "No Interface", "Scan Error", "Scanning...", "Initial Scan..."])) and \
           0 <= app_state["selected_ap_index"] < len(app_state["ap_list"]):
            
            selected_ssid_for_connection = app_state["ap_list"][app_state["selected_ap_index"]]
            print(f"Selected AP: {selected_ssid_for_connection}")
            app_state["current_page_title"] = "STATUS"
            app_state["connection_status"] = "Connecting..." 
            app_state["ip_address"] = None 
            app_state["connected_ssid"] = None # Clean SSID and store selected as temporary while connection is tried
            
            oled_manager.display_status_page(
                app_state["current_page_title"],
                app_state["device_hostname"],
                app_state["connection_status"],
                app_state["ip_address"],
                app_state["connected_ssid"] 
            )
            
            connection_result = network_operations.connect_to_wifi(selected_ssid_for_connection, app_state["wlx_interface"])
            
            status_for_line_3 = ""
            actual_ip_for_line_4 = None
            ssid_for_line_5 = None

            defined_non_ip_statuses = [
                "No IP Acquired", "Not Connected", "Timeout", 
                "Error Occurred", "No Interface"
            ]

            if connection_result not in defined_non_ip_statuses and connection_result is not None:
                actual_ip_for_line_4 = connection_result
                status_for_line_3 = "Connected"
                ssid_for_line_5 = selected_ssid_for_connection # Set SSID if connection is succcessful
            else:
                status_for_line_3 = connection_result if connection_result is not None else "Error"
                # ssid_for_line_5 stays as None (unsuccessful connection)
            
            app_state["connection_status"] = status_for_line_3
            app_state["ip_address"] = actual_ip_for_line_4
            app_state["connected_ssid"] = ssid_for_line_5


            oled_manager.display_status_page(
                app_state["current_page_title"],
                app_state["device_hostname"],
                app_state["connection_status"],
                app_state["ip_address"],
                app_state["connected_ssid"]
            )
        else:
            print("No valid AP selected or AP list is empty/status message.")

    elif app_state["current_page_title"] == "STATUS":
        print("Returning to APs page and rescanning...")
        app_state["connection_status"] = network_operations.disconnect_wifi(app_state["wlx_interface"], app_state["connection_status"])
        app_state["ip_address"] = None 
        app_state["connected_ssid"] = None # Clean connected SSID
        app_state["current_page_title"] = "APs"
        
        scan_message = "Scanning..."
        app_state["ap_list"] = [scan_message] 
        app_state["selected_ap_index"] = 0
        app_state["scroll_offset_ap"] = 0
        oled_manager.display_ap_page(app_state["current_page_title"], app_state["ap_list"], app_state["selected_ap_index"], app_state["scroll_offset_ap"])
        
        app_state["ap_list"] = network_operations.scan_wifi_networks(app_state["wlx_interface"])
        oled_manager.display_ap_page(app_state["current_page_title"], app_state["ap_list"], app_state["selected_ap_index"], app_state["scroll_offset_ap"])

def start_project_sequence():
    """Orchestrates the project startup."""
    if app_state["project_running"]:
        print("Project is already running.")
        return

    print("Starting project sequence...")
    if not app_state["oled_instance"]:
        print("CRITICAL ERROR: OLED not available at project start.")
        return
            
    app_state["project_running"] = True
    oled_manager.show_project_starting()

    app_state["wlx_interface"] = network_operations.get_wlx_interface()
    if not app_state["wlx_interface"]:
        oled_manager.show_no_wifi_interface_error()
        time.sleep(3)
        if app_state["oled_instance"]: oled_manager.show_initial_boot_message()
        app_state["project_running"] = False 
        return

    app_state["device_hostname"] = network_operations.set_hostname_on_system(app_state["wlx_interface"])
    network_operations.clear_existing_wifi_connections(app_state["wlx_interface"])
    
    app_state["current_page_title"] = "APs"
    app_state["ip_address"] = None 
    app_state["connected_ssid"] = None # No connected SSID during start-up
    
    scan_message = "Initial Scan..."
    app_state["ap_list"] = [scan_message]
    app_state["selected_ap_index"] = 0
    app_state["scroll_offset_ap"] = 0
    oled_manager.display_ap_page(app_state["current_page_title"], app_state["ap_list"], app_state["selected_ap_index"], app_state["scroll_offset_ap"])

    app_state["ap_list"] = network_operations.scan_wifi_networks(app_state["wlx_interface"])
    app_state["connection_status"] = "Not Connected" 
    oled_manager.display_ap_page(app_state["current_page_title"], app_state["ap_list"], app_state["selected_ap_index"], app_state["scroll_offset_ap"])
    print("Project sequence started.")

def stop_project_sequence():
    """Orchestrates the project shutdown."""
    if not app_state["project_running"]:
        print("Project is not running or already stopped.")
        if app_state["oled_instance"] and not app_state["project_running"]: 
             oled_manager.show_initial_boot_message()
        return

    print("Stopping project sequence...")
    was_running = app_state["project_running"]
    app_state["project_running"] = False 
    
    if was_running and app_state["wlx_interface"]:
        app_state["connection_status"] = network_operations.disconnect_wifi(app_state["wlx_interface"], app_state["connection_status"])
    else:
        app_state["connection_status"] = "Not Connected"

    app_state["ip_address"] = None 
    app_state["connected_ssid"] = None # Clean connected SSID
    
    if app_state["oled_instance"]:
        oled_manager.show_project_stopped()
        time.sleep(2)
        oled_manager.show_initial_boot_message()
    
    print("Project sequence stopped. Press GPIO {} to restart.".format(config.START_BUTTON_GPIO))

# --- Main Execution ---
def main():
    """Main program entry point."""
    print("Raspberry Pi WiFi Manager Project - Modular Version")
    print(f"Use GPIO {config.START_BUTTON_GPIO} switch to start.")
    print(f"Use GPIO {config.STOP_BUTTON_GPIO} switch to stop.")

    app_state["oled_instance"] = oled_manager.init_oled()
    if app_state["oled_instance"]:
         oled_manager.show_initial_boot_message()
    else:
        print("CRITICAL: OLED display could not be initialized.")
        return 

    app_state["encoder_instance"] = gpio_input_handler.setup_gpio(
        rotate_cb=handle_app_rotation,
        click_cb=handle_app_click,
        start_cb=start_project_sequence,
        stop_cb=stop_project_sequence
    )

    if not app_state["encoder_instance"]: 
        print("CRITICAL: GPIO setup failed. Exiting.")
        if app_state["oled_instance"]:
             oled_manager.display_message("ERROR:","GPIO Setup","Failed.","Exiting.")
        return 

    try:
        print("Application running. Press Ctrl+C to exit.")
        while True: 
            signal.pause() 
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Shutting down...")
    except Exception as e:
        print(f"An unexpected error occurred in main loop: {e}")
    finally:
        print("Initiating final cleanup...")
        if app_state["project_running"]:
            stop_project_sequence() 
        
        if app_state["oled_instance"] and not app_state["project_running"]: 
            oled_manager.show_goodbye() 
            time.sleep(1)
            oled_manager.clear_oled_and_stop_scroll() 
        
        gpio_input_handler.cleanup_gpio() 
        print("Program terminated.")

if __name__ == "__main__":
    main()
