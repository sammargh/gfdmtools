import struct
import sys
import os

with open(sys.argv[1], "rb") as infile:
    infile.seek(0, 2)
    filesize = infile.tell()
    infile.seek(0)

    entry_count = filesize // 0x30

    for i in range(entry_count):
        filename = infile.read(0x20).decode('shift-jis').strip()
        unk1_1, unk1_2, w, h, unk2_1, anim_group_id, colors, cluts = struct.unpack("<HHHHHHHH", infile.read(0x10))
        w *= 4

        print("%04d: %s (%d, %d) resolution[(%d, %d)] %d anim_group_id[%d] colors[%d] cluts[%d]" % (i, filename, unk1_1, unk1_2, w, h, unk2_1, anim_group_id, colors, cluts))