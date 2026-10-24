# parameters.txt

`parameters.txt` tells Rotor which files make up a car, where its wheels go,
and how it handles.

## Format
- One setting per line: a key, then its values. Keys ignore letter case.
- Values are separated by spaces, tabs or commas. File names go in quotes.
- `;` starts a comment that runs to the end of the line.
- A section is `NAME {` on one line, its settings, then `}` on its own line.
- Wrapping the whole file in `{ ... }` is allowed but not needed.

Positions use the model's own units, with X to the right, Y down (negative is
up) and Z forward. This stays the same when the meshes are `.obj` files
(which are Y up, -Z forward): a wheel at the front of an OBJ model, at
Z = -36, still has `Offset1 ... 36` here. Rotor scales the car so the body is 0.45 m long, and sets
its lowest point on the ground.

## Files
| Key | Values | Meaning |
| --- | --- | --- |
| `MODEL` | slot, `"file"` | Assigns a model file to a numbered slot, e.g. `MODEL 0 "body.obj"`. Must be a Wavefront `.obj` file. Parts refer to slots by number. Required for the body. |
| `TPAGE` | `"file"` | Texture page (BMP). Optional; without it faces use vertex colours. |

## Handling
| Key | Default | Range | Meaning |
| --- | --- | --- | --- |
| `TopEnd` | 34.4 | 5 to 90 | Top speed in mph; the speedometer reads this flat out. Values over 200 are treated as internal speed units and multiplied by 0.01118. |
| `TopSpeed` | none | 5 to 90 | Used for top speed only when `TopEnd` is missing or out of range. |
| `Acc` | none | | Acceleration rating. Launch acceleration is 4.5 + 0.6 × `Acc` m/s², kept between 5 and 11 (7 when missing). |
| `SteerRate` | 2.5 | 0.5 to 10 | How fast the steering moves towards the input. |
| `SteerMod` | 0.4 | 0 to 0.9 | Share of steering lock removed at top speed. |
| `EngineRate` | 4.5 | 0.5 to 20 | How fast the motor responds to the throttle. |
| `Name` | folder name | | Optional. Only printed to the console when the car loads. |

## Sections
**`BODY { }`**: optional; the body is model slot 0 when it's missing.
| Key | Default | Meaning |
| --- | --- | --- |
| `ModelNum` | 0 | Model slot of the body. |
| `Offset` | 0 0 0 | Moves the body mesh. |

**`SPINNER { }`**: optional extra part fixed to the body, such as lights.
| Key | Default | Meaning |
| --- | --- | --- |
| `ModelNum` | none | Model slot of the part. |
| `Offset` | 0 0 0 | Position, on top of the body `Offset`. |

**`WHEEL n { }`**: one per wheel, numbered from 0.

| Key | Default | Meaning |
| --- | --- | --- |
| `Offset1` | required | Wheel centre. A wheel without it is skipped. |
| `ModelNum` | none | Model slot of the wheel mesh. Without one the wheel isn't drawn but still counts for steering. |
| `IsPresent` | true | `false` removes the wheel. |
| `IsTurnable` | false | `true` for steering wheels. |
| `SteerRatio` | none | On steering wheels. The largest absolute value is the steering lock in radians, kept between 0.15 and 0.6 (0.35 when no wheel steers). |

The wheelbase comes from the `Offset1` Z distance between the steering wheels
and the fixed ones, kept between 0.1 and 0.5 m (0.26 m by default).

## Example
The whole Gravel Basher file, cut down to what Rotor reads:

```text
TopEnd      37.0
Acc         6.757629
SteerRate   3.0
SteerMod    0.4
EngineRate  4.5

MODEL 0 "body.obj"
MODEL 1 "wheelf.obj"
MODEL 2 "wheelb.obj"
MODEL 3 "foglights.obj"
TPAGE   "car.bmp"

SPINNER {
ModelNum 3
}

WHEEL 0 {
ModelNum   1
Offset1    -20 -2 36
IsTurnable true
SteerRatio -0.4
}
WHEEL 1 {
ModelNum   1
Offset1    20 -2 36
IsTurnable true
SteerRatio -0.4
}
WHEEL 2 {
ModelNum   2
Offset1    -20 -3 -36
}
WHEEL 3 {
ModelNum   2
Offset1    20 -3 -36
}
```
