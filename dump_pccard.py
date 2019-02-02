import struct

files = []
with open("unk_data.DAT", "rb") as infile:
    while True:
        filename_hash, offset, filesize, flag = struct.unpack("<IIII", infile.read(0x10))

        if offset == 0xffffffff:
            break

        files.append({
            'filename_hash': filename_hash,
            'offset': offset,
            'filesize': filesize,
            'flag': flag
        })

with open("GAME.DAT", "rb") as infile:
    for idx, fileinfo in enumerate(files):
        output_filename = "output_%04d.bin" % idx

        print("Extracting", output_filename)

        with open(output_filename, "wb") as outfile:
            infile.seek(fileinfo['offset'])
            outfile.write(infile.read(fileinfo['filesize']))

