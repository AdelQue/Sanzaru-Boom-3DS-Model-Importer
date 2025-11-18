# Sanzaru/Sly Cooper Model Importer for Blender

A WIP Blender model importer for Sly Cooper: Thieves in Time(and Bentley's Hackpack), primarily for PS3. Right Now the importer only works for static meshes as PS3 skeletal meshes use an entirely different block that uses edge intrices rather than vertex intrices, so it may be a while(if ever) when it starts working. The Vita models(including skeletal as that doesn't sue edge intrices there) can work with the script if the script is modified for endianess, but I haven't fount a way to switch between them programmatically.


## Requirements:
[QuickBMS](https://aluigi.altervista.org/quickbms.htm) for sancooked archive unpacking and CTEX to GTF conversion

gtf2dds for converting GTF textures to DDS textures

## Installation:
- In Blender, go to Edit > Preferences... > Add-ons > Install... 
- Select sanzarumodelimportSly.py
- Ensure Import-Export: Sly Cooper/Sanzaru Model Importer is checked

## Instructions:
- Run QuickBMS with sancooked_named_files.bms, select your sancooked archive, extract it and ensure all extracted files remain in the same folder with each other at all times

### Model Import:
- In Blender, go to go to File > Import > Sly Cooper/Sanzaru Model
- Select a .geo model from an extracted sancooked archive

### Texture Extraction:
- Run QuickBMS with tex2gtf.bms, select all your .tex files, and extract the files to convert them to .gtf
- Drag all for .gtf files to gtf2dds to convert them to dds

### Planned features:
- PS3 Skeletal Meshes
- PS3/Vita switching
- Full level instancing


## Thanks:
- [@ik-01](https://github.com/ik-01) for game executible research and providing various format specs 

- [killercracker on vg-resource](https://www.vg-resource.com/thread-29953-post-624230.html#pid624230) for the original QuickBMS script

- [@sleepyzay](https://github.com/sleepyzay) for other QuickBMS script

- [@AleQue](https://github.com/AdelQue) for original Sonic importer
