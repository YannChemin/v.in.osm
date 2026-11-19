"""Tests for the v.in.osm addon: areas, lines, reprojection."""

import pytest

from grass.tools import ToolError


def test_polygon_layer_is_imported_as_areas(osm_setup):
    """A closed building way becomes one area with its attributes."""
    tools = osm_setup.tools
    tools.v_in_osm(
        input=osm_setup.input,
        table="multipolygons",
        where="building IS NOT NULL",
        output="buildings",
    )

    info = tools.v_info(map="buildings", flags="t", format="json")
    assert info["areas"] == 1
    assert info["lines"] == 0

    records = tools.v_db_select(map="buildings", format="json")["records"]
    assert [row["building"] for row in records] == ["hangar"]


def test_line_layer_has_no_boundaries(osm_setup):
    """Default types must not turn linestrings into boundaries."""
    tools = osm_setup.tools
    tools.v_in_osm(
        input=osm_setup.input,
        table="lines",
        where="highway IS NOT NULL",
        output="roads",
    )

    info = tools.v_info(map="roads", flags="t", format="json")
    assert info["lines"] >= 1
    assert info["boundaries"] == 0


def test_data_are_reprojected_to_project_crs(osm_setup):
    """Without -o, coordinates are Lambert-93, not WGS84 degrees."""
    tools = osm_setup.tools
    tools.v_in_osm(input=osm_setup.input, table="lines", output="projected")

    info = tools.v_info(map="projected", flags="g", format="json")
    assert 6.77e6 < info["north"] < 6.78e6
    assert 5.77e5 < info["east"] < 5.79e5


def test_override_flag_keeps_source_coordinates(osm_setup):
    """With -o, the data are imported without reprojection."""
    tools = osm_setup.tools
    tools.v_in_osm(input=osm_setup.input, table="lines", output="raw", flags="o")

    info = tools.v_info(map="raw", flags="g", format="json")
    assert info["north"] == pytest.approx(48.057, abs=1e-3)


def test_polygon_layer_rejects_line_type(osm_setup):
    """Requesting only lines from a polygon layer fails loudly."""
    with pytest.raises(ToolError, match="boundary"):
        osm_setup.tools.v_in_osm(
            input=osm_setup.input, table="multipolygons", type="line", output="bad"
        )


@pytest.fixture
def reserved_gpkg(tmp_path):
    """A line layer whose fields "from" and "to" are SQL reserved words, as
    on OSM route relations."""
    from osgeo import ogr, osr

    ogr.UseExceptions()
    path = str(tmp_path / "routes.gpkg")
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ds = ogr.GetDriverByName("GPKG").CreateDataSource(path)
    layer = ds.CreateLayer("multilinestrings", srs, ogr.wkbMultiLineString)
    for name in ("name", "from", "to"):
        layer.CreateField(ogr.FieldDefn(name, ogr.OFTString))
    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetField("name", "Bus 8")
    feature.SetField("from", "Gold Souq")
    feature.SetField("to", "Al Quoz")
    feature.SetGeometry(
        ogr.CreateGeometryFromWkt(
            "MULTILINESTRING ((1.368 48.054, 1.370 48.055, 1.372 48.056))"
        )
    )
    layer.CreateFeature(feature)
    ds = None
    return path


@pytest.mark.parametrize("flags", [None, "o"])
def test_reserved_column_names_keep_attributes(osm_setup, reserved_gpkg, flags):
    """Fields named like SQL keywords are renamed, so the table survives the
    v.split and v.build.polylines copies, with and without reprojection."""
    tools = osm_setup.tools
    tools.v_in_osm(
        input=reserved_gpkg, table="multilinestrings", output="routes", flags=flags
    )

    records = tools.v_db_select(map="routes", format="json")["records"]
    assert records, "attribute table lost"
    assert records[0]["from_"] == "Gold Souq"
    assert records[0]["to_"] == "Al Quoz"
    assert records[0]["name"] == "Bus 8"
