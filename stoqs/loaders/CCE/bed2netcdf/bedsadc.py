# ADC details for the BEDS unit. This must match ads_with_config.c
class ADCConfig(): 
    def __init__(self, channel, name, slope, intercept, units):
        self.channel = channel
        self.name = name
        self.slope = slope
        self.intercept = intercept
        self.units = units

adcConv = [
    ADCConfig(0, "VSys",   12.11, 0.0,   "Batt Volts"),
    ADCConfig(1, "VModem", 12.11, 0.0,   "Batt Volts"),
    ADCConfig(2, "PR-EXT", 50.0, 12.5,   "bar"),
    ADCConfig(3, "PR-INT", 50.0, 12.5,   "psia"),
    ADCConfig(4, "Temp-I", 100.0, 50.0,  "degC"),
    ADCConfig(5, "RelHum", 47.175, 23.82, "%"),
    ADCConfig(6, "??1",    1.0, 0.0,      "ADCCounts"),
    ADCConfig(7, "??2",    1.0, 0.0,      "ADCCounts")
    ]


VREF	= 2.50
def RAW_TO_VOLTS(n):
    return (float(n) * VREF / 65536.0)
def RAW_TO_BATTVOLTS(n):
    return((float(n) * 12.11* VREF / 65536.0))
def VOLTS_TO_BATTVOLTS(f): return (12.11*f)
def VOLTS_TO_TEMP(f): return (100.0*(f-0.5))
def VOLTS_TO_RH(f):   return (50.0*(f-0.5))

BATT_CHAN = 0;
MODEM_MIN_CHAN = 1;
EXT_PRESS_CHAN = 2;
INT_PRESS_CHAN = 3;
TEMP_CHAN = 4;
HUMIDITY_CHAN = 5;


def adcEngValue(channel, counts):
    if channel > len(adcConv):
        raise KeyError
    adcConvChan = adcConv[channel]
    engval = (adcConvChan.slope * RAW_TO_VOLTS(counts)) - adcConvChan.intercept
    return engval, adcConvChan.units

