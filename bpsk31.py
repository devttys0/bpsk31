#!/usr/bin/env python
# Code to sample the clock and data pins from a simple BPSK31 demodulator circuit
# via an FTDI FT232R chip in bit-bang mode.
#
# http://www.analogzoo.com/2014/12/amplitude-demodulating-bpsk31
# Craig Heffner
# 2014-12-26

import sys
# It's easiest to use pip to install pylibftdi
import pylibftdi

# Using an FTDI TTL-232R cable:
#   o Clock = bit 0 = orange
#   o Data  = bit 1 = yellow
CLOCK = (1 << 0)
DATA  = (1 << 1)

# PSK31 varicodes from http://www.arrl.org/psk31-spec.
# Not all are correct, found some errors from their site already.
# Note that for lookup simplicity, these codes include the 3 trailing 0 bits:
# two that denote the end-of-character marker, and one that is incurred as a
# resut of the bit-shifting loop below.
lookup = {
            0b1010101011000     : 'NUL',
            0b1011110111000     : 'DLE',
            0b1011011011000     : 'SOH',
            0b1011110101000     : 'DCI',
            0b1011101101000     : 'STX',
            0b1110101101000     : 'DC2',
            0b1101110111000     : 'ETX',
            0b1110101111000     : 'DC3',
            0b1011101011000     : 'EOT',
            0b1101011011000     : 'DC4',
            0b1101011111000     : 'ENQ',
            0b1101101011000     : 'NAK',
            0b1011101111000     : 'ACK',
            0b1101101101000     : 'SYN',
            0b1011111101000     : 'BEL',
            0b1101010111000     : 'ETB',
            0b1011111111000     : '\b',
            0b1101111011000     : 'CAN',
            0b11101111000       : 'HT',
            0b1101111101000     : 'EM',
            0b11101000          : '\r\n',
            0b1110110111000     : 'SUB',
            0b1101101111000     : 'VT',
            0b1101010101000     : 'ESC',
            0b1011011101000     : 'FF',
            0b1101011101000     : 'FS',
            0b11111000          : '\r\n',
            0b1110111011000     : 'GS',
            0b1101110101000     : 'SO',
            0b1011111011000     : 'RS',
            0b1110101011000     : 'SI',
            0b1101111111000     : 'US',
            0b1000              : ' ',
            0b10101101000       : 'C',
            0b111111111000      : '!',
            0b10110101000       : 'D',
            0b101011111000      : '"',
            0b101111111000      : "'",
            0b1110111000        : 'E',
            0b111110101000      : '#',
            0b11011011000       : 'F',
            0b111011011000      : '$',
            0b11111101000       : 'G',
            0b1011010101000     : '%',
            0b101010101000      : 'H',
            0b1010111011000     : '&',
            0b1111111000        : 'I',
            0b111111101000      : 'J',
            0b11111011000       : '(',
            0b101111101000      : 'K',
            0b11110111000       : ')',
            0b11010111000       : 'L',
            0b101101111000      : '*',
            0b10111011000       : 'M',
            0b111011111000      : '+',
            0b11011101000       : 'N',
            0b1110101000        : ',',
            0b10101011000       : 'O',
            0b110101000         : '-',
            0b11010101000       : 'P',
            0b1010111000        : '.',
            0b111011101000      : 'Q',
            0b110101111000      : '/',
            0b10101111000       : 'R',
            0b10110111000       : '0',
            0b1101111000        : 'S',
            0b10111101000       : '1',
            0b1101101000        : 'T',
            0b11101101000       : '2',
            0b101010111000      : 'U',
            0b11111111000       : '3',
            0b110110101000      : 'V',
            0b101011101000      : 'W',
            0b101110111000      : '4',
            0b101110101000      : 'X',
            0b101011011000      : '5',
            0b101111011000      : 'Y',
            0b101101011000      : '6',
            0b1010101101000     : 'Z',
            0b110101101000      : '7',
            0b110101011000      : '8',
            0b110110111000      : '9',
            0b111110111000      : '[',
            0b111111011000      : ']',
            0b11110101000       : ':',
            0b1010111111000     : '^',
            0b110111101000      : ';',
            0b101101101000      : '_',
            0b111101101000      : '<',
            0b1010101000        : '=',
            0b1011011111000     : '/',
            0b111010111000      : '>',
            0b1011000           : 'a',
            0b1010101111000     : '?',
            0b1011111000        : 'b',
            0b1010111101000     : '@',
            0b101111000         : 'c',
            0b1111101000        : 'A',
            0b101101000         : 'd',
            0b11101011000       : 'B',
            0b11000             : 'e',
            0b111101000         : 'f',
            0b10111000          : 's',
            0b1011011000        : 'g',
            0b101000            : 't',
            0b101011000         : 'h',
            0b110111000         : 'u',
            0b1101000           : 'i',
            0b1111011000        : 'v',
            0b111101011000      : 'j',
            0b1101011000        : 'w',
            0b10111111000       : 'k',
            0b11011111000       : 'x',
            0b11011000          : 'l',
            0b1011101000        : 'y',
            0b111011000         : 'm',
            0b111010101000      : 'z',
            0b1111000           : 'n',
            0b1010110111000     : '{',
            0b111000            : 'o',
            0b110111011000      : '|',
            0b111111000         : 'p',
            0b1010110101000     : '}',
            0b110111111000      : 'q',
            0b1011010111000     : '~',
            0b10101000          : 'r',
            0b1110110101000     : 'DEL',
         }

bits = 0
armed = False

with pylibftdi.BitBangDevice() as dev:
    dev.direction = 0
    dev.baudrate = 115200

    try:
        while True:
            # Read the FT232 pin's states
            pins = dev.port

            # Data is read on the falling edge of the clock
            if (pins & CLOCK):
                armed = True
            elif armed:
                armed = False

                # Shift in the next data bit
                bits = (bits << 1) + (pins & DATA)

                # If we've gotten bits and the three lowest bits are clear, that's the end of this character
                if bits and (bits & 0b111) == 0:
                    try:
                        sys.stdout.write(lookup[bits])
                    except Exception as e:
                        #sys.stdout.write('(%s)' % bin(bits))
                        pass

                    sys.stdout.flush()
                    bits = 0
    except KeyboardInterrupt:
        pass

