import io
import struct
import sys
import os

CONVERT_TIM = True

basepath = os.path.splitext(sys.argv[1])[0]

if not os.path.exists(basepath):
    os.makedirs(basepath)

with open(sys.argv[1], "rb") as infile:
    filesize, unk1, filetable_size, unk2 = struct.unpack("<IIII", infile.read(16))

    is_new_format = False
    if filesize & 0x08000000 != 0:
        is_new_format = True

    if is_new_format:
        file_count = filesize & 0xffff

    else:
        file_count = filetable_size // 0x28

    for i in range(file_count):
        infile.seek(0x10 + (i * 0x28))

        filename = infile.read(0x20).decode('shift-jis').strip()
        filename = os.path.join(basepath, filename)
        offset, datalen = struct.unpack("<II", infile.read(8))

        if is_new_format:
            infile.seek(0x10 + (file_count * 0x28) + offset)

        else:
            infile.seek(0x10 + filetable_size + offset)

        data = infile.read(datalen)

        with open(filename, "wb") as outfile:
            outfile.write(data)

        if CONVERT_TIM and filename.lower().endswith(".tim"):
            from tim2png import readTimImage

            filename = filename[:-3] + "png"

            print("Extracting", filename)

            image, _ = readTimImage(io.BytesIO(data))
            image.save(filename)