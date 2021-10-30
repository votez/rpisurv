#!/usr/bin/python

import cec

if __name__ == '__main__':
    cec.init()
    devices = cec.list_devices()
    for (key, device) in devices.items() :
        print('Device {} osd {}'.format(key, device.osd_string))
    
    if devices[0].is_on():
        print('Turn off')
        devices[0].standby()
    else:
        print('Turn on')
        devices[0].power_on()
    print('mission complete')
