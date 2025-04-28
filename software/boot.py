####
# BOOT FILE FOR ESP32C3OLED module
####

from time import sleep_ms
from machine import PWM, Pin, I2C
from ssd1306 import SSD1306_I2C
 
led = Pin(8, Pin.OUT)
b_boot = Pin(0, Pin.IN, Pin.PULL_UP)
b_config = Pin(4, Pin.IN, Pin.PULL_UP)
# Setup display
i2c = I2C(0, sda=Pin(5), scl=Pin(6))
display = SSD1306_I2C(70, 40, i2c)

def display_msg(display, msg):
    display.fill(0)
    display.text("bouvy_drawer", 0, 0, 1)
    y = 10
    for line in msg.split('\n'):
        display.text(line, 0, y, 1)
        y += 10
    display.show()

#blink
led.value(1)
sleep_ms(100)
led.value(0)
sleep_ms(100)
#blink
led.value(1)
sleep_ms(100)
led.value(0)
sleep_ms(100)
#blink
led.value(1)
sleep_ms(100)
led.value(0)
sleep_ms(100)

if b_boot.value() == 0 :
    display_msg(display,"bootmode")
    pass

elif b_config.value() == 0: 
    display_msg(display,"configmode")
    import config_mode

# else :
#     display_msg(display,"mainmode")
#     import main_mode


