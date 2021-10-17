import argparse
import socket
from gpiozero import LED
from time import sleep


def no_internet(led_pin):
    led_pin.on()
    sleep(1)
    led_pin.off()
    sleep(1)
    led_pin.on()
    sleep(1)
    led_pin.off()
    sleep(1)
    led_pin.on()


def internet(led_pin):
    led_pin.off()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--pin", default="14", type=int, help="PIN number as gpiozero")
    ap.add_argument("-pb", "--blue", default="15", type=int, help="Blue pin")
    ap.add_argument("-pg", "--green", default="18", type=int, help="Green pin")
    ap.add_argument("-i", "--host", default="unix.stackexchange.com", type=str, help="host to resolve")
    ap.add_argument("-l", "--local", default="192.", type=str, help="local network first byte of IPv4")
    args = vars(ap.parse_args())
    led = LED(args.get("pin"))
    blue = LED(args.get("blue"))
    green = LED(args.get("green"))
    host = args.get("host")
    local = args.get("local")
    try:
        ip = socket.gethostbyname(host)
        if ip.startswith(local):
            no_internet(led)
        else:
            internet(led)
    except socket.gaierror as e:
        no_internet(led)
