import struct
import sys
import os
import math

def calc_bpm(timestamp, val1=300, val2=240):
    return round(((val1 / 4) / (timestamp / 4)) * val2)

with open(sys.argv[1], "rb") as infile:
    magic, music_id, unk1, unk2, event_count, note_count, unk3 = struct.unpack("<4sHBBHHI", infile.read(0x10))

    if magic != b"GSQ1":
        print("Not a valid GSQ file")
        exit(1)

    print(magic, music_id, event_count, note_count)

    last_timestamp = None
    cur_bpm = None

    measures = 0
    while True:
        timestamp, param1, param2, cmd = struct.unpack("<IIHH", infile.read(12))
        param3 = cmd & 0xff0f
        cmd &= 0x00f0

        if cmd == 0x10:
            if last_timestamp is not None:
                cur_bpm = calc_bpm(timestamp - last_timestamp)

            last_timestamp = timestamp
            measures += 1

        print("%08x %08x %04x %04x %04x" % (timestamp, param1, param2, cmd, param3), cur_bpm)

        if timestamp == 0xffffffff:
            break

    print(measures)