# Topology Contract

Use topology only when visible structural consistency matters. It declares project facts; it does not infer hidden engineering details from an image.

## Schema

~~~toml
[topology]
forbid_extra_components = true

[[topology.components]]
id = "base"
required = true
count = 1

[[topology.components]]
id = "decorative_screw"
required = true
count = 3

[[topology.relationships]]
id = "shade_mounted_on_arm"
type = "mounted_on"
members = ["shade", "arm"]
required = true
~~~

Supported relationship types:

- `integral`
- `separate`
- `mounted_on`
- `enclosed_by`
- `aligned_with`
- `shared_centers`
- `interfaces_with`

## Derived QA gates

Required components produce:

~~~text
topology.component.<component_id>.count
~~~

Required relationships produce:

~~~text
topology.relationship.<relationship_id>
~~~

When extra components are forbidden:

~~~text
topology.no_forbidden_extra_components
~~~

These gates are mandatory in QA. Missing gates invalidate the QA report. A topology `FAIL` routes to major regeneration; a required topology fact that is `NOT_VERIFIABLE` blocks acceptance.

## Boundaries

- Do not encode knife-specific assumptions globally.
- Do not invent millimeter precision from pixels.
- Do not declare hidden structure authoritative unless an approved reference/source supports it.
- Different assets may define completely different topology contracts.
