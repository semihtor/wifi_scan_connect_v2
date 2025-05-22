# oled_manager.py

from board import SCL, SDA
import busio
from oled_text import OledText
import config

oled_instance = None

def init_oled():
    """Initializes the OLED display."""
    global oled_instance
    try:
        i2c = busio.I2C(SCL, SDA)
        oled_instance = OledText(i2c, config.OLED_WIDTH, config.OLED_HEIGHT)
        oled_instance.clear()
        oled_instance.text("System Ready", 1)
        oled_instance.text(f"Press GPIO {config.START_BUTTON_GPIO} to", 2)
        oled_instance.text("start project.", 3)
        return oled_instance
    except Exception as e:
        print(f"ERROR: OLED initialization failed: {e}")
        oled_instance = None
        return None

def clear_oled():
    if oled_instance:
        oled_instance.clear()

def display_message(line1, line2=None, line3=None, line4=None):
    if not oled_instance: return
    oled_instance.clear()
    if line1: oled_instance.text(line1, 1)
    if line2: oled_instance.text(line2, 2)
    if line3: oled_instance.text(line3, 3)
    if line4: oled_instance.text(line4, 4)


def display_ap_page(current_page_title_val, ap_list_val, selected_ap_index_val, scroll_offset_ap_val):
    """Displays the APs page on the OLED screen."""
    if not oled_instance: return
    oled_instance.clear()
    oled_instance.text(f"{current_page_title_val}" if current_page_title_val == "APs" else "APs", 1)

    if not ap_list_val:
        oled_instance.text("No APs found", 2)
        oled_instance.text("or filtered", 3)
        return

    displayable_aps = ap_list_val[scroll_offset_ap_val : scroll_offset_ap_val + 4]

    for i, ap_name in enumerate(displayable_aps):
        line_num = i + 2
        prefix = ">" if (i + scroll_offset_ap_val) == selected_ap_index_val else " "
        oled_instance.text(f"{prefix}{ap_name[:15]}", line_num)

def display_status_page(current_page_title_val, device_hostname_val, connection_status_val):
    """Displays the Status page on the OLED screen."""
    if not oled_instance: return
    oled_instance.clear()
    oled_instance.text(f"{current_page_title_val}" if current_page_title_val == "STATUS" else "STATUS", 1)
    oled_instance.text(f"H:{device_hostname_val}", 2)
    oled_instance.text(f"S:{connection_status_val[:14]}", 3)

def show_initial_boot_message():
    if not oled_instance: return
    oled_instance.clear()
    oled_instance.text("System Ready", 1)
    oled_instance.text(f"Press GPIO {config.START_BUTTON_GPIO} to", 2)
    oled_instance.text("start project.", 3)

def show_project_starting():
    if not oled_instance: return
    oled_instance.clear()
    oled_instance.text("Project Starting", 1)

def show_no_wifi_interface_error():
    if not oled_instance: return
    oled_instance.clear()
    oled_instance.text("ERROR:",1)
    oled_instance.text("No USB WiFi!",2)

def show_project_stopped():
    if not oled_instance: return
    oled_instance.clear()
    oled_instance.text("Project Stopped.", 1)

def show_goodbye():
    if not oled_instance: return
    oled_instance.clear()
    oled_instance.text("Goodbye!", 1)

def get_oled_instance():
    return oled_instance