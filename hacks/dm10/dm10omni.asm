.psx
.open "d40jaa02/output/main.exe", 0x80010000 - 0x800

.org 0x8004f628
    j HookMusicListLoad
ReturnHookMusicListLoad:

.org 0x80017548
MusicOmniBin: .asciiz "music_omni.bin", 0

HookMusicListLoad:
    ; If dip switch 1 is flipped, load omnimix music_info.bin
    lb a0, 0x1f400004
    nop

    andi a0, a0, 0x01

    bne a0, zero, LoadMusicInfo
    nop

    la a1, MusicOmniBin


LoadMusicInfo:
    lui a0, 0
    jal 0x80042d98
    nop

    j ReturnHookMusicListLoad
    nop

.close
