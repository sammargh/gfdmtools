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

filename_hashes = []
with open("seqcode.dat", "rb") as infile:
    data = bytearray(infile.read())

    for i in range(0, len(data), 4):
        filename_hashes.append(int.from_bytes(data[i:i+4], 'little'))

        if filename_hashes[-1] in filename_lookup:
            print("%08x: %s" % (filename_hashes[-1], filename_lookup[filename_hashes[-1]]))
        else:
            print("%08x" % filename_hashes[-1])

output_path = "output"

os.makedirs(output_path, exist_ok=True)

with open("seqdata.dat", "rb") as infile:
    data = bytearray(infile.read())

    file_count = int.from_bytes(data[:4], 'little')
    cur_offset = 0x10

    for i in range(file_count):
        offset = int.from_bytes(data[cur_offset:cur_offset+4], 'little')
        cur_offset += 4

        chunk = data[offset & 0x7fffffff:]

        is_enc = (offset & 0x80000000) != 0

        output_filename = "%s.bin" % (filename_lookup[filename_hashes[i]]) if filename_hashes[i] in filename_lookup else "output_%04d.bin" % i
        output_filename = os.path.join(output_path, output_filename)
        # print("%08x: %s" % (offset, output_filename))

        if is_enc:
            decoder = DecodeGfdm(chunk)
            chunk = decoder.decode()
            chunk = decode_lz(chunk)

        else:
            chunk = decode_lz(chunk)

        with open(output_filename, "wb") as outfile:
            outfile.write(chunk)
