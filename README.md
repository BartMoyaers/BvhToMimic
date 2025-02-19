# BvhToMimic [WIP]

## Goal

The [DeepMimic project](https://github.com/xbpeng/DeepMimic) currently offers no way to import custom reference motions. This is shown in [DeepMimic issue #23](https://github.com/xbpeng/DeepMimic/issues/23). This project aims to transfer animation data from .BVH files into DeepMimic Motion files. Motion files can then be used to Train DeepMimic skills.

## Related Projects

[List of related projects](https://github.com/SleepingFox88/DeepMimic-Animation-Conversion)

## Progress so far

![walkTest1](./Assets/walkTest1.gif)

### [experimental] manual offset test:

[link to branch](https://github.com/SleepingFox88/BvhToMimic/tree/manual-offset-experimentation)

![manualOffsetTest](./Assets/manualOffsetTest.gif)

## Dependencies

Python `sudo apt install python`

numpy `pip install numpy`

bvh `pip install bvh`

tqdm `pip install tqdm`

## Creating a humanoid rig

Currently joints in .bvh files have to be manually assigned by name to the corresponding joints in the Mimic Motion humanoid rig. This is done by assigning .bvh model's bone names to the corresponding joint properties in [./Rigs/humanoidRig.json](./Rigs/humanoidRig.json)

I am currently unaware of how to create or use any algorithms that know how to automatically generate a humanoid rig (similar to how unity can), but am open to using them upon finding one.

## Running the project

```Bash
python BvhToMimic.py
```

Will convert all .bvh files located in /InputBvh/ into Mimic Motion files, located in /OutputMimic/
