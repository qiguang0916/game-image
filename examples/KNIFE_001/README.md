# KNIFE_001 example

This example demonstrates a 3D Hero Prop reference workflow.

The image files themselves are intentionally not stored in this repository. The TOML files show how approved Master References would be registered and how a local material edit would be constrained.

## Scenario

Requested edit:

“Keep KNIFE_001 unchanged except for the three existing handle rivets. Change only their finish to subtle brushed cold-silver steel.”

## Why this is a local edit

The assembled master already has:

- correct overall identity;
- correct blade and handle silhouette;
- correct camera/framing;
- correct rivet count and positions.

Therefore the operation should not regenerate the entire knife.

## Files

- asset.toml — approved reference atlas and locks.
- edits/rivets-brushed-silver.toml — delta-only edit request.
- qa/expected.toml — example passing QA record.

Run:

~~~bash
python3 scripts/validate_project.py examples/KNIFE_001
~~~
