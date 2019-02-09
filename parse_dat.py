import ctypes
import hexdump
import io
import struct
import sys
import os
import re

from PIL import Image, ImageChops
import tim2png

import imageops

def parse_obj(data):
    filenames = []

    filesize = len(data)
    entry_count = filesize // 0x30

    for i in range(entry_count):
        filename = data[i*0x30:i*0x30+0x1c].decode('shift-jis').strip().strip('\0')
        unk1, unk2, arr_unk1, arr_unk2, arr_unk3, arr_unk4, w, h, arr_unk5, anim_group_id = struct.unpack("<HHHHHHHHHH", data[i*0x30+0x1c:i*0x30+0x1c+0x14])

        output_filenames = []

        if '@' in filename:
            match = re.search(r'@(\d+)_(\d+)(?:\.(\d+))?$', filename)

            subimages = int(match.group(1))
            subimages2 = int(match.group(2))

            if subimages2 != 1:
                print("Found subimages2", subimages2)
                exit(1)

            subimages_base = 0
            if match.group(3):
                subimages_base = int(match.group(3))

            subimages_base *= subimages

            # Split image into x subimages
            for j in range(subimages):
                new_filename = filename.replace(match.group(0), "_%03d" % (j + subimages_base))
                output_filenames.append(new_filename)

        else:
            output_filenames.append(filename)

        for filename in output_filenames:
            print("%04d: %s %d %d %d %d %d %d (%d, %d) %d anim_group_id[%d]" % (i, filename, unk1, unk2, arr_unk1, arr_unk2, arr_unk3, arr_unk4, w, h, arr_unk5, anim_group_id))
            filenames.append(filename)

    return filenames




def get_images_from_fcn(filename):
    import sys
    print(filename, file=sys.stderr)

    output_files = {}

    with open(filename, "rb") as infile:
        filesize, unk1, filetable_size, unk2 = struct.unpack("<IIII", infile.read(16))

        is_new_format = False
        if filesize & 0x08000000 != 0:
            is_new_format = True

        if is_new_format:
            file_count = filesize & 0xffff

        else:
            file_count = filetable_size // 0x28

        sheet_images = {}
        for i in range(file_count):
            infile.seek(0x10 + (i * 0x28))

            filename = infile.read(0x20).decode('shift-jis').strip()

            offset, datalen = struct.unpack("<II", infile.read(8))

            if is_new_format:
                infile.seek(0x10 + (file_count * 0x28) + offset)

            else:
                infile.seek(0x10 + filetable_size + offset)

            data = infile.read(datalen)

            print("Extracting", filename)

            if filename.endswith('tim'):
                filename = filename[:-4]

                if '@' in filename:
                    match = re.search(r'(.*)@\d+_\d+(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?$', filename)

                    try:
                        subimages_base = int(match.group(2))
                    except:
                        subimages_base = 0

                    print(filename, subimages_base)

                    if match.group(1) not in sheet_images:
                        sheet_images[match.group(1)] = {}

                    if subimages_base not in sheet_images[match.group(1)]:
                        sheet_images[match.group(1)][subimages_base] = []

                    sheet_images[match.group(1)][subimages_base].append((filename, data))

                else:
                    output_files[filename] = data

            else:
                output_files[filename] = data

        for k in sheet_images:
            for sheet_idx in sheet_images[k]:
                for sheet in sheet_images[k][sheet_idx]:
                    filename, data = sheet
                    match = re.search(r'@(\d+)_(\d+)(?:\.(\d+))?(?:\.(\d+))?$', filename)

                    sub_images_x = int(match.group(1))
                    sub_images_y = int(match.group(2)) // len(sheet_images[k][sheet_idx])

                    try:
                        subimages_base = int(match.group(3))

                        try:
                            subimages_base2 = int(match.group(4))
                        except:
                            subimages_base2 = None
                    except:
                        subimages_base = 0
                        subimages_base2 = None

                    j = 0
                    for x in range(sub_images_x):
                        for y in range(sub_images_y):
                            new_filename = filename.replace(match.group(0), "_%03d" % (j + (sub_images_x * sub_images_y * subimages_base)))
                            print(new_filename)

                            if new_filename not in output_files or not isinstance(output_files[new_filename], list):
                                output_files[new_filename] = []

                            output_files[new_filename].append({
                                'data': data,
                                'region': (x, y),
                                'division': (sub_images_x, sub_images_y)
                            })
                            j += 1

    # exit(1)

    return output_files


def parse_dat(filename, output_filename="output", animation_filenames=[], sprite_images={}):
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
        print(animation_filenames)

        base_images = []

        render_by_timestamp = {}
        frame_width = 0
        frame_height = 0
        total_start_frame = 0
        total_end_frame = 0

        infile.seek(0x0c)
        for _ in range(0, entry_count):
            cur_offset = infile.tell()

            first_block = infile.read(0x40)

            frame_start_timestamp, frame_end_timestamp, entry_id, entry_type, anim_id, initial_x, initial_y = struct.unpack("<IIHHHHH", first_block[:0x12])

            blend_mode = struct.unpack("<H", first_block[0x1a:0x1c])[0]
            initial_rotate = struct.unpack("<H", first_block[0x1c:0x1e])[0]
            initial_x_zoom, initial_y_zoom = struct.unpack("<HH", first_block[0x1e:0x22])
            anim_in_time, anim_out_time  = struct.unpack("<HH", first_block[0x22:0x26])
            initial_animation_idx, initial_clut = struct.unpack("<BB", first_block[0x28:0x2a])
            sprite_x, sprite_y = struct.unpack("<HH", first_block[0x22:0x26])

            sprite_x *= 2
            sprite_y *= 2

            blend_mode = ctypes.c_short(blend_mode).value

            initial_x = ctypes.c_short(initial_x).value
            initial_y = ctypes.c_short(initial_y).value

            initial_x_zoom = ctypes.c_short(initial_x_zoom).value
            initial_y_zoom = ctypes.c_short(initial_y_zoom).value
            initial_x_zoom /= 4096
            initial_y_zoom /= 4096

            initial_rotate = ctypes.c_short(initial_rotate).value
            initial_rotate /= 1024
            initial_rotate *= 90

            print("[%08x] %d to %d: %08x %04x" % (cur_offset, frame_start_timestamp, frame_end_timestamp, entry_id, anim_id))

            hexdump.hexdump(first_block)
            print()

            frame_count = struct.unpack("<I", infile.read(4))[0]
            frames = []

            initial_alpha = struct.unpack("<B", first_block[0x16:0x17])[0]

            w, h, blend_a, blend_r, blend_g, blend_b = struct.unpack("<HHBBBB", first_block[0x12:0x1a])

            if anim_id > len(filenames):
                infile.seek(frame_count * 0x20)
                continue

            if entry_type == 0:
                if anim_id < len(filenames):
                    print(filenames[anim_id])

                base_images.append(filenames[anim_id])

            elif entry_type == 1:
                base_images.append(Image.new("RGBA", (w, h), (blend_r, blend_g, blend_b, 255)))

            elif entry_type == 2:
                # Frame information
                frame_width, frame_height = struct.unpack("<HH", first_block[0x12:0x16])
                total_start_frame = frame_start_timestamp
                total_end_frame = frame_end_timestamp
                continue

            for i in range(frame_count):
                cur_block = infile.read(0x20)
                frames.append(cur_block)

                hexdump.hexdump(cur_block)

                start_timestamp, end_timestamp, command, command_unk, entry_idx, subcommand = struct.unpack("<IIHHHH", cur_block[:16])

                if command in [4096]:
                    continue

                for idx in range(start_timestamp, end_timestamp + 1):
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

                        for idx in range(start_timestamp, end_timestamp if end_timestamp <= frame_end_timestamp else frame_end_timestamp):
                            cur_x = start_x + (idx - start_timestamp) * ((end_x - start_x) / ((end_timestamp - 1) - start_timestamp))
                            cur_y = start_y + (idx - start_timestamp) * ((end_y - start_y) / ((end_timestamp - 1) - start_timestamp))

                            render_by_timestamp[idx][entry_idx]['x'] = cur_x + render_by_timestamp[idx][entry_idx].get('x', 0)
                            render_by_timestamp[idx][entry_idx]['y'] = cur_y + render_by_timestamp[idx][entry_idx].get('y', 0)

                        print("Move: (%d,%d) -> (%d,%d)" % (start_x, start_y, end_x, end_y))

                    elif subcommand == 1:
                        # Image center
                        start_x, end_x, start_y, end_y = struct.unpack("<HHHH", cur_block[16:24])
                        start_x = ctypes.c_short(start_x).value
                        end_x = ctypes.c_short(end_x).value
                        start_y = ctypes.c_short(start_y).value
                        end_y = ctypes.c_short(end_y).value

                        for idx in range(start_timestamp, end_timestamp if end_timestamp <= frame_end_timestamp else frame_end_timestamp):
                            cur_x = start_x + (idx - start_timestamp) * ((end_x - start_x) / ((end_timestamp - 1) - start_timestamp))
                            cur_y = start_y + (idx - start_timestamp) * ((end_y - start_y) / ((end_timestamp - 1) - start_timestamp))

                            render_by_timestamp[idx][entry_idx]['center_x'] = int(cur_x)
                            render_by_timestamp[idx][entry_idx]['center_y'] = int(cur_y)

                        print("Image center: (%d,%d) -> (%d,%d)" % (start_x, start_y, end_x, end_y))

                    elif subcommand == 2:
                        start_x_zoom, end_x_zoom, start_y_zoom, end_y_zoom = struct.unpack("<HHHH", cur_block[16:24])

                        start_x_zoom = ctypes.c_short(start_x_zoom).value
                        start_y_zoom = ctypes.c_short(start_y_zoom).value
                        end_x_zoom = ctypes.c_short(end_x_zoom).value
                        end_y_zoom = ctypes.c_short(end_y_zoom).value

                        start_x_zoom /= 4096
                        start_y_zoom /= 4096
                        end_x_zoom /= 4096
                        end_y_zoom /= 4096

                        for idx in range(start_timestamp, end_timestamp if end_timestamp <= frame_end_timestamp else frame_end_timestamp):
                            cur_x_zoom = start_x_zoom + (idx - start_timestamp) * ((end_x_zoom - start_x_zoom) / ((end_timestamp - 1) - start_timestamp))
                            cur_y_zoom = start_y_zoom + (idx - start_timestamp) * ((end_y_zoom - start_y_zoom) / ((end_timestamp - 1) - start_timestamp))

                            render_by_timestamp[idx][entry_idx]['x_zoom'] = cur_x_zoom
                            render_by_timestamp[idx][entry_idx]['y_zoom'] = cur_y_zoom

                        print("Zoom: (%f,%f) -> (%f,%f)" % (start_x_zoom, start_y_zoom, end_x_zoom, end_y_zoom))

                    elif subcommand == 3:
                        # Rotation command
                        start_rotate, end_rotate = struct.unpack("<HH", cur_block[16:20])
                        start_rotate = ctypes.c_short(start_rotate).value
                        end_rotate = ctypes.c_short(end_rotate).value

                        start_rotate /= 12
                        end_rotate /= 12

                        for idx in range(start_timestamp, end_timestamp if end_timestamp <= frame_end_timestamp else frame_end_timestamp):
                            cur_rotate = start_rotate + (idx - start_timestamp) * ((end_rotate - start_rotate) / ((end_timestamp - 1) - start_timestamp))
                            render_by_timestamp[idx][entry_idx]['rotate'] = cur_rotate

                        print("Rotation: %d -> %d" % (start_rotate, end_rotate))

                    elif subcommand == 4:
                        # Transparency command
                        start_transparency, end_transparency = struct.unpack("<HH", cur_block[16:20])

                        for idx in range(start_timestamp, end_timestamp if end_timestamp <= frame_end_timestamp else frame_end_timestamp):
                            cur_transparency = start_transparency + (idx - start_timestamp) * ((end_transparency - start_transparency) / ((end_timestamp - 1) - start_timestamp))
                            render_by_timestamp[idx][entry_idx]['opacity'] = cur_transparency / 128

                        print("Transparency: %d -> %d" % (start_transparency, end_transparency))

                    elif subcommand in [6, 8]:
                        # Animate image transitions
                        start_image_idx, end_image_idx = struct.unpack("<HH", cur_block[16:20])
                        anim_diff = abs(end_image_idx - start_image_idx)

                        if anim_diff == 0:
                            anim_diff = 1

                        step = -1 if start_image_idx > end_image_idx else 1
                        end_timestamp2 = end_timestamp if end_timestamp <= frame_end_timestamp else frame_end_timestamp
                        time_step = (end_timestamp2 - start_timestamp) / anim_diff
                        anim_idx = animation_filenames.index(filenames[anim_id])

                        cur_timestamp = start_timestamp
                        cur_anim_idx = start_image_idx
                        while cur_timestamp < end_timestamp:
                            for j in range(0, int(cur_timestamp + time_step) - int(cur_timestamp)):
                                if int(cur_timestamp) + j >= end_timestamp:
                                    break

                                render_by_timestamp[int(cur_timestamp) + j][entry_idx]['filename'] = animation_filenames[anim_idx + cur_anim_idx]
                                render_by_timestamp[int(cur_timestamp) + j][entry_idx]['anim_idx'] = cur_anim_idx

                            cur_timestamp += time_step
                            cur_anim_idx += step

                        # render_by_timestamp[end_timestamp2][entry_idx]['filename'] = animation_filenames[anim_idx + end_image_idx]
                        # render_by_timestamp[end_timestamp2][entry_idx]['anim_idx'] = end_image_idx

                        print("Image transition: %d -> %d" % (start_image_idx, end_image_idx))

                    elif subcommand in [7, 9]:
                        # Palette transition
                        start_palette, end_palette = struct.unpack("<HH", cur_block[16:20])
                        palette_diff = abs(end_palette - start_palette)

                        if palette_diff == 0:
                            palette_diff = 1

                        step = -1 if start_palette > end_palette else 1
                        end_timestamp2 = end_timestamp if end_timestamp <= frame_end_timestamp else frame_end_timestamp
                        time_step = (end_timestamp2 - start_timestamp) / palette_diff

                        cur_timestamp = start_timestamp
                        cur_palette = start_palette
                        while cur_timestamp < end_timestamp:
                            for j in range(0, int(cur_timestamp + time_step) - int(cur_timestamp)):
                                if int(cur_timestamp) + j >= end_timestamp:
                                    break

                                render_by_timestamp[int(cur_timestamp) + j][entry_idx]['clut'] = cur_palette

                            cur_timestamp += time_step
                            cur_palette += step

                        # render_by_timestamp[end_timestamp2][entry_idx]['clut'] = end_palette

                        print("Clut transition: %d -> %d" % (start_palette, end_palette))

                    else:
                        print("Unknown effect subcommand", subcommand)
                        exit(1)

                elif command == 1 and subcommand == 0:
                    # Sprite command, no frame speed calculation
                    anim_image_count, time_per_image, flip_mode = struct.unpack("<HHI", cur_block[16:24])
                    anim_idx = animation_filenames.index(filenames[anim_id])

                    # Image-based animation
                    print("Sprite (image type 0): %d images, %d frames per image, flip mode %d" % (anim_image_count, time_per_image, flip_mode))

                    for idx in range(anim_idx, anim_idx + anim_image_count):
                        print(animation_filenames[idx])

                    anim_frame_idx = initial_animation_idx

                    flip_val = 0
                    for idx in range(start_timestamp, end_timestamp, time_per_image):
                        for j in range(0, time_per_image):
                            if idx + j >= end_timestamp:
                                break

                            afi = anim_frame_idx + render_by_timestamp[idx + j][entry_idx].get('anim_idx', 0)

                            render_by_timestamp[idx + j][entry_idx]['filename'] = animation_filenames[anim_idx + afi]
                            render_by_timestamp[idx + j][entry_idx]['clut'] = initial_clut

                        if flip_mode == 0:
                            anim_frame_idx = (anim_frame_idx + 1)

                            if anim_frame_idx >= anim_image_count:
                                anim_frame_idx = anim_image_count - 1

                        elif flip_mode == 1:
                            anim_frame_idx = (anim_frame_idx + 1) % anim_image_count

                        elif flip_mode == 2:
                            if anim_frame_idx - 1 < 0:
                                if flip_val == 0:
                                    flip_val = 1
                                else:
                                    flip_val = 0

                            elif anim_frame_idx + 1 >= anim_image_count:
                                if flip_val == 0:
                                    flip_val = -1
                                else:
                                    flip_val = 0

                            anim_frame_idx += flip_val

                        else:
                            # anim_frame_idx = (anim_frame_idx + 1)

                            # if anim_frame_idx >= anim_image_count:
                            #     anim_frame_idx = anim_image_count - 1

                            print("Unknown flip mode", flip_mode)
                            # exit(1)

                elif command == 1 and subcommand == 1:
                    # Sprite command, palette flip, no frame speed calculation
                    palette_colors, time_per_image, flip_mode = struct.unpack("<HHI", cur_block[16:24])
                    anim_idx = animation_filenames.index(filenames[anim_id])

                    # Image-based animation
                    print("Sprite (palette type 1): %d frames per palette, %d palettes, flip mode %d" % (time_per_image, palette_colors, flip_mode))

                    print(animation_filenames[anim_idx])

                    anim_frame_idx = initial_animation_idx

                    flip_val = 0
                    cur_timestamp = start_timestamp
                    while cur_timestamp < end_timestamp:
                        for j in range(0, int(cur_timestamp + time_per_image) - int(cur_timestamp)):
                            if int(cur_timestamp) + j >= end_timestamp:
                                break

                            if 'filename' not in render_by_timestamp[int(cur_timestamp) + j][entry_idx]:
                                render_by_timestamp[int(cur_timestamp) + j][entry_idx]['filename'] = animation_filenames[anim_idx]

                            render_by_timestamp[int(cur_timestamp) + j][entry_idx]['clut'] = anim_frame_idx

                        cur_timestamp += time_per_image

                        if flip_mode == 1:
                            anim_frame_idx = (anim_frame_idx + 1) % palette_colors

                        else:
                            # print("Unknown flip mode", flip_mode)
                            # exit(1)
                            pass

                elif command == 1 and subcommand == 2:
                    # Scroll sprite command
                    anim_idx = animation_filenames.index(filenames[anim_id])

                    time_per_image, offset_x, offset_y = struct.unpack("<HHH", cur_block[0x10:0x16])
                    offset_x = ctypes.c_short(offset_x).value / 16
                    offset_y = ctypes.c_short(offset_y).value / 16

                    print("Sprite (tiled image type 2): %d frames per image, (%d, %d) offset" % (time_per_image, offset_x, offset_y))

                    anim_frame_idx = initial_animation_idx
                    cur_offset_x = 0
                    cur_offset_y = 0

                    for idx in range(start_timestamp, end_timestamp, 1):
                        for j in range(0, 1):
                            if idx + j >= end_timestamp:
                                break

                            if 'filename' not in render_by_timestamp[idx + j][entry_idx]:
                                render_by_timestamp[idx + j][entry_idx]['filename'] = animation_filenames[anim_idx + anim_frame_idx]

                            render_by_timestamp[idx + j][entry_idx]['offset_x'] = int(cur_offset_x) + render_by_timestamp[idx + j][entry_idx].get('offset_x', 0)
                            render_by_timestamp[idx + j][entry_idx]['offset_y'] = int(cur_offset_y) + render_by_timestamp[idx + j][entry_idx].get('offset_y', 0)
                            render_by_timestamp[idx + j][entry_idx]['tile'] = time_per_image

                            cur_offset_x += offset_x
                            cur_offset_y += offset_y

                elif command == 1 and subcommand == 4:
                    # Sprite command, image based, frame calculation
                    anim_image_count, time_per_image, flip_mode = struct.unpack("<HHI", cur_block[16:24])
                    anim_idx = animation_filenames.index(filenames[anim_id])

                    # Image-based animation
                    print("Sprite (image type %d): %d images, %d frames per image, flip mode %d" % (subcommand, anim_image_count, time_per_image, flip_mode))

                    for idx in range(anim_idx, anim_idx + anim_image_count):
                        print(animation_filenames[idx])

                    anim_frame_idx = initial_animation_idx

                    # TODO: Rewrite code to handle time divisions with fractions (3 + 2 frames instead of 2.5, for example)
                    if time_per_image == 1:
                        time_per_image = 45

                    else:
                        time_per_image = 60 / time_per_image

                    print(time_per_image)

                    flip_val = 0
                    cur_timestamp = start_timestamp
                    while cur_timestamp < end_timestamp:
                        for j in range(0, int(cur_timestamp + time_per_image) - int(cur_timestamp)):
                            if int(cur_timestamp) + j >= end_timestamp:
                                break

                            afi = anim_frame_idx + render_by_timestamp[int(cur_timestamp) + j][entry_idx].get('anim_idx', 0)

                            if flip_mode in [4, 5, 6]:
                                afi = anim_image_count - afi - 1

                            render_by_timestamp[int(cur_timestamp) + j][entry_idx]['filename'] = animation_filenames[anim_idx + afi]
                            render_by_timestamp[int(cur_timestamp) + j][entry_idx]['clut'] = initial_clut

                        cur_timestamp += time_per_image

                        if time_per_image == 0:
                            cur_timestamp += 1
                            continue

                        if flip_mode in [0, 1, 4]:
                            anim_frame_idx = (anim_frame_idx + 1)

                            if anim_frame_idx >= anim_image_count:
                                anim_frame_idx = anim_image_count - 1

                        elif flip_mode in [2, 5]:
                            anim_frame_idx = (anim_frame_idx + 1) % anim_image_count

                        elif flip_mode in [3, 6]:
                            if anim_frame_idx - 1 < 0:
                                flip_val = 1

                            elif anim_frame_idx + 1 >= anim_image_count:
                                flip_val = -1

                            anim_frame_idx += flip_val

                        else:
                            print("Unknown flip mode", flip_mode)
                            # exit(1)


                elif command == 1 and subcommand == 5:
                    # Sprite command, palette flip, frame speed calculation
                    palette_colors, time_per_image, flip_mode = struct.unpack("<HHI", cur_block[16:24])
                    anim_idx = animation_filenames.index(filenames[anim_id])

                    # Image-based animation
                    print("Sprite (palette type 5): %d frames per palette, %d palettes, flip mode %d" % (time_per_image, palette_colors, flip_mode))

                    print(animation_filenames[anim_idx])

                    anim_frame_idx = initial_animation_idx

                    if time_per_image == 1:
                        time_per_image = 45

                    else:
                        time_per_image = 60 / time_per_image

                    flip_val = 0
                    cur_timestamp = start_timestamp
                    while cur_timestamp < end_timestamp:
                        for j in range(0, int(cur_timestamp + time_per_image) - int(cur_timestamp)):
                            if int(cur_timestamp) + j >= end_timestamp:
                                break

                            afi = anim_frame_idx + render_by_timestamp[int(cur_timestamp) + j][entry_idx].get('clut', 0)

                            if flip_mode in [4, 5, 6]:
                                afi = palette_colors - afi - 1

                            render_by_timestamp[int(cur_timestamp) + j][entry_idx]['filename'] = animation_filenames[anim_idx]
                            render_by_timestamp[int(cur_timestamp) + j][entry_idx]['clut'] = afi

                        cur_timestamp += time_per_image

                        if time_per_image == 0:
                            cur_timestamp += 1
                            continue

                        if flip_mode in [0, 1, 4]:
                            anim_frame_idx = (anim_frame_idx + 1)

                            if anim_frame_idx >= palette_colors:
                                anim_frame_idx = palette_colors - 1

                        elif flip_mode in [2, 5]:
                            anim_frame_idx = (anim_frame_idx + 1) % palette_colors

                        elif flip_mode in [3, 6]:
                            if anim_frame_idx - 1 < 0:
                                flip_val = 1

                            elif anim_frame_idx + 1 >= palette_colors:
                                flip_val = -1

                            anim_frame_idx += flip_val

                        else:
                            print("Unknown flip mode", flip_mode)
                            # exit(1)

                else:
                    print("Unknown command block %04x" % command)
                    exit(1)


                print()

            print()


            flip_val = 0
            last_filename = base_images[-1]
            last_alpha = initial_alpha / 0x80
            last_x = initial_x
            last_y = initial_y
            last_clut = initial_clut
            last_zoom_x = initial_x_zoom
            last_zoom_y = initial_y_zoom
            last_rotate = initial_rotate
            cur_offset_x = 0
            cur_offset_y = 0

            for idx in range(0, frame_start_timestamp):
                if idx not in render_by_timestamp or entry_idx not in render_by_timestamp[idx]:
                    continue

                # Find last used values
                if 'filename' in render_by_timestamp[idx][entry_idx]:
                    last_filename = render_by_timestamp[idx][entry_idx]['filename']

                if 'opacity' in render_by_timestamp[idx][entry_idx]:
                    last_alpha = render_by_timestamp[idx][entry_idx]['opacity']

                if 'x' in render_by_timestamp[idx][entry_idx]:
                    last_x = render_by_timestamp[idx][entry_idx]['x']

                if 'y' in render_by_timestamp[idx][entry_idx]:
                    last_y = render_by_timestamp[idx][entry_idx]['y']

                if 'clut' in render_by_timestamp[idx][entry_idx]:
                    last_clut = render_by_timestamp[idx][entry_idx]['clut']

                if 'x_zoom' in render_by_timestamp[idx][entry_idx]:
                    last_zoom_x = render_by_timestamp[idx][entry_idx]['x_zoom']

                if 'y_zoom' in render_by_timestamp[idx][entry_idx]:
                    last_zoom_y = render_by_timestamp[idx][entry_idx]['y_zoom']

                if 'rotate' in render_by_timestamp[idx][entry_idx]:
                    last_rotate = render_by_timestamp[idx][entry_idx]['rotate']

            for idx in range(frame_start_timestamp, frame_end_timestamp):
                if idx not in render_by_timestamp:
                    render_by_timestamp[idx] = {}

                if entry_idx not in render_by_timestamp[idx]:
                    render_by_timestamp[idx][entry_idx] = {}

                if 'filename' not in render_by_timestamp[idx][entry_idx]:
                    render_by_timestamp[idx][entry_idx]['filename'] = last_filename
                else:
                    last_filename = render_by_timestamp[idx][entry_idx]['filename']

                if 'blend_mode' not in render_by_timestamp[idx][entry_idx]:
                    render_by_timestamp[idx][entry_idx]['blend_mode'] = blend_mode

                if 'opacity' not in render_by_timestamp[idx][entry_idx]:
                    render_by_timestamp[idx][entry_idx]['opacity'] = last_alpha
                else:
                    last_alpha = render_by_timestamp[idx][entry_idx]['opacity']

                if 'x' not in render_by_timestamp[idx][entry_idx]:
                    render_by_timestamp[idx][entry_idx]['x'] = last_x
                else:
                    last_x = render_by_timestamp[idx][entry_idx]['x']

                if 'y' not in render_by_timestamp[idx][entry_idx]:
                    render_by_timestamp[idx][entry_idx]['y'] = last_y
                else:
                    last_y = render_by_timestamp[idx][entry_idx]['y']

                if 'clut' not in render_by_timestamp[idx][entry_idx]:
                    render_by_timestamp[idx][entry_idx]['clut'] = last_clut
                else:
                    last_clut = render_by_timestamp[idx][entry_idx]['clut']

                if 'x_zoom' not in render_by_timestamp[idx][entry_idx]:
                    render_by_timestamp[idx][entry_idx]['x_zoom'] = last_zoom_x
                else:
                    last_zoom_x = render_by_timestamp[idx][entry_idx]['x_zoom']

                if 'y_zoom' not in render_by_timestamp[idx][entry_idx]:
                    render_by_timestamp[idx][entry_idx]['y_zoom'] = last_zoom_y
                else:
                    last_zoom_y = render_by_timestamp[idx][entry_idx]['y_zoom']

                if 'rotate' not in render_by_timestamp[idx][entry_idx]:
                    render_by_timestamp[idx][entry_idx]['rotate'] = last_rotate
                else:
                    last_rotate = render_by_timestamp[idx][entry_idx]['rotate']

        # exit(1)

        # return

        if sprite_images:
            frames = []

            image_cache = {}

            print(frame_width, frame_height, total_start_frame, total_end_frame)
            for k in sorted(render_by_timestamp.keys()):
                # if k < 528 or k > 948:
                #     continue

                # if k < 2766 or k > 2916:
                #     continue

                # if k < 1032 or k > 1380:
                #     continue

                # if k < 2670 or k > 3480:
                #     continue

                print()
                print()

                render_frame = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
                for k2 in sorted(render_by_timestamp[k].keys())[::-1]:
                    if not render_by_timestamp[k][k2] or 'filename' not in render_by_timestamp[k][k2]:
                        continue

                    print(k, k2, render_by_timestamp[k][k2])

                    if isinstance(render_by_timestamp[k][k2]['filename'], Image.Image):
                        image = render_by_timestamp[k][k2]['filename'].copy()

                    else:

                        if render_by_timestamp[k][k2]['filename'] + "_" + str(render_by_timestamp[k][k2]['clut']) in image_cache:
                            image = image_cache[render_by_timestamp[k][k2]['filename'] + "_" + str(render_by_timestamp[k][k2]['clut'])].copy()

                        else:
                            if render_by_timestamp[k][k2]['filename'] not in sprite_images:
                                continue

                            image = sprite_images[render_by_timestamp[k][k2]['filename']]

                            if isinstance(image, list):
                                subimages = []

                                for subimage_info in image:
                                    image = tim2png.readTimImage(io.BytesIO(subimage_info['data']), render_by_timestamp[k][k2]['clut'])
                                    x1 = (image.width / subimage_info['division'][0]) * subimage_info['region'][0]
                                    x2 = (image.width / subimage_info['division'][0]) * (subimage_info['region'][0] + 1)

                                    y1 = (image.height / subimage_info['division'][1]) * subimage_info['region'][1]
                                    y2 = (image.height / subimage_info['division'][1]) * (subimage_info['region'][1] + 1)

                                    subimages.append(image.crop((x1, y1, x2, y2)))

                                image = Image.new('RGBA', (subimages[0].width, subimages[0].height * len(subimages)), (0, 0, 0, 0))

                                for idx, subimage in enumerate(subimages):
                                    image.paste(subimage, (0, subimage.height * idx), subimage)

                            elif not isinstance(image, Image.Image):
                                image = tim2png.readTimImage(io.BytesIO(image), render_by_timestamp[k][k2]['clut'])

                            if render_by_timestamp[k][k2]['filename'] + "_" + str(render_by_timestamp[k][k2]['clut']) not in image_cache:
                                image_cache[render_by_timestamp[k][k2]['filename'] + "_" + str(render_by_timestamp[k][k2]['clut'])] = image.copy()

                    center_x = render_by_timestamp[k][k2].get('center_x', 0)
                    center_y = render_by_timestamp[k][k2].get('center_y', 0)

                    if center_x != 0 or center_y != 0:
                        image3 = Image.new(image.mode, (image.width + center_x, image.height + center_y), (0, 0, 0, 0))
                        image3.paste(image, (image3.width // 2 - center_x, image3.height // 2 - center_y), image)

                        image.close()
                        del image

                        image = image3

                    pixels = image.load()
                    # if render_by_timestamp[k][k2]['blend_mode'] == 2:
                    #     for y in range(image.height):
                    #         for x in range(image.width):
                    #             pixels[x, y] = (255 - pixels[x, y][0], 255 - pixels[x, y][1], 255 - pixels[x, y][2], pixels[x, y][3])

                    if render_by_timestamp[k][k2].get('opacity', 1.0) != 1.0:
                        for y in range(image.height):
                            for x in range(image.width):
                                pixels[x, y] = (pixels[x, y][0], pixels[x, y][1], pixels[x, y][2], int(pixels[x, y][3] * render_by_timestamp[k][k2].get('opacity', 1.0)))

                    new_w = image.width * render_by_timestamp[k][k2]['x_zoom']
                    new_h = image.height * render_by_timestamp[k][k2]['y_zoom']

                    if new_w < 0:
                        image = image.transpose(Image.FLIP_LEFT_RIGHT)
                        new_w = abs(new_w)

                    if new_h < 0:
                        image = image.transpose(Image.FLIP_TOP_BOTTOM)
                        new_h = abs(new_h)

                    new_w = round(new_w)
                    new_h = round(new_h)

                    if (new_w, new_h) != image.size:
                        if new_w <= 0 or new_h <= 0:
                            image = Image.new(image.mode, image.size, (0, 0, 0, 0))
                        else:
                            image = image.resize((new_w, new_h))

                    if 'offset_x' in render_by_timestamp[k][k2]:
                        image = ImageChops.offset(image, render_by_timestamp[k][k2]['offset_x'], 0)

                    if 'offset_y' in render_by_timestamp[k][k2]:
                        image = ImageChops.offset(image, 0, render_by_timestamp[k][k2]['offset_y'])

                    if 'rotate' in render_by_timestamp[k][k2]:
                        image = image.rotate(-render_by_timestamp[k][k2]['rotate'], expand=True)

                    image2 = Image.new(render_frame.mode, render_frame.size, (0, 0, 0, 0))

                    new_x = render_by_timestamp[k][k2]['x'] - (frame_width // 2)
                    new_x = int(new_x + ((frame_width - image.width) // 2))

                    new_y = render_by_timestamp[k][k2]['y'] - (frame_height // 2)
                    new_y = int(new_y + ((frame_height - image.height) // 2))

                    if render_by_timestamp[k][k2].get('tile', 0) == 1:
                        for i in range(0, image2.width, image.width):
                            for j in range(0, image2.height, image.height):
                                image2.paste(image, (i, j))

                    elif render_by_timestamp[k][k2].get('tile', 0) == 2:
                        for i in range(0, image2.width, image.width):
                            image2.paste(image, (i, new_y))

                    elif render_by_timestamp[k][k2].get('tile', 0) == 3:
                        for j in range(0, image2.height, image.height):
                            image2.paste(image, (new_x, j))

                    else:
                        image2.paste(image, (new_x, new_y), image)

                    if 'blend_mode' in render_by_timestamp[k][k2]:
                        if render_by_timestamp[k][k2]['blend_mode'] == 1:
                            render_frame = ImageChops.add(render_frame, image2)
                            # render_frame = imageops.image_blend_2(image2, render_frame, render_by_timestamp[k][k2].get('opacity', 1.0), 1.0)

                        elif render_by_timestamp[k][k2]['blend_mode'] == 2:
                            render_frame = ImageChops.subtract(render_frame, image2)
                            # render_frame = imageops.image_blend_2(image2, render_frame, render_by_timestamp[k][k2].get('opacity', 1.0), 1.0)
                            # render_frame.paste(image2, (0, 0), image2)

                        else:
                            render_frame.paste(image2, (0, 0), image2)
                            # render_frame = Image.alpha_composite(render_frame, image2)

                    else:
                        # render_frame.paste(image2, (0, 0), image2)
                        render_frame = Image.alpha_composite(render_frame, image2)

                    # image2.save("output_%d_%d.png" % (k2, k))

                frames.append(render_frame)

            import imageio
            import numpy
            with imageio.get_writer(output_filename + ".mp4", mode='I', fps=60, quality=10, format='FFMPEG') as writer:
                for frame in frames:
                    writer.append_data(numpy.asarray(frame, dtype='uint8'))

            # frames[0].save(output_filename + ".webp", format="webp", save_all=True, append_images=frames[1:], loop=0, lossless=True, quality=0, duration=round((1/60)*1000))
            # frames[0].save(output_filename + ".gif", format="gif", save_all=True, append_images=frames[1:], loop=0, lossless=True, quality=0, duration=round((1/60)*1000))

            for x in frames:
                x.close()
                del x

print("Converting", sys.argv[1])

fcn_files = get_images_from_fcn(sys.argv[2])
obj_filename = [x for x in fcn_files if x.endswith('.obj')][0]
filenames = parse_obj(fcn_files[obj_filename])

base_filename = os.path.splitext(os.path.basename(sys.argv[1]))[0]
parse_dat(sys.argv[1], base_filename, filenames, fcn_files)