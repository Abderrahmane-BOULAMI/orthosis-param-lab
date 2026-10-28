"""Write an orthosis to STL / 3MF for printing and to .3dm so it opens in Rhino and Grasshopper."""
import json
from pathlib import Path

import rhino3dm


def to_rhino_mesh(mesh, mesh_cls=None):
    """Copy a trimesh into a Rhino mesh. mesh_cls is Rhino.Geometry.Mesh inside Rhino, rhino3dm.Mesh outside."""
    rm = (mesh_cls or rhino3dm.Mesh)()
    for v in mesh.vertices:
        rm.Vertices.Add(float(v[0]), float(v[1]), float(v[2]))
    for f in mesh.faces:
        rm.Faces.AddFace(int(f[0]), int(f[1]), int(f[2]))
    rm.Normals.ComputeNormals()
    rm.Compact()
    return rm


def to_3dm(mesh, path, measures=None, params=None, name="AFO"):
    """Rhino file with one named mesh on an 'Orthosis' layer; measurements and parameters stored as user text."""
    model = rhino3dm.File3dm()
    model.Settings.ModelUnitSystem = rhino3dm.UnitSystem.Millimeters
    layer = rhino3dm.Layer()
    layer.Name = "Orthosis"
    layer.Color = (46, 125, 150, 255)
    li = model.Layers.Add(layer)
    rm = to_rhino_mesh(mesh)
    attr = rhino3dm.ObjectAttributes()
    attr.LayerIndex = li
    attr.Name = name
    for key, val in (measures or {}).items():
        attr.SetUserString(f"measure.{key}", str(val))
    for key, val in (params or {}).items():
        attr.SetUserString(f"param.{key}", str(val))
    model.Objects.AddMesh(rm, attr)
    model.Write(str(path), 8)
    return Path(path)


def read_3dm(path):
    model = rhino3dm.File3dm.Read(str(path))
    obj = model.Objects[0]
    geo = obj.Geometry
    keys = obj.Attributes.GetUserStrings()
    return {"vertices": len(geo.Vertices), "faces": geo.Faces.Count, "name": obj.Attributes.Name,
            "user_text": dict(keys)}


def export_all(mesh, folder, stem, measures=None, params=None):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    mesh.export(folder / f"{stem}.stl")
    mesh.export(folder / f"{stem}.3mf")
    to_3dm(mesh, folder / f"{stem}.3dm", measures, params, name=stem)
    clean = {k: v for k, v in (params or {}).items() if isinstance(v, (int, float, str))}
    (folder / f"{stem}.json").write_text(json.dumps({"measures": measures, "params": clean}, indent=2))
    return folder


def export_articulated(parts, folder, stem, measures=None):
    """One STL per part (print them separately), a 3MF and a .3dm of the assembly with one object/layer per part.

    Works for the two-part articulated AFO and for the segmented foot (hindfoot, midfoot, forefoot, toes).
    """
    import trimesh
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    meshes = {"calf_cuff": parts["upper"]}
    if "segments" in parts:
        meshes.update({f"foot_{k}": v for k, v in parts["segments"].items()})
        meshes["pins_preview"] = trimesh.util.concatenate([parts["pins"], parts["foot_pins"]])
    else:
        meshes["foot_section"] = parts["lower"]
        meshes["pins_preview"] = parts["pins"]
    for name, mesh in meshes.items():
        mesh.export(folder / f"{stem}_{name}.stl")
    scene = trimesh.Scene()
    for name, mesh in meshes.items():
        scene.add_geometry(mesh, node_name=name, geom_name=name)
    scene.export(folder / f"{stem}_assembly.3mf")
    model = rhino3dm.File3dm()
    model.Settings.ModelUnitSystem = rhino3dm.UnitSystem.Millimeters
    palette = {"calf_cuff": (51, 92, 158, 255), "pins_preview": (150, 150, 158, 255), "foot_section": (0, 144, 156, 255),
               "foot_hindfoot": (0, 144, 156, 255), "foot_midfoot": (227, 163, 59, 255),
               "foot_forefoot": (217, 100, 74, 255), "foot_toes": (126, 107, 181, 255)}
    for name, mesh in meshes.items():
        layer = rhino3dm.Layer()
        layer.Name = name
        layer.Color = palette.get(name, (128, 128, 128, 255))
        li = model.Layers.Add(layer)
        attr = rhino3dm.ObjectAttributes()
        attr.LayerIndex = li
        attr.Name = name
        for k, v in (measures or {}).items():
            attr.SetUserString(f"measure.{k}", str(v))
        model.Objects.AddMesh(to_rhino_mesh(mesh), attr)
    model.Write(str(folder / f"{stem}_assembly.3dm"), 8)
    j = parts["joint"]
    info = {"measures": measures, "ankle_axis_point_mm": [round(float(v), 2) for v in j.origin],
            "ankle_axis_direction": [1, 0, 0], "pin": "M5 screw and nyloc nut, one per side",
            "hinge_radius_mm": j.radius, "print_gap_mm": j.gap}
    if "foot_joints" in parts:
        info["foot_joints"] = [{"name": fj.name, "axis_point_mm": [round(float(v), 2) for v in fj.origin],
                                "axis_direction": [round(float(v), 4) for v in fj.axis],
                                "dorsiflexion_range_deg": fj.range_deg, "pin": "M3 screw and nyloc nut, one per side"}
                               for fj in parts["foot_joints"]]
    (folder / f"{stem}_assembly.json").write_text(json.dumps(info, indent=2))
    return folder
