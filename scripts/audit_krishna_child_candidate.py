"""Inspect real GLB facial deltas and animated bone channels before promotion."""

from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path

from krishna_core.avatar_asset_pipeline import ARKIT_52, OCULUS_15, AvatarAssetInspector
from krishna_core.avatar_production import AvatarProductionPipeline


def inspect(path: Path) -> dict:
    data = path.read_bytes()
    document = json.loads(data[20 : 20 + struct.unpack_from("<I", data, 12)[0]])
    bin_start = 28 + struct.unpack_from("<I", data, 12)[0]
    views = document["bufferViews"]
    accessors = document["accessors"]
    dtype = {5126: "f", 5123: "H", 5125: "I", 5121: "B"}
    components = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}

    def values(index: int):
        accessor = accessors[index]
        fmt = dtype[accessor["componentType"]]
        width = components[accessor["type"]]
        size = struct.calcsize("<" + fmt * width)
        result = [(0,) * width for _ in range(accessor["count"])]
        if "bufferView" in accessor:
            view = views[accessor["bufferView"]]
            start = bin_start + view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
            stride = view.get("byteStride", size)
            result = [struct.unpack_from("<" + fmt * width, data, start + i * stride)
                      for i in range(accessor["count"])]
        if sparse := accessor.get("sparse"):
            index_view = views[sparse["indices"]["bufferView"]]
            index_fmt = dtype[sparse["indices"]["componentType"]]
            index_start = bin_start + index_view.get("byteOffset", 0) + sparse["indices"].get("byteOffset", 0)
            value_view = views[sparse["values"]["bufferView"]]
            value_start = bin_start + value_view.get("byteOffset", 0) + sparse["values"].get("byteOffset", 0)
            for i in range(sparse["count"]):
                at = struct.unpack_from("<" + index_fmt, data, index_start + i * struct.calcsize(index_fmt))[0]
                result[at] = struct.unpack_from("<" + fmt * width, data, value_start + i * size)
        return result

    target_magnitude = {}
    for mesh in document["meshes"]:
        names = mesh.get("extras", {}).get("targetNames", [])
        for primitive in mesh.get("primitives", []):
            for name, target in zip(names, primitive.get("targets", [])):
                if "POSITION" not in target:
                    continue
                magnitude = max((max(map(abs, vertex)) for vertex in values(target["POSITION"])), default=0)
                target_magnitude[name] = max(target_magnitude.get(name, 0), magnitude)

    clips = {}
    for animation in document.get("animations", []):
        moving = 0
        for channel in animation.get("channels", []):
            path_name = channel["target"].get("path")
            if path_name not in ("rotation", "translation"):
                continue
            sampler = animation["samplers"][channel["sampler"]]
            output = values(sampler["output"])
            if len(output) > 1 and any(
                math.dist(output[0], later) > 1e-5 for later in output[1:]
            ):
                moving += 1
        clips[animation["name"]] = moving

    return {"bytes": len(data), "morph_targets": len(target_magnitude),
            "nonzero_arkit": sum(target_magnitude.get(n, 0) > 1e-6 for n in ARKIT_52),
            "nonzero_visemes": sum(target_magnitude.get(n, 0) > 1e-6 for n in OCULUS_15),
            "zero_targets": sorted(n for n, value in target_magnitude.items() if value <= 1e-6),
            "clip_moving_bone_channels": clips,
            "profile": document.get("asset", {}).get("extras", {}).get("krishnaRuntimeProfile")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("asset", type=Path)
    args = parser.parse_args()
    report = inspect(args.asset)
    report["production_validation"] = AvatarProductionPipeline(args.asset.resolve().parents[5]).validate_output(args.asset)
    print(json.dumps(report, indent=2))
    assert report["production_validation"]["ready"]
    assert report["nonzero_arkit"] >= 45
    assert report["nonzero_visemes"] >= 12
    assert all(count > 0 for count in report["clip_moving_bone_channels"].values())


if __name__ == "__main__":
    main()
