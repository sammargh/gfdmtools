import argparse
import glob
import hashlib
import os
import struct

from ctypes import c_ulong

class PakDumper:
    def __init__(self, packinfo, encryption):
        self.entries = self.parse_pack_data(packinfo)
        self.packlist = self.generate_packlist()
        self.crc32_tab = self.generate_crc32_table()
        self.encryption = encryption


    def generate_crc32_table(self):
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

        return crc32_tab


    def parse_pack_data(self, filename):
        entries = {}

        with open(filename, "rb") as infile:
            infile.seek(0x10)

            while True:
                md5sum = infile.read(0x10)
                data = infile.read(0x10)

                if not md5sum or not data:
                    break

                key1, key2, packid, offset, filesize = struct.unpack("<IHHII", data)

                entry = {
                    'key1': key1,
                    'key2': key2,
                    'packid': packid,
                    'offset': offset,
                    'filesize': filesize,
                    'md5sum': md5sum,
                }

                entries[key1] = entry

        return entries


    def generate_packlist(self):
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

        return packlist


    def decrypt(self, data, key1, key2):
        rol = lambda val, r_bits: (val << r_bits % 32) & (2 ** 32 - 1) | ((val & (2 ** 32 - 1)) >> (32 - (r_bits % 32)))

        # This is where the slowdown happens when decrypting data.
        # TODO: Rewrite to be faster.
        key = key1
        for i in range(0, int(len(data) / 4) * 4, 4):
            key = rol(key + key2, 3)

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


    def calculate_filename_hash(self, input):
        if input.startswith("data/"):
            input = "/" + input

        if input.startswith("/data/aep"):
            input = input.lower()

        input = bytearray(input, 'ascii')

        crc32_sum = 0xffffffff
        for i in range(len(input)):
            crc32_sum = self.crc32_tab[(crc32_sum & 0xff) ^ input[i]] ^ ((crc32_sum >> 8) & 0xffffffff)

        return ~crc32_sum & 0xffffffff


    def file_exists(self, input):
        filename_hash = self.calculate_filename_hash(input)
        return filename_hash in self.entries


    def get_md5sum(self, data):
        md5 = hashlib.md5()
        md5.update(data)
        return md5.digest()


    def extract_data(self, path):
        filename_hash = self.calculate_filename_hash(path)

        if filename_hash not in self.entries:
            print("Couldn't find entry for", path)
            return False

        entry = self.entries[filename_hash]

        if entry['packid'] > len(self.packlist):
            print("[BAD PACK_ID] pack_id: %d, data_offset: %08x, data_size: %08x, filename: %s" % (entry['packid'], entry['offset'], entry['filesize'], path))
            return False

        packpath = self.packlist[entry['packid']]
        if packpath.startswith('/'):
            packpath = packpath[1:]

        if not os.path.exists(packpath):
            print("Could not find %s" % packpath)
            return

        data = bytearray(open(packpath, "rb").read()[entry['offset']:entry['offset']+entry['filesize']])

        encryption = False
        if self.get_md5sum(data) != entry['md5sum']:
            encryption = True

        if encryption:
            decrypted = self.decrypt(data, entry['key1'], entry['key2'])

        else:
            decrypted = data

        if self.get_md5sum(data) != entry['md5sum']:
            print("Bad checksum for", path)
            return False

        if path.startswith('/'):
            path = path[1:]

        output_path = os.path.join("output", path)

        if not os.path.exists(os.path.dirname(output_path)):
            os.makedirs(os.path.dirname(output_path))

        open(output_path, "wb").write(decrypted)
        return True


def bruteforce_filenames(dumper):
    filenames = []

    templates = [
        "/data/product/music/m%04d/d%04d.sq2",
        "/data/product/music/m%04d/g%04d.sq2",

        "/data/product/music/m%04d/d%04d.sq3",
        "/data/product/music/m%04d/g%04d.sq3",

        "/data/product/music/m%04d/d%04d.seq",
        "/data/product/music/m%04d/g%04d.seq",

        "/data/product/music/m%04d/spu%04dd.vas",
        "/data/product/music/m%04d/spu%04dg.vas",
        "/data/product/music/m%04d/spu%04dd.va2",
        "/data/product/music/m%04d/spu%04dg.va2",
        "/data/product/music/m%04d/spu%04dd.va3",
        "/data/product/music/m%04d/spu%04dg.va3",

        "/data/product/music/m%04d/fre%04d.bin",

        "/data/product/music/m%04d/bgm%04d.mpg",
        "/data/product/music/m%04d/bgm%04d.m2v",
        "/data/product/music/m%04d/bgm%04d.pss",
        "/data/product/music/m%04d/m%04d.mpg",
        "/data/product/music/m%04d/m%04d.m2v",
        "/data/product/music/m%04d/m%04d.pss",

        "/data/product/music/m%04d/i%04ddm.bin",
        "/data/product/music/m%04d/i%04dgf.bin",
        "/data/product/music/m%04d/bgm%04d___k.bin",
        "/data/product/music/m%04d/bgm%04d__bk.bin",
        "/data/product/music/m%04d/bgm%04d_gbk.bin",
        "/data/product/music/m%04d/bgm%04dd__k.bin",
        "/data/product/music/m%04d/bgm%04dd_bk.bin",

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

    for i in range(0, 1100):
        for template in templates:
            path = template % tuple(i for _ in range(template.count("%04d")))

            if dumper.file_exists(path):
                filenames.append(path)

    return filenames


def find_packinfo(path):
    packinfo_paths = glob.glob(os.path.join(path, "**", "packinfo.bin"), recursive=True)

    if packinfo_paths:
        # Shouldn't ever really have more than one packinfo.bin in a normal setup...
        # But my setup is a mess so yeah
        return packinfo_paths[-1]

    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Input folder', required=True)
    parser.add_argument('-o', '--output', help='Output folder (optional)', default="output")

    args = parser.parse_args()

    packinfo_path = find_packinfo(args.input)

    if not packinfo_path:
        print("Couldn't find packinfo.bin in input directory")
        exit(1)

    dumper = PakDumper(packinfo_path, False)
    filenames = bruteforce_filenames(dumper)

    for path in filenames:
        if path.startswith('/'):
            path = path[1:]

        print("Extracting {}...".format(path))
        dumper.extract_data(path)
