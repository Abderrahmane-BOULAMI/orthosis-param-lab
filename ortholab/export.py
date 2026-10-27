"""Write an orthosis to STL / 3MF for printing and to .3dm so it opens in Rhino and Grasshopper."""
import json
from pathlib import Path

import rhino3dm


def to_3dm(mesh, path, measures=None, params=None, name="AFO"):
    """Rhino file with one named mesh on an 'Orthosis' layer; measurements and parameters stored as user text."""
    model = rhino3dm.File3dm()
    model.Settings.ModelUnitSystem = rhino3dm.UnitSystem.Millimeters
    layer = rhino3dm.Layer()
    layer.Name = "Orthosis"
    layer.Color = (46, 125, 150, 255)
    li = model.Layers.Add(layer)
    rm = rhino3dm.Mesh()
    for v in mesh.vertices:
        rm.Vertices.Add(float(v[0]), float(v[1]), float(v[2]))
    for f in mesh.faces:
        rm.Faces.AddFace(int(f[0]), int(f[1]), int(f[2]))
    rm.Normals.ComputeNormals()
    rm.Compact()
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
