import energydata_kit


def test_all_exports_resolve():
    for name in energydata_kit.__all__:
        assert hasattr(energydata_kit, name), name
