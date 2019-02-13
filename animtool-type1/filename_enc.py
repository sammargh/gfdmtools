import struct
import sys

def encrypt_string(filename):
    key = "Encrypt using this default key!!"

    chksum = sum([ord(c) for c in filename])
    buffer = [ord(c) for c in filename[:8]]

    # Pad buffer to at least 8 numbers
    for _ in range(0, 8 - len(buffer)):
        chksum2 = chksum + len(filename)
        idx = (chksum2) - ((chksum2 >> 4) << 4)
        buffer.append(ord(key[16 + idx]))

    # Add key to buffer, and remaining characters above 8 to the buffer in a circular fashion
    for idx in range(len(filename)):
        buffer[idx % 8] += ord(key[idx])

        if idx >= 8:
            buffer[idx % 8] += ord(filename[idx])

    # Scramble buffer
    for i in range(8):
        idx = chksum - ((chksum >> 5) << 5)
        idx2 = (idx + 1) % 0x20

        s1 = ord(key[idx]) & 7
        s2 = ord(key[idx2]) & 7

        a1 = buffer[s1]
        buffer[s1] = buffer[s2]
        buffer[s2] = a1

        chksum = (idx2 + 1) % 0x20

    # Create actual encrypted filename
    output = []
    for i in range(8):
        c = (buffer[i] * 0x4EC4EC4F) >> 32
        c1 = (c // 8)
        c = (c1 * 12 + c1) * 2
        output.append(chr(buffer[i] - c + 0x61))

    return "".join(output)

idx_mapping = {}
with open("BG_LIST.BIN", "rb") as infile:
    infile.seek(0, 2)
    filesize = infile.tell()
    infile.seek(0, 0)
    idx = 0
    while infile.tell() < filesize:
        song_id = struct.unpack("<H", infile.read(2))[0]
        idx_mapping[idx] = song_id
        idx += 1

with open("PCCARD1.DAT", "rb") as infile:
    infile.seek(0x8000, 0)
    file_count = struct.unpack("<I", infile.read(4))[0]

    infile.seek(0x8010, 0)
    for idx in range(file_count):
        string = infile.read(0x10).decode('shift-jis').strip('\0')
        infile.read(0x10)

        if idx not in idx_mapping:
            idx_mapping[idx] = -1

        print("[%04d] %-20s -> DATA6/%s.DAT" % (idx_mapping[idx], string, encrypt_string(string).upper()))