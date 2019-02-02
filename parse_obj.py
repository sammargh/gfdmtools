import struct
import sys
import os

with open(sys.argv[1], "rb") as infile:
    infile.seek(0, 2)
    filesize = infile.tell()
    infile.seek(0)

    entry_count = filesize // 0x30

    found_ids = []
    filenames = []
    for i in range(entry_count):
        filename = infile.read(0x1c).decode('shift-jis').strip()
        unk1, unk2, arr_unk1, arr_unk2, arr_unk3, arr_unk4, w, h, arr_unk5, anim_group_id = struct.unpack("<HHHHHHHHHH", infile.read(0x14))

        print("%04d: %s %d %d %d %d %d %d (%d, %d) %d anim_group_id[%d]" % (i, filename, unk1, unk2, arr_unk1, arr_unk2, arr_unk3, arr_unk4, w, h, arr_unk5, anim_group_id))

        if anim_group_id not in found_ids:
            found_ids.append(anim_group_id)
            filenames.append((anim_group_id, unk1, filename))

    for id, id2, filename in sorted(filenames, key=lambda x:x[0]):
        print("%04x %04x" % (id, id2), filename)