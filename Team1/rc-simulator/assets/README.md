# Car files

Rotor builds its car from a small set of files, loose next to `__init__.py`
or in the `CAR_DIR` subfolder (`assets/gravelbasher/` by default). Both are
searched; `CAR_FILES_LOOSE = True` tries the loose files first.

| File | Needed | Used for |
| --- | --- | --- |
| `parameters.txt` | Required | Names the model and texture files, places the wheels, and sets the handling. See [PARAMETERS.md](PARAMETERS.md). |
| Body model, e.g. `body.obj` | Required | The car body mesh (`MODEL 0` unless `BODY` says otherwise). |
| Wheel models, e.g. `wheelf.obj`, `wheelb.obj` | Recommended | Wheel meshes; each `WHEEL` picks one with `ModelNum`. Without them the car still drives, but no wheels are drawn. |
| Texture page, e.g. `car.bmp` | Recommended | Colours every face with the average texture colour under it. Uncompressed BMP, 8, 24 or 32-bit. Without it, faces use the model's vertex colours (often plain white). |
| Extra part, e.g. `foglights.obj` | Optional | A static part fixed to the body, set by `SPINNER`. |

## Model formats
Meshes are **Wavefront `.obj`** files, which open in Blender and any 3D
viewer.

For `.obj` files:
- Axes are Y up, -Z forward, the usual OBJ / Blender layout.
- A face with UVs on every corner is coloured from the texture page; one
  without UVs uses its vertex colours (`v x y z r g b`) or else the
  material's `Kd` colour from the `.mtl`.
- A material whose name contains `double` (e.g. `tex15_double`) is two-sided.
- Faces with more than four corners are split into triangles.

Model and texture names come from `parameters.txt`. Only the file name counts:
any folder in front of it (`cars/gravelbasher/body.obj`) is ignored, and letter
case doesn't matter.

## Gravel Basher
| File | Needed |
| --- | --- |
| `parameters.txt` | Required |
| `body.obj` | Required |
| `wheelf.obj` | Recommended (front wheels) |
| `wheelb.obj` | Recommended (rear wheels) |
| `car.bmp` | Recommended |
| `foglights.obj` | Optional |
| `car.mtl` | Optional (lets 3D apps show the texture; Rotor only reads its `Kd` colours) |

The first launch processes the car and caches the result in
`/state/rotor-<folder>.json`. It is rebuilt whenever one of these files
changes size.

These are third-party files, so they are git-ignored. Do not commit them.
