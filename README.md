# GaussianSplat
Tools and stuff for gaussian splatting

## Blender Exporter for [Jawset Postshot](https://www.jawset.com/)

![export_tut_hi](https://github.com/user-attachments/assets/49846d21-c392-48b4-bec7-afbff2e6f81b)

This script facilitates the generation of Synthetic Gaussian splats by making a camera dome, exporting cameras positions and a sparse pointcloud.

### Workflow

- Install the blender plugin
- select the object you want to export, hit Export Scene Data
- drag and drop the whole folder created into postshot with these settings:
- disable start training
- set Model Profile to Splat ADC (works best with synthetic scenes)
- set Black Background to true
- Hit Start Training

### Limitations

- the Model in Blender needs to be one single Mesh Object


## [Substance 3D Viewer Converter](https://colab.research.google.com/drive/13y6C3kVZpaeUSXzXjRiY-rZTg39qS9uo?usp=sharing)

[Substance 3D Viewer (Beta)](https://helpx.adobe.com/de/substance-3d-viewer.html) from Adobe lets you create Gaussian Splats with a pretty good text-to-3D model. Adobe is working with Babylon and other actors to standardize and optimize the format and its rendering. Until then, this is a quick converter that allows you ti use the popular Supersplat Editor and other, and you can easily run it directly in [Google Colab](https://colab.research.google.com/drive/13y6C3kVZpaeUSXzXjRiY-rZTg39qS9uo?usp=sharing) to convert your files.

<img width="1633" alt="image" src="https://github.com/user-attachments/assets/f01c8cec-aceb-4971-88eb-be37bbc28317">

Subtance 3D Viewer does not let you officially export the files, but it tells you where it keeps the temp files. Just load this into the converter and voila.

![image](https://github.com/user-attachments/assets/129d9e5c-6d4c-4624-94bb-892cd893489a)
