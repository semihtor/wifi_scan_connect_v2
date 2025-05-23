# config.py

# --- Project Settings ---
WIFI_PASSWORD = "password"
START_BUTTON_GPIO = 16
STOP_BUTTON_GPIO = 26
ROTARY_ENCODER_A_GPIO = 17
ROTARY_ENCODER_B_GPIO = 18
ROTARY_ENCODER_BUTTON_GPIO = 27

# OLED Display
OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_LINE_MAX_CHARS = 18  # Max characters per line on OLED
OLED_SCROLL_DELAY = 0.30  # Scroll speed in seconds

# Network
HOSTNAME_PREFIX = "RPi0-"
WIFI_INTERFACE_PREFIX = "wlx"
WIFI_SSID_PREFIX_FILTER = "QW-"

# Timeouts
NMCLI_RESCAN_TIMEOUT = 15  # seconds
NMCLI_LIST_TIMEOUT = 10    # seconds
NMCLI_CONNECT_TIMEOUT = 45 # seconds
