# v.in.osm

GRASS GIS addon that imports OpenStreetMap data — `.osm`, `.osm.pbf`, or an
osm2pgsql PostgreSQL/PostGIS database — into a GRASS vector map.

It wraps *v.in.ogr* with the two things OSM data needs that a plain OGR import
gets wrong:

- **Geometry-aware feature types.** Polygon layers (`multipolygons`,
  `planet_osm_polygon`) are imported as areas with boundaries, centroids and
  their attributes; point and line layers (`lines`, `planet_osm_line`) as
  points and lines. Types given in **type** that do not match the layer
  geometry are ignored, so closed building ways no longer turn into loose
  lines and linestrings no longer turn into dangling boundaries.
- **Reprojection on the fly.** By default the selected features (after the
  **where** filter) are reprojected to the CRS of the current project with
  GDAL before import, so WGS84 OSM data lands correctly in a projected
  project. `-o` skips it.

Line layers are additionally split at every vertex and rebuilt into polylines
(*v.split* + *v.build.polylines*), which is what makes OSM ways usable as
network geometry in GRASS.

```
v.in.osm input=map.osm.pbf table=multipolygons output=buildings \
         where="building IS NOT NULL"
```

## Requirements

- GRASS GIS (built with OGR support)
- GDAL Python bindings, with the [OSM driver](https://gdal.org/drivers/vector/osm.html)
- For database input: PostgreSQL, PostGIS, [osm2pgsql](https://wiki.openstreetmap.org/wiki/Osm2pgsql)

## Install

From the official addons repository, inside a GRASS session:

```sh
g.extension extension=v.in.osm
```

From this repository instead — `g.extension` clones the URL and builds the tool
locally:

```sh
g.extension extension=v.in.osm url=https://github.com/YannChemin/v.in.osm.git
```

Or build and install against an installed GRASS from a checkout:

```sh
make MODULE_TOPDIR="$(grass --config path)"
```

## Usage

```
v.in.osm input=name table=name output=name [type=string[,...]] [where=sql_query] [-ol]
```

| Key | Parameter | Description |
| --- | --- | --- |
| `input` | name | OSM/PBF file, or a DB connection string (`input` is required) |
| `table` | name | OGR layer to import, e.g. `multipolygons`, `lines` |
| `output` | name | Name of the output vector map |
| `type` | list of `point,line,boundary,centroid` | Feature types to import; defaults to all four, then narrowed to the layer's geometry |
| `where` | SQL query | Attribute filter, e.g. `"highway IS NOT NULL"` |

| Flag | Meaning |
| --- | --- |
| `-o` | Override the projection check: assume the data are already in the project's CRS and import without reprojection |
| `-l` | List the OGR layers available in `input` and exit (no `table`/`output` needed) |

`v.in.osm -l input=saarland-latest.osm.pbf` is the quickest way to find the
layer names of a file.

### Examples

Points and lines from an osm2pgsql database, filtered to roads:

```sh
v.in.osm input="PG:host=localhost dbname=gis user=ostepok" table=planet_osm_line \
         type=point,line output=roads where="highway is not null"
```

Roads from a PBF extract:

```sh
v.in.osm input=saarland-latest.osm.pbf table=lines output=roads \
         where="highway is not null"
```

Buildings and land use as areas in a projected project:

```sh
v.in.osm input=saarland-latest.osm.pbf table=multipolygons output=buildings \
         where="building IS NOT NULL"
v.in.osm input=saarland-latest.osm.pbf table=multipolygons output=landuse \
         where="landuse IS NOT NULL OR \"natural\" IS NOT NULL"
```

Full manual page: [`v.in.osm.md`](v.in.osm.md), which is also what GRASS ships
as [`v.in.osm.html`](v.in.osm.html). Keep the two in sync when you edit one.

## Repository layout

```
v.in.osm.py                  the module (GRASS parser options in the header comments)
v.in.osm.md / v.in.osm.html  manual page and its HTML form, installed as DOCFILES
Makefile / CMakeLists.txt    build as a GRASS addon (Autotools / CMake)
tests/                       pytest suite + a small synthetic OSM file
```

## Tests

The suite runs the tool by name, so install it into the GRASS you test against
first. It creates a throwaway Lambert-93 (EPSG:2154) project and imports
`tests/data_small.osm` into it, which checks areas, line handling, and both
reprojected and `-o` coordinates.

```sh
make MODULE_TOPDIR="$(grass --config path)"
export PYTHONPATH="$(grass --config python_path):${PYTHONPATH}"
export LD_LIBRARY_PATH="$(grass --config path)/lib:${LD_LIBRARY_PATH}"
pytest tests/
```

## Origin

This is a standalone copy of `src/vector/v.in.osm` from
[OSGeo/grass-addons](https://github.com/OSGeo/grass-addons), where the tool
belongs to the `vector` category. Upstream development happens there — changes
made here should go back as a pull request against that repository.

The module is based on Stepan Turek's original *v.in.osm* (© 2016), with `-l`
layer listing by Markus Neteler; the geometry-aware import and the GDAL
reprojection were added in
[grass-addons PR #1863](https://github.com/OSGeo/grass-addons/pull/1863).

## License

The module header states GPL-2.0-or-later, the GRASS convention. The
`LICENSE` file currently in this repository is the Unlicense text and does not
match it; it should be replaced with GPL-2.0-or-later.
