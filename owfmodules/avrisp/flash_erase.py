import time

from octowire_framework.module.AModule import AModule
from octowire.gpio import GPIO
from octowire.spi import SPI
from owfmodules.avrisp.device_id import DeviceID


class FlashErase(AModule):
    def __init__(self, owf_config):
        super(FlashErase, self).__init__(owf_config)
        self.meta.update({
            'name': 'AVR write flash memory',
            'version': '1.0.0',
            'description': 'Module to write the flash memory of an AVR device using the ISP protocol.',
            'author': 'Jordan Ovrè / Ghecko <jovre@immunit.ch>, Paul Duncan / Eresse <pduncan@immunit.ch>'
        })
        self.options = {
            "spi_bus": {"Value": "", "Required": True, "Type": "int",
                        "Description": "The octowire SPI bus (0=SPI0 or 1=SPI1)", "Default": 0},
            "reset_line": {"Value": "", "Required": True, "Type": "int",
                           "Description": "The octowire GPIO used as the Reset line", "Default": 0},
            "spi_baudrate": {"Value": "", "Required": True, "Type": "int",
                             "Description": "set SPI baudrate (1000000 = 1MHz) maximum = 50MHz", "Default": 1000000},
        }
        self.dependencies.append("owfmodules.avrisp.device_id>=1.0.0")

    def get_device_id(self, spi_bus, reset_line, spi_baudrate):
        device_id_module = DeviceID(owf_config=self.config)
        # Set DeviceID module options
        device_id_module.options["spi_bus"]["Value"] = spi_bus
        device_id_module.options["reset_line"]["Value"] = reset_line
        device_id_module.options["spi_baudrate"]["Value"] = spi_baudrate
        device_id_module.owf_serial = self.owf_serial
        device_id = device_id_module.run(return_value=True)
        return device_id

    def erase(self, spi_interface, reset, device):
        erase_cmd = b'\xac\x80\x00\x00'
        enable_mem_access_cmd = b'\xac\x53\x00\x00'

        # Drive reset low
        reset.status = 0

        self.logger.handle("Enable Memory Access...", self.logger.INFO)
        # Drive reset low
        reset.status = 0
        # Enable Memory Access
        spi_interface.transmit(enable_mem_access_cmd)
        time.sleep(0.5)

        # Send erase command and wait N ms
        self.logger.handle("Erasing the flash memory...", self.logger.INFO)
        spi_interface.transmit(erase_cmd)
        time.sleep(int(device["erase_delay"]) // 1000)

        # Drive reset high
        reset.status = 1
        self.logger.handle("Flash memory successfully erased.", self.logger.SUCCESS)

    def process(self):
        spi_bus = self.options["spi_bus"]["Value"]
        reset_line = self.options["reset_line"]["Value"]
        spi_baudrate = self.options["spi_baudrate"]["Value"]

        device = self.get_device_id(spi_bus, reset_line, spi_baudrate)
        if device is None:
            return

        spi_interface = SPI(serial_instance=self.owf_serial, bus_id=spi_bus)
        reset = GPIO(serial_instance=self.owf_serial, gpio_pin=reset_line)

        # Configure SPI with default phase and polarity
        spi_interface.configure(baudrate=spi_baudrate)
        # Configure GPIO as output
        reset.direction = GPIO.OUTPUT

        # Active Reset is low
        reset.status = 1

        # Erase the target chip
        self.erase(spi_interface, reset, device)

    def run(self, return_value=False):
        """
        Main function.
        Erase the flash memory of an AVR device.
        :return: Nothing.
        """
        # If detect_octowire is True then Detect and connect to the Octowire hardware. Else, connect to the Octowire
        # using the parameters that were configured. It sets the self.owf_serial variable if the hardware is found.
        self.connect()
        if not self.owf_serial:
            return
        try:
            self.process()
            if return_value:
                return True
        except ValueError as err:
            self.logger.handle(err, self.logger.ERROR)
            if return_value:
                return False
        except Exception as err:
            self.logger.handle("{}: {}".format(type(err).__name__, err), self.logger.ERROR)
            if return_value:
                return False
