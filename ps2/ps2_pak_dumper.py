import argparse
import glob
import hashlib
import os
import struct

from ctypes import c_ulong

class PakDumper:
    def __init__(self, packinfo, demux):
        self.entries = self.parse_pack_data(packinfo)
        self.packlist = self.generate_packlist()
        self.crc32_tab = self.generate_crc32_table()
        self.demux = demux


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


    def calculate_filename_hash_crc16(self, data):
        crc16_ccitt_table_reverse = [
            0x0000, 0x1189, 0x2312, 0x329B, 0x4624, 0x57AD, 0x6536, 0x74BF,
            0x8C48, 0x9DC1, 0xAF5A, 0xBED3, 0xCA6C, 0xDBE5, 0xE97E, 0xF8F7,
            0x1081, 0x0108, 0x3393, 0x221A, 0x56A5, 0x472C, 0x75B7, 0x643E,
            0x9CC9, 0x8D40, 0xBFDB, 0xAE52, 0xDAED, 0xCB64, 0xF9FF, 0xE876,
            0x2102, 0x308B, 0x0210, 0x1399, 0x6726, 0x76AF, 0x4434, 0x55BD,
            0xAD4A, 0xBCC3, 0x8E58, 0x9FD1, 0xEB6E, 0xFAE7, 0xC87C, 0xD9F5,
            0x3183, 0x200A, 0x1291, 0x0318, 0x77A7, 0x662E, 0x54B5, 0x453C,
            0xBDCB, 0xAC42, 0x9ED9, 0x8F50, 0xFBEF, 0xEA66, 0xD8FD, 0xC974,
            0x4204, 0x538D, 0x6116, 0x709F, 0x0420, 0x15A9, 0x2732, 0x36BB,
            0xCE4C, 0xDFC5, 0xED5E, 0xFCD7, 0x8868, 0x99E1, 0xAB7A, 0xBAF3,
            0x5285, 0x430C, 0x7197, 0x601E, 0x14A1, 0x0528, 0x37B3, 0x263A,
            0xDECD, 0xCF44, 0xFDDF, 0xEC56, 0x98E9, 0x8960, 0xBBFB, 0xAA72,
            0x6306, 0x728F, 0x4014, 0x519D, 0x2522, 0x34AB, 0x0630, 0x17B9,
            0xEF4E, 0xFEC7, 0xCC5C, 0xDDD5, 0xA96A, 0xB8E3, 0x8A78, 0x9BF1,
            0x7387, 0x620E, 0x5095, 0x411C, 0x35A3, 0x242A, 0x16B1, 0x0738,
            0xFFCF, 0xEE46, 0xDCDD, 0xCD54, 0xB9EB, 0xA862, 0x9AF9, 0x8B70,
            0x8408, 0x9581, 0xA71A, 0xB693, 0xC22C, 0xD3A5, 0xE13E, 0xF0B7,
            0x0840, 0x19C9, 0x2B52, 0x3ADB, 0x4E64, 0x5FED, 0x6D76, 0x7CFF,
            0x9489, 0x8500, 0xB79B, 0xA612, 0xD2AD, 0xC324, 0xF1BF, 0xE036,
            0x18C1, 0x0948, 0x3BD3, 0x2A5A, 0x5EE5, 0x4F6C, 0x7DF7, 0x6C7E,
            0xA50A, 0xB483, 0x8618, 0x9791, 0xE32E, 0xF2A7, 0xC03C, 0xD1B5,
            0x2942, 0x38CB, 0x0A50, 0x1BD9, 0x6F66, 0x7EEF, 0x4C74, 0x5DFD,
            0xB58B, 0xA402, 0x9699, 0x8710, 0xF3AF, 0xE226, 0xD0BD, 0xC134,
            0x39C3, 0x284A, 0x1AD1, 0x0B58, 0x7FE7, 0x6E6E, 0x5CF5, 0x4D7C,
            0xC60C, 0xD785, 0xE51E, 0xF497, 0x8028, 0x91A1, 0xA33A, 0xB2B3,
            0x4A44, 0x5BCD, 0x6956, 0x78DF, 0x0C60, 0x1DE9, 0x2F72, 0x3EFB,
            0xD68D, 0xC704, 0xF59F, 0xE416, 0x90A9, 0x8120, 0xB3BB, 0xA232,
            0x5AC5, 0x4B4C, 0x79D7, 0x685E, 0x1CE1, 0x0D68, 0x3FF3, 0x2E7A,
            0xE70E, 0xF687, 0xC41C, 0xD595, 0xA12A, 0xB0A3, 0x8238, 0x93B1,
            0x6B46, 0x7ACF, 0x4854, 0x59DD, 0x2D62, 0x3CEB, 0x0E70, 0x1FF9,
            0xF78F, 0xE606, 0xD49D, 0xC514, 0xB1AB, 0xA022, 0x92B9, 0x8330,
            0x7BC7, 0x6A4E, 0x58D5, 0x495C, 0x3DE3, 0x2C6A, 0x1EF1, 0x0F78
        ]

        checksum = 0xffff

        for b in bytearray(data, "ascii"):
            checksum = ((checksum >> 8) ^ crc16_ccitt_table_reverse[(checksum ^ b) & 0xff]) & 0xffff

        return ~checksum & 0xffff


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
                    'key1': key1, # CRC32 filename hash
                    'key2': key2, # CRC16 filename hash
                    'packid': packid,
                    'offset': offset,
                    'filesize': filesize,
                    'md5sum': md5sum,
                }

                if key1 in entries:
                    print("Found key already")
                    exit(1)

                entries[key1] = entry

        return entries


    def generate_packlist(self):
        packlist = []

        cur_folder = 0
        for i in range(0, 3000):
            if (i % 30) == 0 and i > 0:
                cur_folder += 1


            p1 = "data/pack/d%03d/pack%04d.pak" % (cur_folder, i)
            p2 = "data/pack_v3/d%03d/pack%04d.pak" % (cur_folder, i)

            if os.path.exists(p2):
                packlist.append(p2)

            else:
                packlist.append(p1)

        return packlist


    def rol(self, val, r_bits):
        return (val << r_bits) & 0xFFFFFFFF | ((val & 0xFFFFFFFF) >> (32 - r_bits))


    def decrypt(self, data, key1, key2):
        # This is where the slowdown happens when decrypting data.
        # TODO: Rewrite to be faster.
        key = key1

        for i in range(0, int(len(data) / 4) * 4, 4):
            key = self.rol(key + key2, 3)
            a, b, c, d = struct.unpack("<BBBB", struct.pack("I", key))

            data[i] ^= a
            data[i + 1] ^= b
            data[i + 2] ^= c
            data[i + 3] ^= d

        i += 4

        parts = struct.unpack("<BBBB", struct.pack("I", self.rol(key + key2, 3)))
        for j in range(len(data) - i):
                data[i] ^= parts[j]

        return data


    def file_exists(self, input):
        filename_hash = self.calculate_filename_hash(input)
        filename_hash_crc16 = self.calculate_filename_hash_crc16(input)
        return filename_hash in self.entries and self.entries[filename_hash]['key2'] == filename_hash_crc16


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

        if path.startswith('/'):
            path = path[1:]

        output_path = os.path.join("output", path)

        if not os.path.exists(os.path.dirname(output_path)):
            os.makedirs(os.path.dirname(output_path))

        open(output_path, "wb").write(decrypted)

        if self.demux and os.path.splitext(output_path)[1].lower() == ".pss":
            from pss_demux import demux_pss
            demux_pss(output_path, os.path.dirname(output_path))

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

    for i in range(0, 3000):
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
    parser.add_argument('-d', '--demux', help='Demux PSS files', default=False, action="store_true")

    args = parser.parse_args()

    packinfo_path = find_packinfo(args.input)

    if not packinfo_path:
        print("Couldn't find packinfo.bin in input directory")
        exit(1)

    dumper = PakDumper(packinfo_path, args.demux)

    filenames = bruteforce_filenames(dumper)

    for path in filenames:
        if path.startswith('/'):
            path = path[1:]

        print("Extracting {}...".format(path))
        dumper.extract_data(path)
