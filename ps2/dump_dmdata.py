import os

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

key = bytearray([ 0x97, 0x47, 0x56, 0x37, 0xE4, 0xAB, 0xE4, 0xAB, 0x60, 0x61, 0x75, 0x11, 0x26, 0x41, 0xBE, 0x81, 0x97, 0x97, 0x22, 0x39, 0xE4, 0x1B, 0x84, 0xA0, 0x60, 0x61, 0x75, 0x14, 0x26, 0x41, 0xBE, 0x8A, 0x97, 0x27, 0x99, 0x32, 0xE4, 0x8B, 0x10, 0xA4, 0x60, 0x92, 0x29, 0x14, 0x26, 0x08, 0x41, 0x8A ])

output_path = "DMDATA"

with open("DMDATA.PAK", "rb") as infile:
    data = bytearray(infile.read())
    file_count = int.from_bytes(data[:4], 'little')

    cur_offset = 0x10
    for i in range(file_count):
        for i in range(0x30):
            data[cur_offset+i] ^= key[i % len(key)]

        filename = data[cur_offset:cur_offset+0x20].decode('ascii').strip('\0')
        flag = data[cur_offset+0x2b]
        chunk_size = int.from_bytes(data[cur_offset+0x2c:cur_offset+0x30], 'little')
        cur_offset += 0x30

        print("%-32s: offset[%08x] size[%08x] flag[%d]" % (filename, cur_offset, chunk_size, flag))

        output_filename = os.path.join(output_path, filename)
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)

        with open(output_filename, "wb") as outfile:
            if flag == 1:
                # Konami standard lzss compression
                start_addr = int.from_bytes(data[cur_offset+0x10:cur_offset+0x14], 'little')
                chunk_size -= start_addr
                cur_offset += start_addr
                outfile.write(decode_lz(data[cur_offset:cur_offset+chunk_size]))

            else:
                # No compression
                outfile.write(data[cur_offset:cur_offset+chunk_size])

        cur_offset += chunk_size

        if cur_offset & 0x0f != 0:
            cur_offset = (cur_offset + 0x10) & ~0x0f

