import struct
import sys

import hexdump

input_filename = sys.argv[1]

commands = {}
with open("commands.dat", "rb") as infile:
    idx = 0

    infile.seek(0, 2)
    filesize = infile.tell()
    infile.seek(0, 0)

    while infile.tell() < filesize:
        command_name = infile.read(0x10).decode('ascii').strip('\0')
        infile.read(8)
        commands[idx] = command_name
        idx += 1

with open(input_filename, "rb") as infile:
    anim_table_size, packet_table_size, string_table_size, _ = struct.unpack("<HHHH", infile.read(8))

    infile.seek(anim_table_size, 1)
    table2 = infile.read(packet_table_size)

    infile.seek(8, 0)

    for i in range(anim_table_size // 8):
        u1, command_idx, packet_offset, packet_size = struct.unpack("<HHHH", infile.read(8))
        packet_size >>= 3

        # u3 is an offset into table2
        print("%04x %04x %04x %04x | %s" % (u1, command_idx, packet_offset, packet_size, commands[command_idx]))

        c = (((table2[packet_offset] << 5) + table2[packet_offset]) << 2)

        # print("%02x %04x" % (table2[packet_offset], c))

        hexdump.hexdump(table2[packet_offset:packet_offset+packet_size])

    exit(1)

    infile.seek(packet_table_size, 1)

    for i in range(string_table_size // 0x20):
        sprite_filename = infile.read(0x20).decode('shift-jis').strip('\0')
        print(sprite_filename)
