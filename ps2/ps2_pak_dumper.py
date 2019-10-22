import argparse
import glob
import hashlib
import os
import struct

from ctypes import c_ulong

class PakDumper:
    def __init__(self, packinfo, demux, fast):
        self.entries = self.parse_pack_data(packinfo)
        self.packlist = self.generate_packlist()
        self.crc32_tab = self.generate_crc32_table()
        self.demux = demux
        self.fast = fast


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


    def calculate_filename_hash_crc16_cs(self, data):
        crc16_ccitt_table = [
            0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
            0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
            0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
            0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
            0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
            0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
            0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
            0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
            0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
            0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
            0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
            0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
            0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
            0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
            0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
            0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
            0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
            0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
            0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
            0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
            0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
            0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
            0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
            0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
            0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
            0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
            0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
            0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3a92,
            0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
            0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
            0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
            0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0,
        ]

        checksum = 0

        for b in bytearray(data, "ascii"):
            checksum = ((checksum << 8) & 0xff00 ^ crc16_ccitt_table[((checksum >> 8) & 0xff) ^ b]) & 0xffff

        return checksum & 0xffff


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

                if key1 in entries and entries[key1]['key2'] == key2:
                    print("Found key already:", entries[key1])
                    continue

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
        if self.fast:
            # Uses a Cython module for fast decryption
            import pakdec
            pakdec.decrypt(data, len(data), key1, key2)
            return data

        key = key1

        for i in range(0, int(len(data) / 4) * 4, 4):
            key = self.rol(key + key2, 3)

            data[i] ^= key & 0xff
            data[i + 1] ^= (key >> 8) & 0xff
            data[i + 2] ^= (key >> 16) & 0xff
            data[i + 3] ^= (key >> 24) & 0xff

        i += 4

        key = self.rol(key + key2, 3)
        parts = [key & 0xff, (key >> 8) & 0xff, (key >> 16) & 0xff, (key >> 24) & 0xff]
        for j in range(len(data) - i):
                data[i] ^= parts[j]

        return data


    def file_exists(self, input):
        filename_hash = self.calculate_filename_hash(input)
        filename_hash_crc16 = self.calculate_filename_hash_crc16(input)
        filename_hash_crc16_2 = self.calculate_filename_hash_crc16_cs(input)
        return filename_hash in self.entries and self.entries[filename_hash]['key2'] in [filename_hash_crc16, filename_hash_crc16_2]


    def get_md5sum(self, data):
        md5 = hashlib.md5()
        md5.update(data)
        return md5.digest()


    def extract_data(self, path, input_path, output_path):
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

        packpath = os.path.join(input_path, packpath)

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

        output_path = os.path.join(output_path, path)

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

        "/data/product/movie/music/mv%04d.m2v",
    ]

    for i in range(0, 3000):
        for template in templates:
            path = template % tuple(i for _ in range(template.count("%04d")))

            if dumper.file_exists(path):
                filenames.append(path)

        for j in range(0, 10):
            for path in ["/data/product/music/m%04d/dm_lesson%01d.va2" % (i, j), "/data/product/music/m%04d/gt_lesson%01d.va2" % (i, j)]:
                if dumper.file_exists(path):
                    filenames.append(path)

    for i in range(0, 100):
        for j in range(0, 100):
            for ext in ['va2', 'va3']:
                path = "/data/product/music/system/gfv%d_v%02d.%s" % (i, j, ext)

                if dumper.file_exists(path):
                    filenames.append(path)

        for ext in ['va2', 'va3']:
            path = "/data/product/music/system/gfv%d_se.%s" % (i, ext)
            if dumper.file_exists(path):
                filenames.append(path)

            path = "/data/product/music/system/gfv_v%02d.%s" % (i, ext)
            if dumper.file_exists(path):
                filenames.append(path)

    possible_filenames = [
        "/data/product/music/system/gfv_se.va2",
        "/data/product/music/system/gfv_se.va3",
        "/data/product/music/course_info.bin",
        "/data/product/music/jp_title.bin",
        "/data/product/music/music_info.bin",
        "/data/product/music/net_id.bin",
        "/data/pack/packinfo.bin",
        "/data/product/music/system/se.va2",
        "/data/product/music/system/ealogo_gf.pss",
        "/dev/nvram/config.xml",
        "/dev/nvram/network.xml",
        "/BISLPM-66575gfdmv2/gfdm.ico",
        "/BISLPM-66575gfdmv2/icon.sys",
        "/data/product/icon/gfdm.ico",
        "/data/product/icon/icon.sys",
        "/data/product/music/mdb.bin",
        "/data/product/music/mdb.xml",
        "/data/product/music/mdb_xg.xml",
        "/data/product/music/mdb_xg.bin",
        "/data/product/music/mdbe.bin",
        "/data/product/music/mdbe.xml",
        "/data/product/music/mdbe_xg.xml",
        "/data/product/music/mdbe_xg.bin",
        "/data/product/mdb.bin",
        "/data/product/mdb.xml",
        "/data/product/mdb_xg.xml",
        "/data/product/mdb_xg.bin",
        "/data/product/mdbe.bin",
        "/data/product/mdbe.xml",
        "/data/product/mdbe_xg.xml",
        "/data/product/mdbe_xg.bin",
        "/data/product/xml/mdbe_xg.xml",
        "/data/product/xml/mdbe_xg.bin",
        "/data/product/xml/mdbe.bin",
        "/data/product/xml/mdbe.xml",
        "/data/product/xml/mdbe_xg.xml",
        "/data/product/xml/mdbe_xg.bin",
        "/data/product/xml/mdbe.bin",
        "/data/product/xml/mdbe.xml",
        "/data/product/font/font16x16x8/0_0.img",
        "/data/product/font/font16x16x8/0_1.img",
        "/data/product/font/font16x16x8/1_0.img",
        "/data/product/font/font16x16x8/1_1.img",
        "/data/product/font/font16x16x8/1_2.img",
        "/data/product/font/font16x16x8/1_3.img",
        "/data/product/font/font16x16x8/2_0.img",
        "/data/product/font/font16x16x8/2_1.img",
        "/data/product/font/font16x16x8/2_2.img",
        "/data/product/font/font16x16x8/2_3.img",
        "/data/product/font/font16x16x8/3_0.img",
        "/data/product/font/font16x16x8/3_1.img",
        "/data/product/font/font16x16x8/3_2.img",
        "/data/product/font/font16x16x8/3_3.img",
        "/data/product/font/DFHSG7.TTC",
    ]

    for path in possible_filenames:
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
    parser.add_argument('-f', '--fast', help='Use Cython decryption code', default=False, action="store_true")

    args = parser.parse_args()

    packinfo_path = find_packinfo(args.input)

    if not packinfo_path:
        print("Couldn't find packinfo.bin in input directory")
        exit(1)

    dumper = PakDumper(packinfo_path, args.demux, args.fast)

    filenames = bruteforce_filenames(dumper)

    for path in filenames:
        if path.startswith('/'):
            path = path[1:]

        print("Extracting {}...".format(path))
        dumper.extract_data(path, args.input, args.output)
