import machine

STANDARD_GRAVITY = 9.806
LIS3DH_ADR = 0x18
CTRL_REG1 = 0x20
CTRL_REG4 = 0x23
CTRL_REG5 = 0x24

BMP388_ADR = 0x76
SCL = machine.Pin(3)
SDA = machine.Pin(2)

import time
import struct

class LIS3DH:
    def __init__(self, i2c, address):
        self.i2c = i2c
        self.addr = address
        self.operating = False

        
    def config_accel(self, value=b'\x38'):
        if self.operating:
            self.disable()
        
        self.i2c.writeto_mem(self.addr, CTRL_REG5, b'\x80')

        time.sleep(0.03)

        self.i2c.writeto_mem(self.addr, CTRL_REG4, b'\x38') # sets device to +-16g and high res
        self.i2c.writeto_mem(self.addr, CTRL_REG1, b'\x47') # sets to 50Hz
    
    def range(self):
        """The range of the accelerometer.

        Could have the following values:

        * RANGE_2_G
        * RANGE_4_G
        * RANGE_8_G
        * RANGE_16_G.

        """
        ctl4 = self.i2c.readfrom_mem(self.addr, CTRL_REG4, 1)
        fifth_and_sixth_bits = (int.from_bytes(ctl4, 'big') >> 3) & 0b11  # Shift right by 3 bits to isolate the 5th and 6th bits, then AND with 0b11 to keep them
        return fifth_and_sixth_bits

    def get_data(self):
        data = self.i2c.readfrom_mem(self.addr, 0x28, 6)
        
        divider = 1365
        
        x, y, z = struct.unpack("<hhh", self.i2c.readfrom_mem(self.addr, 0x28 | 0x80, 6))
        
        x = (x / divider)
        y = (y / divider)
        z = (z / divider)
        
        return (x, y, z)
            


class BMP388:
    def __init__(self, i2c, address):
        self.i2c = i2c
        self.addr = address
        self.pressure_calib = 0
        self.temp_calib = 0
    
    def enable_temp_and_pressure(self):
        self.i2c.writeto_mem(BMP388_ADR, 0x1B, b'\x33')
    
    def calibrate(self):
        # find our compensation coefficient values (this shit is all copied from adafruit's library, don't ask me how it works)
        coeff = self.i2c.readfrom_mem(self.addr, 0x31, 21)
        coeff = struct.unpack("<HHbhhbbHHbbhbb", coeff)
        
        self.temp_calib = (
            coeff[0] / 2**-8.0,  # T1
            coeff[1] / 2**30.0,  # T2
            coeff[2] / 2**48.0,
        )  # T3
        self.pressure_calib = (
            (coeff[3] - 2**14.0) / 2**20.0,  # P1
            (coeff[4] - 2**14.0) / 2**29.0,  # P2
            coeff[5] / 2**32.0,  # P3
            coeff[6] / 2**37.0,  # P4
            coeff[7] / 2**-3.0,  # P5
            coeff[8] / 2**6.0,  # P6
            coeff[9] / 2**8.0,  # P7
            coeff[10] / 2**15.0,  # P8
            coeff[11] / 2**48.0,  # P9
            coeff[12] / 2**48.0,  # P10
            coeff[13] / 2**65.0,
        )  # P11
        
    def enable_temp_and_pressure(self):
        self.i2c.writeto_mem(self.addr, 0x1B, b'\x33')
    
    def toInt(self, data):
        return int.from_bytes(data, 'big')
    
    def getTemperature(self):
        return self.read_temp_and_pressure()[0]

    def getPressure(self):
        return self.read_temp_and_pressure()[1]
    
    def read_temp_and_pressure(self):
        # See if readings are ready
        status = self.i2c.readfrom_mem(self.addr, 0x03, 1)
        #print(toHex(status))
        if (self.toInt(status) & 0x60 != 0x60):
            print("Not ready")
        else:
            # ** If you want to know how this works, don't ask me. I stole all this code from https://github.com/adafruit/Adafruit_CircuitPython_BMP3XX/
            
            # read and bit shift our readings
            data = self.i2c.readfrom_mem(self.addr, 0x04, 6)
            adc_p = data[2] << 16 | data[1] << 8 | data[0]
            adc_t = data[5] << 16 | data[4] << 8 | data[3]
            #print(adc_t)
            
            T1, T2, T3 = self.temp_calib
            
            pd1 = adc_t - T1
            pd2 = pd1 * T2
            
            temperature = pd2 + (pd1 * pd1) * T3 #TEMPERATURE IN C
                    
            # datasheet, sec 9.3 Pressure compensation
            P1, P2, P3, P4, P5, P6, P7, P8, P9, P10, P11 = self.pressure_calib

            pd1 = P6 * temperature
            pd2 = P7 * temperature**2.0
            pd3 = P8 * temperature**3.0
            po1 = P5 + pd1 + pd2 + pd3

            pd1 = P2 * temperature
            pd2 = P3 * temperature**2.0
            pd3 = P4 * temperature**3.0
            po2 = adc_p * (P1 + pd1 + pd2 + pd3)

            pd1 = adc_p**2.0
            pd2 = P9 + P10 * temperature
            pd3 = pd1 * pd2
            pd4 = pd3 + P11 * adc_p**3.0

            pressure = (po1 + po2 + pd4)/100 #PRESSURE IN hPa
            
            return(temperature, pressure)
        
        return(-1, -1) # We only get here if there's an error

