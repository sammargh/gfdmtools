import binascii
from ctypes import c_ulong, c_int, c_long, c_uint
import hexdump
import os
import struct

crc32_tab = []
crc32_constant = 0xEDB88320
for i in range(0, 256):
    crc = i
    for j in range(0, 8):
        if crc & 0x00000001:
            crc = int(c_ulong(crc >> 1).value) ^ crc32_constant
        else:
            crc = int(c_ulong(crc >> 1).value)

    crc32_tab.append(crc)

def get_pack_list(data):
    file_count = struct.unpack("<I", data[0:4])[0]

    paths = []
    for i in range(file_count):
        path = data[4+(i*0x58):4+(i*0x58)+0x40].decode('ascii').replace('\0','')
        paths.append(path)

    return paths

def decrypt(data, key1, key2):
    rol = lambda val, r_bits: \
        (val << r_bits%32) & (2**32-1) | \
    ((val & (2**32-1)) >> (32-(r_bits%32)))

    # This is where the slowdown happens when decrypting data.
    # TODO: Rewrite to be faster.
    key = key1
    for i in range(0, int(len(data) / 4) * 4, 4):
        key = rol(key + key2, 3)
        #print("key: %08x, idx: %08x" % (key, i))

        a,b,c,d = struct.unpack("<BBBB", struct.pack("I", key))
        data[i] ^= a
        data[i + 1] ^= b
        data[i + 2] ^= c
        data[i + 3] ^= d

    key = rol(key + key2, 3)
    remaining_key = struct.unpack("<BBBB", struct.pack("I", key))

    for i in range(len(data) - (int(len(data) / 4) * 4)):
        data[(int(len(data) / 4) * 4) + i] ^= remaining_key[i]

    return data


packdata = bytearray(open("data/pack_v3/packinfo.bin","rb").read())
# packlist = get_pack_list(open("data/finfolist.bin","rb").read())

packlist = []

cur_folder = 0
for i in range(0, 1000):
    if (i % 30) == 0 and i > 0:
        cur_folder += 1


    p1 = "data/pack/d%03d/pack%04d.pak" % (cur_folder, i)
    p2 = "data/pack_v3/d%03d/pack%04d.pak" % (cur_folder, i)

    if os.path.exists(p2):
        packlist.append(p2)

    else:
        packlist.append(p1)

def get_filedata(path, check_exists=False):
    output = []

    if path.startswith("data/"):
        path = "/" + path

    if path.startswith("/data/aep"):
        path = path.lower()

    output = bytearray(path, 'ascii')

    sum = 0xffffffff
    for i in range(len(output)):
        #print("%02x" % ((sum & 0xff) ^ output[i]))
        sum = crc32_tab[(sum & 0xff) ^ output[i]] ^ ((sum >> 8) & 0xffffffff)

    crc32_hash = ~sum & 0xffffffff

    #print(path)
    #print("%08x" % crc32_hash)

    data = packdata
    b = struct.pack("<I", crc32_hash)

    def extract_data(path, data, offset):
        key1, key2 = struct.unpack("<IH", data[offset:offset+6])
        pack_id, data_offset, data_size = struct.unpack("<HII", data[offset + 6:offset + 6 + 10])
        # print("pack_id: %d, data_offset: %08x, data_size: %08x" % (pack_id, data_offset, data_size))
        #print(packlist[pack_id])

        if pack_id > len(packlist):
            print("[BAD PACK_ID] pack_id: %d, data_offset: %08x, data_size: %08x, filename: %s" % (pack_id, data_offset, data_size, path))
            return False

        if check_exists:
            return True

        packpath = packlist[pack_id]
        if packpath.startswith('/'):
            packpath = packpath[1:]

        if not os.path.exists(packpath):
            print("Could not find %s" % packpath)
            return

        data = bytearray(open(packpath, "rb").read()[data_offset:data_offset+data_size])

        # decrypted = decrypt(data, key1, key2)
        decrypted = data

        if path.startswith('/'):
            path = path[1:]

        output_path = os.path.join("output", path)

        if not os.path.exists(os.path.dirname(output_path)):
            os.makedirs(os.path.dirname(output_path))

        open(output_path, "wb").write(decrypted)
        return True

    offset = data.find(b)
    while offset >= 0:
        if extract_data(path, data, offset):
            return True

        offset = data.find(b, offset+1)

    if check_exists:
        return False



found_songdata = []
for i in range(0, 3000):
    templates = [
        "/data/product/music/m%04d/d%04d.sq2",
        "/data/product/music/m%04d/g%04d.sq2",

        "/data/product/music/m%04d/spu%04dd.va2",
        "/data/product/music/m%04d/spu%04dg.va2",
        "/data/product/music/m%04d/spu%04dd.va3",
        "/data/product/music/m%04d/spu%04dg.va3",

        "/data/product/music/m%04d/bgm%04d.m2v",
        "/data/product/music/m%04d/bgm%04d.pss",
        "/data/product/music/m%04d/m%04d.m2v",
        "/data/product/music/m%04d/m%04d.pss",

        "/data/product/music/m%04d/i%04ddm.bin",
        "/data/product/music/m%04d/i%04dgf.bin",
        "/data/product/music/m%04d/bgm%04d___k.bin",
        "/data/product/music/m%04d/bgm%04d__bk.bin",
        "/data/product/music/m%04d/bgm%04d_gbk.bin",
        "/data/product/music/m%04d/bgm%04dd__k.bin",
        "/data/product/music/m%04d/bgm%04dd_bk.bin",

        "/data/product/music/m%04d/i%04ddm.pss",
        "/data/product/music/m%04d/i%04dgf.pss",
        "/data/product/music/m%04d/bgm%04d___k.pss",
        "/data/product/music/m%04d/bgm%04d__bk.pss",
        "/data/product/music/m%04d/bgm%04d_gbk.pss",
        "/data/product/music/m%04d/bgm%04dd__k.pss",
        "/data/product/music/m%04d/bgm%04dd_bk.pss",

        "/data/product/music/m%04d/i%04ddm.at3",
        "/data/product/music/m%04d/i%04dgf.at3",
        "/data/product/music/m%04d/bgm%04d___k.at3",
        "/data/product/music/m%04d/bgm%04d__bk.at3",
        "/data/product/music/m%04d/bgm%04d_gbk.at3",
        "/data/product/music/m%04d/bgm%04dd__k.at3",
        "/data/product/music/m%04d/bgm%04dd_bk.at3",
        "/data/product/music/m%04d/b%04d___k.at3",
        "/data/product/music/m%04d/b%04d__bk.at3",
        "/data/product/music/m%04d/b%04d_gbk.at3",
        "/data/product/music/m%04d/b%04dd__k.at3",
        "/data/product/music/m%04d/b%04dd_bk.at3",
    ]

    for template in templates:
        path = template % tuple(i for _ in range(template.count("%04d")))
        if get_filedata(path, True):
            found_songdata.append(path)

for path in found_songdata:
    if path.startswith('/'):
        path = path[1:]

    if os.path.exists(os.path.join("output", path)):
        continue

    print("Extracting {}...".format(path))
    get_filedata(path)