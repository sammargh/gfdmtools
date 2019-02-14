import struct
import ctypes

def get_filename_hash(filename):
    t1 = 0x4c11db7
    v1 = 0

    for cidx, c in enumerate(filename):
        a1 = 0
        c = ord(c)

        for i in range(6):
            a0 = (v1 << 1) | ((c >> i) & 1)
            v1 = ((v1 >> 31) & t1) ^ a0
            v1 = ctypes.c_int(v1).value

    return abs(v1)

pccard_filenames = [
    "fpga_mp3.bin",
    "object_2d_data.bin",
    "arrangement_data.bin",
    "music_info.bin",
    "course_info.bin",
    "t_cb_tmd.bin",
    "v_cb_tmd.bin",
    "gsq_list.bin",
    "tex_group_gf_panel.fcn",
    "ascii_size8.bin",
    "ascii_size16.bin",
    "ascii_size24.bin",
    "rank_size20.bin",
    "tex_group_system.fcn",
    "tex_group_gf_system.fcn",
    "tex_group_gf_wait_server.fcn",
    "tex_group_gf_cg_check.fcn",
    "tex_group_gf_title.fcn",
    "tex_group_gf_game.fcn",
    "tex_group_gf_play_config.fcn",
    "tex_group_gf_frame_0.fcn",
    "tex_group_gf_sta_t_result.fcn",
    "tex_group_gf_title.fcn",
    "tex_group_internet.fcn",
    "tex_group_music_ranking.fcn",
    "tex_group_setting_unmatch.fcn",
    "tex_group_staff.fcn",
    "tex_group_wait_session.fcn",
    "tex_group_warning_logo.fcn",
]

hash_list = {}

for filename in pccard_filenames:
    hash_list[get_filename_hash(filename)] = filename

files = []
with open("PCCARD1.DAT", "rb") as infile:
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

    for idx, fileinfo in enumerate(files):
        output_filename = "output_%04d.bin" % idx

        if fileinfo['filename_hash'] in hash_list:
            output_filename = hash_list[fileinfo['filename_hash']]

        print("Extracting", output_filename)

        with open(output_filename, "wb") as outfile:
            infile.seek(fileinfo['offset'])
            outfile.write(infile.read(fileinfo['filesize']))



with open("GAME.DAT", "rb") as infile:
    infile.seek(0x24, 0)

    for _ in range(2):
        infile.seek(0x1c, 1)
        exe_size = struct.unpack("<I", infile.read(4))[0]
        infile.seek(exe_size + 0x800 - 0x1c, 1)

        print("%08x" % infile.tell())

        if (infile.tell() % 0x60000) != 0:
            infile.seek(0x60000 - (infile.tell() % 0x60000), 1)


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

    for idx, fileinfo in enumerate(files):
        output_filename = "output_%04d.bin" % idx

        if fileinfo['filename_hash'] in hash_list:
            output_filename = hash_list[fileinfo['filename_hash']]

        print("Extracting", output_filename)

        with open(output_filename, "wb") as outfile:
            infile.seek(fileinfo['offset'])
            outfile.write(infile.read(fileinfo['filesize']))

