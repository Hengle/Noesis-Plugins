# Noesis-Plugins

My plugins for [Noesis by Rich Whitehouse](http://richwhitehouse.com/index.php?content=inc_projects.php&showproject=91). 

If you find any issues with the plugins, feel free to contact me here or on Xentax or anywhere.

## Megaman X8 (PC) (fmt_mmx8_wsx.py & fmt_mmx8_wpg.py) ##
Opens textures and most models in the game (and animations too).

## Fatal Frame 4 (Wii) (fmt_fatalframe_rsl.py) ##
Textures and rigged models.
***Reqires lib_zq_nintendo_tex.py!***

Notes:

 * Some meshes have flipped normals on rare occasion.
 * Only diffuse textures are applied.
 * Animation support can probably be added if requested.

## Star Wars: The Force Unleashed (Wii) (fmt_swtfu_wii_tex.py) ##
Textures.
***Reqires lib_zq_nintendo_tex.py!***

## Planet 51 (Wii) (fmt_planet51_wii_s3t.py) ##
Textures.
***Reqires lib_zq_nintendo_tex.py!***

## Silent Hill: Shattered Memories (fmt_silenthill_wii_tx.py) ##
Textures.
***Reqires lib_zq_nintendo_tex.py!***

See [this topic](http://forum.xentax.com/viewtopic.php?f=18&t=15025).

## Fire Emblem (Wii) (fmt_fireemblem_gs.py & fmt_fireemblem_pak.py) ##
Extracts .pak files.
Opens .gs/.g files (mesh, uv, skeleton, weights, vertex colors). 

Notes:
 * Requires fmt_wii_tpl.py (and lib_zq_nintendo_tex.py) to load textures but can do without it. Only diffuse textures are applied but all textures are loaded.
 * Vertex colors are disabled by default. To enable them, change *vertex_colors = 0* to *vertex_colors = 1*. Likewise, you can disable texture loading by setting *textures* flag to 0.

## MT Framework Engine (3DS) (fmt_mtframework_3ds_tex.py) ##
Textures.

Uses etc1tool.exe by onepiecefreak3.

https://github.com/onepiecefreak3/etc1tool/releases

Put the executable into Noesis/Scenes folder.

## TPL format (fmt_wii_tpl.py) ##
Common Wii texture format.
***Reqires lib_zq_nintendo_tex.py!***

## Nintex lib (lib_zq_nintendo_tex.py) ##
Work-in-progress library for extracting textures used on Nintendo consoles.

Also can be used as Texture Finder, just add .nintex extension to the file you want to examine.
