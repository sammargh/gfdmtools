import ctypes
import hexdump
import struct
import sys
import os

from PIL import Image
import tim2png

def parse_obj(filename):
    found_ids = []
    filenames = []

    with open(filename, "rb") as infile:
        infile.seek(0, 2)
        filesize = infile.tell()
        infile.seek(0)

        entry_count = filesize // 0x30

        for i in range(entry_count):
            filename = infile.read(0x1c).decode('shift-jis').strip().strip('\0')
            unk1, unk2, arr_unk1, arr_unk2, arr_unk3, arr_unk4, w, h, arr_unk5, anim_group_id = struct.unpack("<HHHHHHHHHH", infile.read(0x14))

            print("%04d: %s %d %d %d %d %d %d (%d, %d) %d anim_group_id[%d]" % (i, filename, unk1, unk2, arr_unk1, arr_unk2, arr_unk3, arr_unk4, w, h, arr_unk5, anim_group_id))

            filenames.append(filename)

    print(filenames)
    return filenames


def parse_dat(filename, animation_filenames=[], tim_folder=None):
    with open(filename, "rb") as infile:
        if infile.read(4) != b"AEBG":
            print("Not a AEBG animation file")
            exit(1)

        unk1, entry_count = struct.unpack("<II", infile.read(8))

        if entry_count == 0:
            if unk1 == 1:
                # Do something...
                pass

        # Skip over actual data so we can get to the file list
        for _ in range(0, entry_count):
            first_block = infile.read(0x40)

            frame_count = struct.unpack("<I", infile.read(4))[0]
            for i in range(frame_count):
                cur_block = infile.read(0x20)

        filename_count = struct.unpack("<I", infile.read(4))[0]

        filenames = []
        for _ in range(0, filename_count):
            filename = infile.read(0x20).decode('shift-jis').strip().strip('\0')
            filenames.append(filename)

        print(filenames)

        render_by_timestamp = {}
        renders = []
        frame_width = 0
        frame_height = 0
        total_start_frame = 0
        total_end_frame = 0

        infile.seek(0x0c)
        for _ in range(0, entry_count):
            cur_offset = infile.tell()

            first_block = infile.read(0x40)

            frame_start_timestamp, frame_end_timestamp, entry_id, entry_type, anim_id, initial_x, initial_y = struct.unpack("<IIHHHHH", first_block[:18])
            transparency = first_block[0x28] & 0x40

            print("[%08x] %d to %d: %08x %04x" % (cur_offset, frame_start_timestamp, frame_end_timestamp, entry_id, anim_id))
            hexdump.hexdump(first_block)
            print()

            if entry_type == 2:
                # Frame information
                frame_width, frame_height = struct.unpack("<HH", first_block[0x12:0x16])
                total_start_frame = frame_start_timestamp
                total_end_frame = frame_end_timestamp
                continue

            frame_count = struct.unpack("<I", infile.read(4))[0]
            frames = []

            for i in range(frame_count):
                cur_block = infile.read(0x20)
                frames.append(cur_block)

                hexdump.hexdump(cur_block)

                start_timestamp, end_timestamp, command, command_unk, entry_idx, subcommand = struct.unpack("<IIHHHH", cur_block[:16])

                if command in [0x1000]:
                    continue

                for idx in range(start_timestamp, end_timestamp):
                    if idx not in render_by_timestamp:
                        render_by_timestamp[idx] = {}

                    if entry_idx not in render_by_timestamp[idx]:
                        render_by_timestamp[idx][entry_idx] = {}

                if command == 0:
                    if subcommand == 0:
                        # Position command
                        start_x, end_x, start_y, end_y = struct.unpack("<HHHH", cur_block[16:24])
                        start_x = ctypes.c_short(start_x).value
                        end_x = ctypes.c_short(end_x).value
                        start_y = ctypes.c_short(start_y).value
                        end_y = ctypes.c_short(end_y).value

                        for idx in range(start_timestamp, end_timestamp if end_timestamp < frame_end_timestamp else frame_end_timestamp):
                            cur_x = start_x + (idx - start_timestamp) * ((end_x - start_x) / (end_timestamp - start_timestamp))
                            cur_y = start_y + (idx - start_timestamp) * ((end_y - start_y) / (end_timestamp - start_timestamp))

                            render_by_timestamp[idx][entry_idx]['x'] = cur_x
                            render_by_timestamp[idx][entry_idx]['y'] = cur_y

                            if 'filename' not in render_by_timestamp[idx][entry_idx]:
                                render_by_timestamp[idx][entry_idx]['filename'] = filenames[anim_id]

                            if 'clut' not in render_by_timestamp[idx][entry_idx]:
                                render_by_timestamp[idx][entry_idx]['clut'] = 0

                            if 'transparency' not in render_by_timestamp[idx][entry_idx]:
                                render_by_timestamp[idx][entry_idx]['transparency'] = transparency

                        print("Move: (%d,%d) -> (%d,%d)" % (start_x, start_y, end_x, end_y))

                    elif subcommand in [4, 7]:
                        pass

                    else:
                        print("Unknown subcommand", subcommand)
                        # exit(1)

                elif command == 1:
                    # Sprite command

                    if subcommand == 0:
                        # Image-based animation
                        anim_image_count, time_per_image, unk1 = struct.unpack("<HHI", cur_block[16:24])
                        print("Sprite: %d images, %d ms per frame" % (anim_image_count, time_per_image))

                        anim_idx = animation_filenames.index(filenames[anim_id])

                        for idx in range(anim_idx, anim_idx + anim_image_count):
                            print(animation_filenames[idx])

                        for idx in range(start_timestamp, end_timestamp, time_per_image):
                            for j in range(0, time_per_image):
                                if idx + j >= end_timestamp:
                                    break

                                render_by_timestamp[idx + j][entry_idx]['filename'] = animation_filenames[anim_idx + ((idx - start_timestamp) % anim_image_count)]
                                render_by_timestamp[idx + j][entry_idx]['clut'] = 0
                                render_by_timestamp[idx + j][entry_idx]['transparency'] = transparency

                                if 'x' not in render_by_timestamp[idx + j][entry_idx]:
                                    render_by_timestamp[idx + j][entry_idx]['x'] = initial_x

                                if 'y' not in render_by_timestamp[idx + j][entry_idx]:
                                    render_by_timestamp[idx + j][entry_idx]['y'] = initial_y

                    elif subcommand == 1:
                        # Clut-based animation
                        anim_image_count, time_per_image, unk1 = struct.unpack("<HHI", cur_block[16:24])
                        print("Sprite: %d images, %d ms per frame" % (anim_image_count, time_per_image))

                        anim_idx = animation_filenames.index(filenames[anim_id])

                        print(animation_filenames[anim_idx])

                        for idx in range(start_timestamp, end_timestamp, time_per_image):
                            for j in range(0, time_per_image):
                                if idx + j >= end_timestamp:
                                    break

                                render_by_timestamp[idx + j][entry_idx]['filename'] = animation_filenames[anim_idx]
                                render_by_timestamp[idx + j][entry_idx]['clut'] = (idx - start_timestamp) % anim_image_count
                                render_by_timestamp[idx + j][entry_idx]['transparency'] = transparency

                                if 'x' not in render_by_timestamp[idx + j][entry_idx]:
                                    render_by_timestamp[idx + j][entry_idx]['x'] = initial_x

                                if 'y' not in render_by_timestamp[idx + j][entry_idx]:
                                    render_by_timestamp[idx + j][entry_idx]['y'] = initial_y

                    else:
                        print("Unknown subcommand", subcommand)
                        # exit(1)

                else:
                    print("Unknown command block %04x" % command)
                    # exit(1)


                print()

            print()

        if tim_folder:
            frames = []
            durations = []

            print(frame_width, frame_height, total_start_frame, total_end_frame)
            for k in sorted(render_by_timestamp.keys()):
                # if k <= 1100 or k >= 1600:
                #     continue

                if k >= 200:
                    continue

                render_frame = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
                for k2 in sorted(render_by_timestamp[k].keys())[::-1]:
                    if not render_by_timestamp[k][k2] or 'filename' not in render_by_timestamp[k][k2]:
                        continue

                    print(k, k2, render_by_timestamp[k][k2])

                    tim_filename = os.path.join(tim_folder, render_by_timestamp[k][k2]['filename'] + ".tim")

                    with open(tim_filename, "rb") as f:
                        image = tim2png.readTimImage(f, render_by_timestamp[k][k2]['clut'], render_by_timestamp[k][k2]['transparency'])

                    render_frame.paste(image, (int(render_by_timestamp[k][k2]['x'] - frame_width // 2 + (frame_width - image.width) // 2), int(render_by_timestamp[k][k2]['y'] - frame_height // 2 + (frame_height - image.height) // 2)), image)
                    frames.append(render_frame)

            frames[0].save("output.webp", format="webp", save_all=True, append_images=frames[1:], loop=0, lossless=True, quality=0, duration=round((1/60)*1000))
            frames[0].save("output.gif", format="gif", save_all=True, append_images=frames[1:], loop=0, lossless=True, quality=0, duration=round((1/60)*1000))

            for x in frames:
                x.close()
                del x

filenames = parse_obj(sys.argv[2])
parse_dat(sys.argv[1], filenames, sys.argv[3])