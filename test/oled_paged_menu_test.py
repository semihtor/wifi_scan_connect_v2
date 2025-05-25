from board import SCL, SDA
import busio
from gpiozero import RotaryEncoder, Button
from oled_text import OledText
import time
import signal

# Setup I2C and OLED
i2c = busio.I2C(SCL, SDA)
oled = OledText(i2c, 128, 64)

# Pages and items
pages = {
    "Page 1": ["Line 1", "Line 2", "Line 3", "Line 4", "Line 5", "Line 6"],
    "Page 2": ["Line A", "Line B", "Line C", "Line D", "Line E", "Line F"],
}
page_titles = list(pages.keys())
current_page_index = 0

# Scrolling state
selected_index = 0  # Starts at header
scroll_offset = 0   # For managing visible window (first visible item in list)

# Rotary encoder and button
encoder = RotaryEncoder(a=17, b=18, max_steps=0)
button = Button(27)

def render_menu():
    oled.clear()
    current_page_title = page_titles[current_page_index]
    items = pages[current_page_title]

    # Line 0: Page title (selectable)
    title_line = f">{current_page_title}" if selected_index == 0 else current_page_title
    oled.text(title_line, 1)

    # Determine which items to show (up to 4 at a time)
    visible_items = items[scroll_offset:scroll_offset+4]
    for i, item in enumerate(visible_items):
        actual_index = i + 1  # OLED line index
        item_index = i + 1 + scroll_offset  # Full list index (1-based due to title)
        marker = ">" if selected_index == item_index else " "
        oled.text(marker + item, actual_index + 1)

def on_rotate():
    global selected_index, scroll_offset

    delta = round(encoder.steps)
    encoder.steps = 0  # Reset for next delta

    current_page_title = page_titles[current_page_index]
    items = pages[current_page_title]
    max_index = len(items)  # Title is index 0

    new_index = selected_index + delta
    new_index = max(0, min(new_index, max_index))  # Clamp

    if new_index != selected_index:
        selected_index = new_index

        # Adjust scroll window
        if selected_index > 0:
            if selected_index - 1 < scroll_offset:
                scroll_offset = selected_index - 1
            elif selected_index - scroll_offset > 4:
                scroll_offset = selected_index - 4

        render_menu()

def on_click():
    global current_page_index, selected_index, scroll_offset
    if selected_index == 0:
        current_page_index = (current_page_index + 1) % len(page_titles)
        selected_index = 0
        scroll_offset = 0
        render_menu()

# Attach event handlers
encoder.when_rotated = on_rotate
button.when_pressed = on_click

# Initial render
render_menu()

# Keep script running
signal.pause()
