# Sanzaru/Sonic Boom 3DS Model Importer for Blender

A model importer for Sanzaru format models, specifically for 3DS Sonic Boom games. Importer currently supports full mesh data (UVs, normals, vertex colors, vertex weights), skeleton data, object names, material names, and texture names. 


## Requirements:
[QuickBMS](https://aluigi.altervista.org/quickbms.htm) for sancooked archive unpacking and CTPK unpacking

[SwitchToolbox](https://github.com/KillzXGaming/Switch-Toolbox/releases) for extracting CTPK textures

## Installation:
- In Blender, go to Edit > Preferences... > Add-ons > Install... 
- Select sanzarumodelimport.py
- Ensure Import-Export: Sonic Boom/Sanzaru Model Importer is checked

## Instructions:
- Run QuickBMS with sancooked-sonic.bms, select your sancooked archive, extract it and ensure all extracted files remain in the same folder with each other at all times

### Model Import:
- In Blender, go to go to File > Import > Sonic Boom/Sanzaru Model
- Select a .geo model from an extracted sancooked archive

### Texture Extraction:
- Run QuickBMS with tex2ctpk.bms, select all your .tex files, and extract the files to convert them to .ctpk
- Open the .ctpk file with Siwtch Toolbox, navigate into the archive and select your texture
- Right click, export the texture to your desired file format

### Planned features:
- Texture parsing within Blender
- Proper GEOB filenames


## Thanks:
[@ik-01](https://github.com/ik-01) for game decompilation and providing various format specs 
