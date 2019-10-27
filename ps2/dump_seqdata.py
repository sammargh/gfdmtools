import argparse
import ctypes
import os


def get_filename_hash(filename):
    def rshift(val, n): return val>>n if val >= 0 else (val+0x100000000)>>n
    def lshift(val, n): return val<<n if val >= 0 else (val+0x100000000)<<n

    filename_hash = 0

    for i, c in enumerate(filename.encode('ascii')):
        filename_hash = (((rshift(filename_hash, 23)) | (lshift(filename_hash, 5))) + c) & 0x0fffffff

    return filename_hash & 0xffffffff

class DecodeGfdm:
    def __init__(self, data):
        self.data = data

        self.unk = int.from_bytes(data[:4], 'little')
        self.cur_offset = 4
        self.cur_bit = -1

        self.tree = self.build_tree()
        self.build_starts()
        self.build_lookups()

    def get_bit(self):
        def rshift(val, n): return val>>n if val >= 0 else (val+0x100000000)>>n

        if self.cur_bit < 0:
            self.cur_bit = 7
            self.orig_flag = self.data[self.cur_offset]
            self.flag = ctypes.c_byte(self.data[self.cur_offset]).value
            self.cur_offset += 1

        ret = rshift(self.flag, self.cur_bit) & 1
        self.cur_bit -= 1

        return ret

    def get_byte(self):
        cur_idx = 0x100

        while True:
            bit = self.get_bit()
            cur_idx = [self.lookup_l, self.lookup_r][bit][cur_idx]

            if cur_idx < 0x100:
                break

        return cur_idx


    def build_tree(self):
        tree = bytearray(0x100)
        tree_idx = 0
        s3 = 0

        if self.data[self.cur_offset] == 0:
            return self.data

        while tree_idx < 0x100:
            if self.get_bit() == 0:
                tree[tree_idx] = s3
                tree_idx += 1

            else:
                s1 = 1

                cnt = 0
                while self.get_bit() == 0:
                    cnt += 1

                while cnt > 0:
                    s1 = (s1 << 1) | self.get_bit()
                    cnt -= 1

                s3 ^= s1
                tree[tree_idx] = s3
                tree_idx += 1

        return tree

    def build_starts(self):
        self.statistics = [0] * 16
        for c in self.tree:
            if c >= 0x11:
                raise Exception("Invalid code")

            else:
                self.statistics[c] += 1

        self.starts = [0] * 16
        for i in range(1, 16-1):
            self.starts[i+1] = (self.starts[i] + self.statistics[i]) * 2

        self.offsets = [0] * len(self.tree)
        for idx in range(len(self.starts)):
            for i, c in enumerate(self.tree):
                if c == idx:
                    self.offsets[i] += self.starts[idx]
                    self.starts[idx] += 1

    def build_lookups(self):
        lookup_r = [0] * 0x10000
        lookup_l = [0] * 0x10000

        cur_idx = len(self.tree)
        next_idx = len(self.tree) + 1
        lookup_r[cur_idx] = lookup_l[cur_idx] = -1
        lookup_r[next_idx] = lookup_l[next_idx] = -1

        for i, c in enumerate(self.tree):
            if c == 0:
                continue

            cur_idx = len(self.tree)

            is_right = False
            for j in range(0, c):
                is_right = (self.offsets[i] >> (c - j - 1)) & 1

                if j + 1 == c:
                    break

                if is_right:
                    a1 = lookup_r[cur_idx]
                    if a1 == -1:
                        lookup_r[cur_idx] = next_idx

                    else:
                        cur_idx = a1

                else:
                    a1 = lookup_l[cur_idx]
                    if a1 == -1:
                        lookup_l[cur_idx] = next_idx

                    else:
                        cur_idx = a1

                if a1 == -1:
                    lookup_l[next_idx] = -1
                    lookup_r[next_idx] = -1
                    cur_idx = next_idx
                    next_idx += 1

            if is_right:
                lookup_r[cur_idx] = i

            else:
                lookup_l[cur_idx] = i

        self.lookup_r = lookup_r
        self.lookup_l = lookup_l

    def decode(self):
        output = []

        decomp_size = int.from_bytes(self.data[:4], 'little')
        for i in range(decomp_size):
            output.append(self.get_byte() & 0xff)

        return bytearray(output)


def decode_lz(input_data):
    output = bytearray()
    input_data = bytearray(input_data)
    idx = 0
    distance = 0
    control = 0

    while True:
        control >>= 1

        if (control & 0x100) == 0:
            control = input_data[idx] | 0xff00
            idx += 1

        data = input_data[idx]
        idx += 1

        if (control & 1) == 0:
            output.append(data)
            continue

        length = None
        if (data & 0x80) == 0:
            distance = ((data & 0x03) << 8) | input_data[idx]
            length = (data >> 2) + 2
            idx += 1

        elif (data & 0x40) == 0:
            distance = (data & 0x0f) + 1
            length = (data >> 4) - 7

        if length is not None:
            start_offset = len(output)
            idx2 = 0

            while idx2 <= length:
                output.append(output[(start_offset - distance) + idx2])
                idx2 += 1

            continue

        if data == 0xff:
            break

        length = data - 0xb9
        while length >= 0:
            output.append(input_data[idx])
            idx += 1
            length -= 1

    return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Input file', required=True)
    parser.add_argument('-o', '--output', help='Output folder (optional)', default="output")

    args = parser.parse_args()

    base_filename = os.path.basename(args.input)

    filename_table = None
    if base_filename == "d_seq.dat":
        filename_table = [
            "seq013prac.dsq",
            "seq020lnkn.dsq",
            "seq020lnkx.dsq",
            "seq020norm.dsq",
            "seq020real.dsq",
            "seq021expr.dsq",
            "seq021lnkn.dsq",
            "seq021lnkx.dsq",
            "seq021norm.dsq",
            "seq021real.dsq",
            "seq022expr.dsq",
            "seq022lnkn.dsq",
            "seq022lnkx.dsq",
            "seq022real.dsq",
            "seq023expr.dsq",
            "seq023lnkn.dsq",
            "seq023lnkx.dsq",
            "seq023norm.dsq",
            "seq023real.dsq",
            "seq024expr.dsq",
            "seq024lnkn.dsq",
            "seq024lnkx.dsq",
            "seq024norm.dsq",
            "seq100expr.dsq",
            "seq100lnkn.dsq",
            "seq100lnkx.dsq",
            "seq100norm.dsq",
            "seq100real.dsq",
            "seq101expr.dsq",
            "seq101lnkn.dsq",
            "seq101lnkx.dsq",
            "seq101norm.dsq",
            "seq101real.dsq",
            "seq102expr.dsq",
            "seq102lnkn.dsq",
            "seq102lnkx.dsq",
            "seq102real.dsq",
            "seq103expr.dsq",
            "seq103lnkn.dsq",
            "seq103lnkx.dsq",
            "seq103norm.dsq",
            "seq103real.dsq",
            "seq104easy.dsq",
            "seq104expr.dsq",
            "seq104lnkn.dsq",
            "seq104lnkx.dsq",
            "seq104norm.dsq",
            "seq104prac.dsq",
            "seq104real.dsq",
            "seq105expr.dsq",
            "seq105lnkn.dsq",
            "seq105lnkx.dsq",
            "seq105real.dsq",
            "seq106expr.dsq",
            "seq106real.dsq",
            "seq107expr.dsq",
            "seq107real.dsq",
            "seq108expr.dsq",
            "seq109expr.dsq",
            "seq109norm.dsq",
            "seq109real.dsq",
            "seq110expr.dsq",
            "seq110lnkn.dsq",
            "seq110lnkx.dsq",
            "seq110norm.dsq",
            "seq110real.dsq",
            "seq111expr.dsq",
            "seq111lnkn.dsq",
            "seq111lnkx.dsq",
            "seq111norm.dsq",
            "seq111real.dsq",
            "seq112expr.dsq",
            "seq112lnkn.dsq",
            "seq112lnkx.dsq",
            "seq112real.dsq",
            "seq113expr.dsq",
            "seq113lnkn.dsq",
            "seq113lnkx.dsq",
            "seq113real.dsq",
            "seq114expr.dsq",
            "seq114lnkn.dsq",
            "seq114lnkx.dsq",
            "seq114real.dsq",
            "seq115expr.dsq",
            "seq115lnkn.dsq",
            "seq115lnkx.dsq",
            "seq115norm.dsq",
            "seq115real.dsq",
            "seq117easy.dsq",
            "seq117expr.dsq",
            "seq117norm.dsq",
            "seq117prac.dsq",
            "seq117real.dsq",
            "seq118expr.dsq",
            "seq118norm.dsq",
            "seq118real.dsq",
            "seq119easy.dsq",
            "seq119norm.dsq",
            "seq119prac.dsq",
            "seq119real.dsq",
            "seq121expr.dsq",
            "seq121norm.dsq",
            "seq122easy.dsq",
            "seq122norm.dsq",
            "seq122real.dsq",
            "seq123easy.dsq",
            "seq123expr.dsq",
            "seq123norm.dsq",
            "seq123prac.dsq",
            "seq123real.dsq",
            "seq126lnkn.dsq",
            "seq126lnkx.dsq",
            "seq127expr.dsq",
            "seq127norm.dsq",
            "seq128norm.dsq",
            "seq128easy.dsq",
            "seq117lnkn.dsq",
            "seq117lnkx.dsq",
            "seq123lnkn.dsq",
            "seq123lnkx.dsq",
            "seq118lnkn.dsq",
            "seq118lnkx.dsq"
        ]

    elif base_filename == "g_seq.dat":
        filename_table = [] # TODO

    elif base_filename == "seqdata.dat":
        filename_lookup = {}

        for i in range(0, 1000):
            filename = "seq%03d" % (i)
            filename_lookup[get_filename_hash(filename)] = filename

            for p in ["", "prac", "easy", "norm", "real", "expr", "lnkn", "lnkx", "bnus"]:
                filename = "seq%03d%s" % (i, p)
                filename_lookup[get_filename_hash(filename)] = filename

            for p1 in ["", "1p", "2p", "1p1", "1p2", "2p1", "2p2", "bas"]:
                for p2 in ["", "bas", "pra", "nor", "exp", "ex1", "ex2", "ex3", "ex4"]:
                    filename = "seq%03d_%3s%3s" % (i, p1, p2)
                    filename_lookup[get_filename_hash(filename)] = filename

        filename_table = []
        with open("seqcode.dat", "rb") as infile:
            data = bytearray(infile.read())

            for i in range(0, len(data), 4):
                filename_hash = int.from_bytes(data[i:i+4], 'little')

                if filename_hash == 0xffffffff:
                    break

                filename_table.append(filename_lookup[filename_hash] + ".bin")

    output_path = args.output

    os.makedirs(output_path, exist_ok=True)

    with open(args.input, "rb") as infile:
        data = bytearray(infile.read())

        file_count = int.from_bytes(data[:4], 'little')
        cur_offset = 0x10

        for i in range(file_count):
            offset = int.from_bytes(data[cur_offset:cur_offset+4], 'little')
            cur_offset += 4

            chunk = data[offset & 0x7fffffff:]

            is_enc = (offset & 0x80000000) != 0

            output_filename = "%s" % (filename_table[i]) if filename_table else "output_%04d.bin" % i
            output_filename = os.path.join(output_path, output_filename)

            print("%08x: %s" % (offset & 0x7fffffff, output_filename))

            if is_enc:
                decoder = DecodeGfdm(chunk)
                chunk = decoder.decode()
                chunk = decode_lz(chunk)

            else:
                chunk = decode_lz(chunk)

            with open(output_filename, "wb") as outfile:
                outfile.write(chunk)
