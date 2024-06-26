import utime
import select
import math
import starlight_mini
import json
import time
import gpio
import sys
import machine
from machine import Pin, PWM

defaultJson = '{"startupMode":0,"features":[{"data":{"action":"none"},"id":0,"type":"PYRO"}]}'

time.sleep(3)

baseline_altitude = 0
def getAltitude(pressure):
    return (145366.45 * (1.0 - pow(pressure / 1013.25, 0.190284))) # returns altitude in feet


# ----------HARDWARE------------
# pyro channels and GPIO pins are treated the same in firmware
outputs = [gpio.GPIO(0, 21)]
leds = [Pin(23, Pin.OUT)]
buzzers = [Pin(16, Pin.OUT)]

# -- HARDWARE FUNCTIONS --
def toggleLeds():
    for i in range(len(leds)):
        if leds[i].value() == 0:
            leds[i].value(1)
        else:
            leds[i].value(0)

def buzz_blocking(duration):
    for i in range(len(buzzers)):
        buzzers[i].value(1)
        time.sleep(duration)
        buzzers[i].value(0)


connected = False
mode = 0

poll_obj = select.poll()
poll_obj.register(sys.stdin,1)

read_data = []

# ON STARTUP do something
# startup modes:
# 0 - programming mode/default mode
# 1 - flight mode
file = None
x = ""

try:
    file = open("data.json", "r")
except:
    file = open("data.json", "w")
    file.write(defaultJson)
    file.close()
    file = open("data.json", "r")

x = file.read()
x = x.replace("'", '"')
y = 0
try:
    y = json.loads(x)
except:
    print("defaulting to startupMode 0")
    y = json.loads(defaultJson)
mode = y["startupMode"]

# Set our pyro channel settings

try:
    for i in range(len(y["features"])):
        print(y["features"][i]["type"])
        if y["features"][i]["type"] == "PYRO" or y["features"][i]["type"] == "GPIO": # gpio is included for "emulate pyro charge"
            action = y["features"][i]["data"]["action"]
            if action == "none":
                outputs[i].setTrigger(0)
            if action == "main":
                outputs[i].setFireLength(12.5 * 5)
                if y["features"][i]["data"]["apogee"] == True:
                    outputs[i].setTrigger(1)
                else:   
                    outputs[i].setTrigger(2)
                    outputs[i].setCustom(y["features"][i]["data"]["height"])
            if action == "drogue": # drogue only has one option: apogee
                outputs[i].setTrigger(1)
                outputs[i].setFireLength(12.5 * 5) # 5 seconds
            if action == "custom": # custom: this is where things get fun :)
                outputs[i].setTrigger(y["features"][i]["data"]["trigger"])
                outputs[i].setCustom(y["features"][i]["data"]["value"])
                outputs[i].setFireLength(y["features"][i]["data"]["time"] * 12.5)
            if action == "output": # output - we either put in LEDs or buzzers
                print("output!")
                if y["features"][i]["data"]["data"]["action"] == "buzzer":
                    print("buzzer found")
                    buzzers.append(Pin(y["features"][i]["data"]["pin"], Pin.OUT))
                if y["features"][i]["data"]["data"]["action"] == "led":
                    leds.append(Pin(y["features"][i]["data"]["pin"], Pin.OUT))

except:
    print("error lmao")
    toggleLeds()
    time.sleep(0.1)
    toggleLeds()
    time.sleep(0.1)
    toggleLeds()
    time.sleep(0.1)
    toggleLeds()
            

       
# outputs[0].setTrigger(y["features"][0]["data"]["action"])
# outputs[1].setTrigger(y["features"][1]["data"]["action"])

# Clean up files
file.close()
time.sleep(0.25)

# two short beeps to signal board is on
buzz_blocking(0.1)
time.sleep(0.25)
buzz_blocking(0.1)

while mode == 0:
    # Programming Mode
    
    # Read serial
    while poll_obj.poll(0):
        read_data.append(sys.stdin.read(1))
    
    if not connected:
        for i in range(len(read_data)):
            # 0x11 is start byte then next byte determines "type" of operation. 0x12 means successfully connected
            if read_data[i] == '\x11':
                if read_data[i+1] == '\x12':
                    toggleLeds()
                    connected = True
                    read_data = []

                    # send curent data.json to MissionControl
                    data_file = open('data.json', 'r')
                    count = 0
                    while True:
                        chunk = data_file.read(1)
                        if chunk == "": # if chunk is empty
                            break
                        print(chunk, end="")
                        count += 1
                    
                    data_file.close()
                    
                    buzz_blocking(0.1)
                    utime.sleep(0.25)
                    toggleLeds()
                    break
                    
    
        # Searching for connection. sd is sl mini's code to send
        print("sd")
        utime.sleep(0.25)

    if connected:
        writing_data = False
        data_to_write = []
        for i in range(len(read_data)):
            # 0x11 is start byte then next byte determines "type" of operation. 0x13 means writing data
            if writing_data:
                data_to_write.append(str(read_data[i]))
            if read_data[i] == '\x11':
                if read_data[i+1] == '\x13':
                    writing_data = True
        if writing_data:
            toggleLeds()
            data_to_write[0] = "" # get rid of the x13 that appears for some reason
            file = open("data.json", "w")
            file.write(''.join(data_to_write))
            file.close()
            utime.sleep(0.05)
            toggleLeds()
            file_check = open("data.json", "r")
            try:
                json.loads(file_check.read())
                writing_data = False
                read_data = []
            except:
                pass
            file_check.close()
      
    if connected:
        for i in range(len(read_data)):
            # 0x11 is start byte then next byte determines "type" of operation. 0x14 means ready to recieve
            if writing_data:
                data_to_write.append(str(read_data[i]))
            if read_data[i] == '\x11':
                if read_data[i+1] == '\x14':
                    file = open('flight_data.txt', 'r')
                    count = 0
                    while True:
                        chunk = file.read(1)
                        if "b" in chunk and count > 1: # count greater than one in order to avoid stopping read at the start
                            break
                        print(chunk, end="")
                        count += 1

    if connected:
        for i in range(len(read_data)):
            # 0x11 is start byte then next byte determines "type" of operation. 0x16 means disconnect
            if writing_data:
                data_to_write.append(str(read_data[i]))
            if read_data[i] == '\x11':
                if read_data[i+1] == '\x16':
                    connected = False
                    toggleLeds()
                    time.sleep(0.25)
                    toggleLeds()



i2c = machine.I2C(1, scl=machine.Pin(3), sda=machine.Pin(2), freq=9600)

accel = starlight_mini.LIS3DH(i2c, 0x18) # create our LIS3DH object
accel.config_accel()

temp = starlight_mini.BMP388(i2c, 0x76) # create our BMP388 object
temp.enable_temp_and_pressure() # enable our sensors
temp.calibrate() # calibrate our sensors

# temp.setGroundPressure(temp.getPressure())


accelX = 0
accelY = 0
accelZ = 0

file = open("flight_data.txt", "w")
file.write('b')
count = 0

event = 0

data_timer = 0
landing_timer = 0
emergency_landing_timer = 0

apoapsis = 10000
apoapsis_timeout = 0
reached_apoapsis = False
pressure_values = []
baseline_pressure = 0
launched = False
burnout = False
landed = False
setAvg = False

limiter = time.ticks_ms()
lastTime = time.ticks_ms()
hz = 0

baseline_pressure = temp.getPressure()

time.sleep(0.25)
buzz_blocking(1) # buzz to make sure we know that we're in launch mode
time.sleep(0.5)
buzz_blocking(1) # buzz to make sure we know that we're in launch mode
time.sleep(0.5)
buzz_blocking(1) # buzz to make sure we know that we're in launch mode

# Switch back to startupMode 0 RIGHT BEFORE starting logging
x = x.replace('"startupMode":1', '"startupMode":0')
fl = open("data.json", "w")
fl.write(x)
fl.close()
while mode == 1: # our main loop    
    lastTime = time.ticks_ms()
    data = accel.get_data()

    # gyr.get_acceleration()
    count += 1
    hz += 1
    
    gpevent = gpio.getEvent()
    if gpevent > 0:
        event = gpevent
    
    # Raw accelaration values switched to resemble SL values
    accelX = data[0] * -1 # + math.sin(f.pitch * (math.pi/180))
    accelY = data[1] * -1 # - math.cos(f.pitch * (math.pi/180)) * math.sin(f.roll * (math.pi/180))
    accelZ = data[2] # - math.cos(f.pitch * (math.pi/180)) * math.cos(f.roll * (math.pi/180))
    
    
    # Pressure averaging
    pressure = temp.getPressure()
    
    pressure_values.append(pressure)
    
    if len(pressure_values) > 5:
        pressure_values.pop(0)
        
    avg_pressure = 0
    for i in range(len(pressure_values)):
        avg_pressure += pressure_values[i]
    
    avg_pressure = avg_pressure / len(pressure_values)
    
    
    # Apogee detection
    if avg_pressure - pressure > 0.05:
        apoapsis = avg_pressure
        apoapsis_timeout = 0
    elif abs(avg_pressure - apoapsis) > 0.1 and len(pressure_values) > 4:
        if apoapsis == 10000:
            apoapsis = avg_pressure
        apoapsis_timeout += 1
    else:
        apoapsis_timeout = 0
        
    if len(pressure_values) > 4 and not setAvg:
        baseline_pressure = avg_pressure
        baseline_altitude = getAltitude(avg_pressure)
        setAvg = True
        
        
    if apoapsis_timeout > 2 and not reached_apoapsis and launched and altitude - baseline_altitude > 15:
        reached_apoapsis = True
        print("apoapsis")
        gpio.runTrigger(outputs, 1, 0)
        event = 2

    
    altitude = getAltitude(avg_pressure)
    
    if len(pressure_values) < 5:
        altitude = 0
        baseline_altitude = 0
    
    # Launch detection
    if (accelY > 3 or altitude - baseline_altitude > 10) and not launched:
        print("launch")
        gpio.runTrigger(outputs, 5, 0)
        event = 13
        launched = True

    # Burnout detection
    if accelY <= 0 and launched and not burnout:
        print("burnout")
        gpio.runTrigger(outputs, 7, 0)
        event = 15
        burnout = True

    # Landing detection
    if altitude - baseline_altitude < 20 and not landed and reached_apoapsis:
        landing_timer += 1
    else:
        landing_timer = 0

    # Emergency landing detection (if the board gets stuck in a tree, etc)
    if altitude - baseline_altitude < 200 and not landed and reached_apoapsis:
        emergency_landing_timer += 1

    if landing_timer > 50 or emergency_landing_timer > 4000: # after 50 data cycles where altitude is < 20 feet, or after 4000 data cycles where altitude is < 200 ft
        gpio.runTrigger(outputs, 9, 0)
        event = 17
        print("Landed")
        landed = True
        
    # Log data
    if baseline_altitude != 0 and data_timer < 100: # if we're ready to go then we should start collecting data
        toggleLeds()
        if landed:
            data_timer += 1
        if data_timer == 99:
            print("Shutting off data collection. Landing was detected.")
        file.write(str(event) + ',' + str(time.ticks_ms()) + ',' + str(altitude - baseline_altitude) + ',' + str(temp.getTemperature()) + ',' + str(accelX) + ',' + str(accelY) + ',' + str(accelZ) + ':')
    
    # Save logged data
    if count % 50 == 0 and data_timer < 151:
        file.close()
        file = open("flight_data.txt", "a")
        
    event = 0
    
    gpio.updateTimeouts()
    gpio.checkForRuns(outputs, altitude - baseline_altitude, reached_apoapsis, accelX, accelY, accelZ)
    

    limiter = time.ticks_ms()
    # Loop control
    time.sleep(((limiter - lastTime - 80) * -1)/1000) # 80 = loop every 80 ms = 12.5hz
    limiter = time.ticks_ms()

    
    hz = 1/((limiter - lastTime)/1000)
#     print(hz)