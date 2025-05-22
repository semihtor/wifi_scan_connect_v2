# main_app.py

import time
import signal
import os # For potential os.system calls if ever needed

import config # Project specific configurations
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
    "connection_status": "Not Started", # Initial status
    "device_hostname": f"{config.HOSTNAME_PREFIX}XXXX", # Will be set dynamically
    "wlx_interface": None, # Will be set dynamically
    "oled_instance": None,
    "encoder_instance": None
}

# --- GPIO Callback Functions (Interacting with App State) ---
def handle_app_rotation(delta):
    """Handles rotary encoder rotation for the application."""
    if not app_state["project_running"] or not app_state["oled_instance"]:
        return

    if app_state["current_page_title"] == "APs":
        if not app_state["ap_list"]:
            return
        
        max_index = len(app_state["ap_list"]) - 1
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
        if app_state["ap_list"] and 0 <= app_state["selected_ap_index"] < len(app_state["ap_list"]):
            selected_ssid = app_state["ap_list"][app_state["selected_ap_index"]]
            
            # Avoid trying to connect to placeholder/error messages
            if selected_ssid not in ["Scan Error", f"No {config.WIFI_SSID_PREFIX_FILTER} APs", "No Interface"]:
                print(f"Selected AP: {selected_ssid}")
                app_state["current_page_title"] = "STATUS"
                app_state["connection_status"] = "Connecting..."
                oled_manager.display_status_page(app_state["current_page_title"], app_state["device_hostname"], app_state["connection_status"])
                
                connection_result = network_operations.connect_to_wifi(selected_ssid, app_state["wlx_interface"])
                app_state["connection_status"] = connection_result
                oled_manager.display_status_page(app_state["current_page_title"], app_state["device_hostname"], app_state["connection_status"])
            else:
                print("Invalid AP selection (placeholder or error message).")
        else:
            print("No AP to select or index error.")

    elif app_state["current_page_title"] == "STATUS":
        print("Returning to APs page and rescanning...")
        app_state["connection_status"] = network_operations.disconnect_wifi(app_state["wlx_interface"], app_state["connection_status"])
        app_state["current_page_title"] = "APs"
        app_state["connection_status"] = "Scanning..." # Update status before scan
        oled_manager.display_ap_page(app_state["current_page_title"], ["Scanning..."], 0, 0) # Show scanning message
        
        app_state["ap_list"] = network_operations.scan_wifi_networks(app_state["wlx_interface"])
        app_state["selected_ap_index"] = 0
        app_state["scroll_offset_ap"] = 0
        if app_state["connection_status"] == "Scanning...": # If status was not updated by disconnect (e.g. was already "Not Connected")
             app_state["connection_status"] = "Scanned/Select"
        oled_manager.display_ap_page(app_state["current_page_title"], app_state["ap_list"], app_state["selected_ap_index"], app_state["scroll_offset_ap"])


# --- Project Flow Control Functions ---
def start_project_sequence():
    """Orchestrates the project startup."""
    if app_state["project_running"]:
        print("Project is already running.")
        return

    print("Starting project sequence...")
    if not app_state["oled_instance"]:
        app_state["oled_instance"] = oled_manager.init_oled()
        if not app_state["oled_instance"]:
            print("CRITICAL ERROR: Cannot start project without OLED display.")
            return
    
    app_state["project_running"] = True
    oled_manager.show_project_starting()

    app_state["wlx_interface"] = network_operations.get_wlx_interface()
    if not app_state["wlx_interface"]:
        oled_manager.show_no_wifi_interface_error()
        time.sleep(3)
        oled_manager.show_initial_boot_message()
        app_state["project_running"] = False # Ensure project stops
        return

    app_state["device_hostname"] = network_operations.set_hostname_on_system(app_state["wlx_interface"])
    network_operations.clear_existing_wifi_connections(app_state["wlx_interface"])
    
    app_state["current_page_title"] = "APs"
    app_state["connection_status"] = "Initial Scan..."
    oled_manager.display_ap_page(app_state["current_page_title"], [app_state["connection_status"]], 0,0)


    app_state["ap_list"] = network_operations.scan_wifi_networks(app_state["wlx_interface"])
    app_state["selected_ap_index"] = 0
    app_state["scroll_offset_ap"] = 0
    if app_state["connection_status"] == "Initial Scan...": # If status was not updated by disconnect (e.g. was already "Not Connected")
         app_state["connection_status"] = "Scanned/Select"

    oled_manager.display_ap_page(app_state["current_page_title"], app_state["ap_list"], app_state["selected_ap_index"], app_state["scroll_offset_ap"])
    print("Project sequence started.")


def stop_project_sequence():
    """Orchestrates the project shutdown."""
    if not app_state["project_running"]:
        print("Project is already stopped.")
        return

    print("Stopping project sequence...")
    app_state["project_running"] = False
    app_state["connection_status"] = network_operations.disconnect_wifi(app_state["wlx_interface"], app_state["connection_status"])
    
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
    # Pass the application-specific handlers to the GPIO setup
    app_state["encoder_instance"] = gpio_input_handler.setup_gpio(
        rotate_cb=handle_app_rotation,
        click_cb=handle_app_click,
        start_cb=start_project_sequence,
        stop_cb=stop_project_sequence
    )

    if not app_state["oled_instance"] :
        print("OLED not available. GPIOs might be set up but project cannot fully run.")
        # Decide if to proceed or exit if OLED is critical for GPIO setup as well
    if not app_state["encoder_instance"]: # Check if GPIO setup itself failed
        print("GPIO setup failed. Exiting.")
        if app_state["oled_instance"]: # Show on OLED if available
             oled_manager.display_message("ERROR:","GPIO Setup","Failed.","Exiting.")
        return # Exit if GPIOs are critical

    try:
        signal.pause() # Keep the main thread alive to listen for GPIO events
    except KeyboardInterrupt:
        print("\nExiting with Ctrl+C...")
    finally:
        if app_state["project_running"]:
            network_operations.disconnect_wifi(app_state["wlx_interface"], app_state["connection_status"])
        if app_state["oled_instance"]:
            oled_manager.show_goodbye()
            time.sleep(1)
            oled_manager.clear_oled()
        gpio_input_handler.cleanup_gpio() # Clean up GPIO resources
        print("Program terminated.")

if __name__ == "__main__":
    # Note: Run with sudo and the virtual environment's python interpreter:
    # sudo /path/to/your/venv/bin/python3 main_app.py
    main()