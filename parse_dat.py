import ctypes
import hexdump
import struct
import sys
import os

from PIL import Image, ImageChops
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
            initial_clut = struct.unpack("<H", first_block[0x28:0x2a])[0]

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

            if anim_id > len(filenames):
                infile.seek(frame_count * 0x20)
                continue

            if entry_type == 0:
                if anim_id < len(filenames):
                    print(filenames[anim_id])

                base_images.append(filenames[anim_id])

            elif entry_type == 1:
                w, h, a, r, g, b = struct.unpack("<HHBBBB", first_block[0x12:0x1a])
                base_images.append(Image.new("RGBA", (w, h), (r, g, b, 255)))

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

                        for idx in range(start_timestamp, end_timestamp):
                            cur_x = start_x + (idx - start_timestamp) * ((end_x - start_x) / ((end_timestamp - 1) - start_timestamp))
                            cur_y = start_y + (idx - start_timestamp) * ((end_y - start_y) / ((end_timestamp - 1) - start_timestamp))

                            render_by_timestamp[idx][entry_idx]['x'] = cur_x
                            render_by_timestamp[idx][entry_idx]['y'] = cur_y

                        print("Move: (%d,%d) -> (%d,%d)" % (start_x, start_y, end_x, end_y))

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

                        for idx in range(start_timestamp, end_timestamp):
                            cur_x_zoom = start_x_zoom + (idx - start_timestamp) * ((end_x_zoom - start_x_zoom) / ((end_timestamp - 1) - start_timestamp))
                            cur_y_zoom = start_y_zoom + (idx - start_timestamp) * ((end_y_zoom - start_y_zoom) / ((end_timestamp - 1) - start_timestamp))

                            render_by_timestamp[idx][entry_idx]['x_zoom'] = cur_x_zoom
                            render_by_timestamp[idx][entry_idx]['y_zoom'] = cur_y_zoom

                        print("Zoom: (%f,%f) -> (%f,%f)" % (start_x_zoom, start_y_zoom, end_x_zoom, end_y_zoom))

                    elif subcommand == 2:
                        # Scrolling sprite - handled separately
                        pass

                    elif subcommand == 3:
                        # Rotation command
                        start_rotate, end_rotate = struct.unpack("<HH", cur_block[16:20])
                        start_rotate = ctypes.c_short(start_rotate).value
                        end_rotate = ctypes.c_short(end_rotate).value

                        end_rotate /= 12

                        for idx in range(start_timestamp, end_timestamp):
                            cur_rotate = start_rotate + (idx - start_timestamp) * ((end_rotate - start_rotate) / ((end_timestamp - 1) - start_timestamp))
                            render_by_timestamp[idx][entry_idx]['rotate'] = cur_rotate

                        print("Rotation: %d -> %d" % (start_rotate, end_rotate))

                    elif subcommand == 4:
                        # Transparency command
                        start_transparency, end_transparency = struct.unpack("<HH", cur_block[16:20])

                        for idx in range(start_timestamp, end_timestamp):
                            cur_transparency = start_transparency + (idx - start_timestamp) * ((end_transparency - start_transparency) / ((end_timestamp - 1) - start_timestamp))
                            render_by_timestamp[idx][entry_idx]['opacity'] = cur_transparency / 128

                        print("Transparency: %d -> %d" % (start_transparency, end_transparency))

                    elif subcommand == 7:
                        # Set palette index
                        palette_idx = struct.unpack("<H", cur_block[16:18])[0]

                        for idx in range(start_timestamp, end_timestamp):
                            render_by_timestamp[idx][entry_idx]['clut'] = palette_idx

                        print("Clut: %d" % (palette_idx))

                    elif subcommand in [6, 8]:
                        # Animate image transitions
                        start_image_idx, end_image_idx = struct.unpack("<HH", cur_block[16:20])

                        anim_idx = animation_filenames.index(filenames[anim_id])
                        for idx in range(start_timestamp, end_timestamp):
                            cur_anim_idx = round(start_image_idx + (idx - start_timestamp) * ((end_image_idx - start_image_idx) / ((end_timestamp - 1) - start_timestamp)))
                            render_by_timestamp[idx][entry_idx]['filename'] = animation_filenames[anim_idx + cur_anim_idx]

                        print("Image transition: %d -> %d" % (start_image_idx, end_image_idx))

                    elif subcommand == 9:
                        # Palette transition??
                        start_palette, end_palette = struct.unpack("<HH", cur_block[16:20])

                        # for idx in range(start_timestamp, end_timestamp):
                        #     cur_palette = int(start_palette + (idx - start_timestamp) * ((end_palette - start_palette) / ((end_timestamp - 1) - start_timestamp)))
                        #     render_by_timestamp[idx][entry_idx]['clut'] = cur_palette

                        for idx in range(start_timestamp, end_timestamp):
                            render_by_timestamp[idx][entry_idx]['clut'] = start_palette

                        render_by_timestamp[idx][entry_idx]['clut'] = end_palette

                        print("Clut 2: %d -> %d" % (start_palette, end_palette))

                    else:
                        print("Unknown effect subcommand", subcommand)
                        # exit(1)

                elif command == 1 and subcommand != 2:
                    # Sprite command
                    anim_image_count, time_per_image, flip_mode = struct.unpack("<HHI", cur_block[16:24])
                    anim_idx = animation_filenames.index(filenames[anim_id])

                    if subcommand in [0, 4]:
                        # Image-based animation
                        print("Sprite (image): %d images, %d ms per frame, flip mode %d" % (anim_image_count, time_per_image, flip_mode))

                        for idx in range(anim_idx, anim_idx + anim_image_count):
                            print(animation_filenames[idx])

                    elif subcommand in [1, 5]:
                        # Clut-based animation
                        print("Sprite (clut): %d images, %d ms per frame, flip mode %d" % (anim_image_count, time_per_image, flip_mode))
                        print(animation_filenames[anim_idx])

                    else:
                        print("Unknown subcommand image type", subcommand)
                        exit(1)

                    # time_per_image = round(time_per_image / anim_image_count)
                    # if subcommand in [4, 5]:
                    #     time_per_image *= 4

                    # time_per_image = int((end_timestamp - start_timestamp) / time_per_image / anim_image_count)

                    # How does the time per frame work?

                    if subcommand == 4:
                        time_per_image = round(60 / time_per_image)
                        flip_mode -= 1

                    anim_frame_idx = 0
                    flip_val = 0
                    for idx in range(start_timestamp, end_timestamp, time_per_image):
                        for j in range(0, time_per_image):
                            if idx + j >= end_timestamp:
                                break

                            if subcommand in [0, 4]:
                                render_by_timestamp[idx + j][entry_idx]['filename'] = animation_filenames[anim_idx + anim_frame_idx]
                                render_by_timestamp[idx + j][entry_idx]['clut'] = 0

                            elif subcommand in [1, 5]:
                                render_by_timestamp[idx + j][entry_idx]['filename'] = animation_filenames[anim_idx]
                                render_by_timestamp[idx + j][entry_idx]['clut'] = anim_frame_idx

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

                            # print(anim_id, anim_image_count, flip_val, anim_frame_idx)
                            anim_frame_idx += flip_val

                        else:
                            print("Unknown flip mode", flip_mode)
                            exit(1)

                elif command == 1 and subcommand == 2:
                    # Scroll sprite command
                    anim_idx = animation_filenames.index(filenames[anim_id])

                    time_per_image, offset_x, offset_y = struct.unpack("<HHH", cur_block[16:22])
                    offset_x = ctypes.c_short(offset_x).value // 16
                    offset_y = ctypes.c_short(offset_y).value // 16

                    anim_frame_idx = 0
                    cur_offset_x = 0
                    cur_offset_y = 0

                    for idx in range(start_timestamp, end_timestamp, time_per_image):
                        for j in range(0, time_per_image):
                            if idx + j >= end_timestamp:
                                break

                            render_by_timestamp[idx + j][entry_idx]['filename'] = animation_filenames[anim_idx + anim_frame_idx]
                            render_by_timestamp[idx + j][entry_idx]['offset_x'] = cur_offset_x
                            render_by_timestamp[idx + j][entry_idx]['offset_y'] = cur_offset_y
                            render_by_timestamp[idx + j][entry_idx]['tile'] = True

                            cur_offset_x += offset_x
                            cur_offset_y += offset_y

                else:
                    print("Unknown command block %04x" % command)
                    exit(1)


                print()

            print()


            flip_val = 0
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
                    render_by_timestamp[idx][entry_idx]['filename'] = base_images[-1]

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

        if tim_folder:
            frames = []

            image_cache = {}

            print(frame_width, frame_height, total_start_frame, total_end_frame)
            for k in sorted(render_by_timestamp.keys()):
                # if k < 1700 or k > 2100:
                #     continue

                # if k < 3300 or k > 3500:
                #     continue

                # if k < 2274 or k > 2274:
                #     continue

                # if k < 6599 or k > 6650:
                #     continue

                print()
                print()

                render_frame = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 255))
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
                            tim_filename = os.path.join(tim_folder, render_by_timestamp[k][k2]['filename'] + ".tim")

                            with open(tim_filename, "rb") as f:
                                image = tim2png.readTimImage(f, render_by_timestamp[k][k2]['clut'])

                            image_cache[render_by_timestamp[k][k2]['filename'] + "_" + str(render_by_timestamp[k][k2]['clut'])] = image.copy()

                    if render_by_timestamp[k][k2].get('opacity', 1.0) != 1.0:
                        pixels = image.load()
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

                    if render_by_timestamp[k][k2].get('tile', False):
                        for i in range(0, image2.width, image.width):
                            for j in range(0, image2.height, image.height):
                                image2.paste(image, (i, j))

                    else:
                        image2.paste(image, (int(render_by_timestamp[k][k2]['x'] - frame_width // 2 + (frame_width - image.width) // 2), int(render_by_timestamp[k][k2]['y'] - frame_height // 2 + (frame_height - image.height) // 2)), image)

                    if 'blend_mode' in render_by_timestamp[k][k2]:
                        if render_by_timestamp[k][k2]['blend_mode'] == 1:
                            render_frame = ImageChops.add(render_frame, image2)

                        elif render_by_timestamp[k][k2]['blend_mode'] == 2:
                            render_frame = ImageChops.subtract(render_frame, image2)

                        else:
                            render_frame.paste(image2, (0, 0), image2)
                            # render_frame = Image.alpha_composite(render_frame, image2)

                    else:
                        render_frame.paste(image2, (0, 0), image2)

                    # image2.save("output_%d_%d.png" % (k2, k))

                frames.append(render_frame)

            import imageio
            import numpy
            with imageio.get_writer("output.mp4", mode='I', fps=60, quality=10, format='FFMPEG') as writer:
                for frame in frames:
                    writer.append_data(numpy.asarray(frame, dtype='uint8'))

            frames[0].save("output.webp", format="webp", save_all=True, append_images=frames[1:], loop=0, lossless=True, quality=0, duration=round((1/60)*1000))
            frames[0].save("output.gif", format="gif", save_all=True, append_images=frames[1:], loop=0, lossless=True, quality=0, duration=round((1/60)*1000))

            for x in frames:
                x.close()
                del x

filenames = parse_obj(sys.argv[2])
parse_dat(sys.argv[1], filenames, sys.argv[3])