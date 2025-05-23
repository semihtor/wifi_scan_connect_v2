# oled_manager.py

from board import SCL, SDA
import busio
from oled_text import OledText # Make sure oled-text is installed with "pip install oled-text"
import threading
import time
import config

oled_instance = None
active_scrolling_threads = [] 

def init_oled():
    """Initializes the OLED display."""
    global oled_instance
    try:
        i2c = busio.I2C(SCL, SDA)
        oled_instance = OledText(i2c, config.OLED_WIDTH, config.OLED_HEIGHT, auto_show=True)
        oled_instance.clear()
        return oled_instance
    except Exception as e:
        print(f"ERROR: OLED initialization failed: {e}")
        oled_instance = None
        return None

def _stop_all_scrolling_threads():
    """Stops all active scrolling threads."""
    global active_scrolling_threads
    for thread, stop_event in active_scrolling_threads:
        stop_event.set()
    for thread, _ in active_scrolling_threads:
        if thread.is_alive():
            thread.join(timeout=0.1) 
    active_scrolling_threads = []

def _scrolling_thread_target(label, value_to_scroll, line_num, value_display_width, stop_event):
    """Target function for a scrolling text thread."""
    if not oled_instance: return

    separator = "   " 
    extended_value = value_to_scroll + separator
    idx = 0

    while not stop_event.is_set():
        scrolling_part = extended_value[idx : idx + value_display_width]
        
        if len(scrolling_part) < value_display_width: 
            remaining = value_display_width - len(scrolling_part)
            scrolling_part += extended_value[:remaining]
        
        current_line_text = f"{label}{scrolling_part}"
        try:
            oled_instance.text(current_line_text.ljust(config.OLED_LINE_MAX_CHARS), line_num)
        except Exception:
            pass 
            
        if stop_event.wait(timeout=config.OLED_SCROLL_DELAY):
            break
        
        idx += 1
        if idx >= (len(value_to_scroll) + len(separator)): 
            idx = 0

def _display_line(label, value, line_num, current_page_title=None, is_selected_ap_line=False, is_title=False):
    """Displays a line of text on the OLED with page-specific scrolling rules."""
    if not oled_instance: return

    label = str(label) if label is not None else ""
    value = str(value) if value is not None else ""
    original_value_len = len(value)

    value_display_width = config.OLED_LINE_MAX_CHARS - len(label)
    if value_display_width < 0: value_display_width = 0

    scroll_if_value_longer_than = value_display_width 
    can_this_line_scroll = True 

    if current_page_title == "STATUS":
        if line_num == 2: # Hostname: 
            scroll_if_value_longer_than = 8
        elif line_num == 3: # Status: 
            scroll_if_value_longer_than = 10
        elif line_num == 4: # IP: 
            scroll_if_value_longer_than = 14
        elif line_num == 5: # SSID: 
            scroll_if_value_longer_than = 12
    elif current_page_title == "APs":
        if not is_selected_ap_line:
            can_this_line_scroll = False

    if is_title or not can_this_line_scroll or original_value_len <= scroll_if_value_longer_than:
        display_value = value
        if not can_this_line_scroll and original_value_len > value_display_width:
            display_value = value[:value_display_width] 
        
        full_line = f"{label}{display_value}"
        oled_instance.text(full_line.ljust(config.OLED_LINE_MAX_CHARS), line_num)
    else:
        stop_event = threading.Event()
        thread = threading.Thread(
            target=_scrolling_thread_target,
            args=(label, value, line_num, value_display_width, stop_event),
            daemon=True
        )
        active_scrolling_threads.append((thread, stop_event))
        thread.start()

def clear_oled_and_stop_scroll():
    _stop_all_scrolling_threads()
    if oled_instance:
        oled_instance.clear()

def display_message(line1, line2=None, line3=None, line4=None, line5=None):
    """Displays up to 5 lines of static text, scrolling if necessary by default rule."""
    clear_oled_and_stop_scroll()
    if not oled_instance: return
    
    lines_to_display = [line1, line2, line3, line4, line5]
    for i, text_line in enumerate(lines_to_display):
        # OLED lines are 1-indexed
        oled_line_num = i + 1
        if text_line is not None: 
             _display_line("", str(text_line), oled_line_num)
        else: 
             _display_line("", "", oled_line_num) # Clear the line


def display_ap_page(current_page_title_val, ap_list_val, selected_ap_index_val, scroll_offset_ap_val):
    """Displays the APs page on the OLED screen (up to 4 APs + title)."""
    clear_oled_and_stop_scroll()
    if not oled_instance: return

    title_display_label = "" 
    _display_line(title_display_label, "[~~~~~~~APs~~~~~~]", 1, current_page_title=current_page_title_val, is_title=True)

    if not ap_list_val or not ap_list_val[0] or any(msg in ap_list_val[0] for msg in ["No APs found", "No Interface", "Scan Error", "Scanning...", "Initial Scan..."]):
        status_message = ap_list_val[0] if (ap_list_val and ap_list_val[0]) else "No APs found"
        _display_line("  ", status_message, 2, current_page_title=current_page_title_val)
        for i in range(3, 6): 
            _display_line("  ", "", i, current_page_title=current_page_title_val) 
        return

    displayable_aps_on_page = ap_list_val[scroll_offset_ap_val : scroll_offset_ap_val + 4] 

    for i, ap_name in enumerate(displayable_aps_on_page):
        oled_line_num = i + 2 
        is_selected = (i + scroll_offset_ap_val) == selected_ap_index_val
        prefix_label = "> " if is_selected else "  "
        _display_line(prefix_label, ap_name, oled_line_num, current_page_title=current_page_title_val, is_selected_ap_line=is_selected)
    
    num_displayed_aps = len(displayable_aps_on_page)
    for i in range(num_displayed_aps, 4): 
         oled_line_num_to_clear = i + 2
         _display_line("  ", "", oled_line_num_to_clear, current_page_title=current_page_title_val)


def display_status_page(current_page_title_val, device_hostname_val, connection_status_text, ip_address_text=None, connected_ssid_text=None):
    """Displays the Status page on the OLED screen. IP and SSID are on new lines if successful/available."""
    clear_oled_and_stop_scroll()
    if not oled_instance: return
    
    title_display_label = "" 
    _display_line(title_display_label, "[~~~~~STATUS~~~~~]", 1, current_page_title=current_page_title_val, is_title=True)
    
    _display_line("Hostname: ", device_hostname_val, 2, current_page_title=current_page_title_val)
    _display_line("Status: ", connection_status_text, 3, current_page_title=current_page_title_val)
    
    ip_val_to_show = ip_address_text if ip_address_text else "N/A"
    _display_line("IP: ", ip_val_to_show, 4, current_page_title=current_page_title_val)

    ssid_val_to_show = connected_ssid_text if connected_ssid_text else "N/A"
    _display_line("SSID: ", ssid_val_to_show, 5, current_page_title=current_page_title_val) # Using "ID:" for SSID label
    
    # Clear line 6 if your OLED screen might show remnants from a previous 6-line display
    # But not needed since oled-text can't handle more than 5 lines on a 128x64 display with the currently used layout and font
    # _display_line("  ","",6, current_page_title=current_page_title_val)


def show_initial_boot_message():
    # display_message now handles up to 5 lines. Line 4 will be empty string.
    display_message("System Ready", f"Press GPIO {config.START_BUTTON_GPIO} to", "start project.", "")

def show_project_starting():
    display_message("Project Starting", "", "", "")

def show_no_wifi_interface_error():
    display_message("ERROR:", "No USB WiFi!", "", "")

def show_project_stopped():
    display_message("Project Stopped.", "", "", "")

def show_goodbye():
    display_message("Goodbye!", "", "", "")

def get_oled_instance():
    return oled_instance
