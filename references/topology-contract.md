# Topology Contract

Use topology only when visible or otherwise authoritative structural facts matter to the task. It is asset-specific data, not a universal knife/character rule.

## Components

~~~toml
[topology]
prohibited_extra_components = false

[[topology.components]]
id = "body"
required = true
count = 1
evidence = "authoritative"
~~~

`count` is optional. `evidence` is one of:

- `authoritative`: may become a required hard QA gate.
- `provisional`: useful working hypothesis; cannot be promoted to approved structure.
- `unknown`: explicitly unresolved.

## Relationships

~~~toml
[[topology.relationships]]
id = "panel_mounted_on_body"
type = "mounted_on"
members = ["panel", "body"]
required = true
evidence = "authoritative"
~~~

Supported relationship types:

`integral`, `continuous`, `separate`, `mounted_on`, `enclosed_by`, `aligned_with`, `shared_centers`, `interface`.

The validator checks the contract shape. The Host/Agent still performs the visual judgment.

## QA mapping

Authoritative required components compile to hard gates such as:

- `topology.component.body.present`
- `topology.component.knob.count`

Authoritative required relationships compile to:

- `topology.relationship.<relationship-id>`

These gates must appear explicitly in a complete QA report. Core topology/count/identity failures route to major regeneration or blocking, not a cosmetic repair.

Do not claim hidden geometry from a single beauty render. Put unresolved facts in provisional/unknown fields instead.
