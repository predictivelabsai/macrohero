from macrohero.fx.factors import FACTOR_UNIVERSE, FactorSpec, get_factor_by_name


def test_factor_universe_is_nonempty() -> None:
    assert len(FACTOR_UNIVERSE) >= 10


def test_each_factor_has_required_fields() -> None:
    for f in FACTOR_UNIVERSE:
        assert isinstance(f, FactorSpec)
        assert f.name
        assert f.massive_ticker
        assert f.asset_class in {"commodity", "rates", "equity", "fx", "crypto"}
        assert f.description
        assert f.transform in {"log_return", "abs_change_bp"}


def test_factor_names_are_unique() -> None:
    names = [f.name for f in FACTOR_UNIVERSE]
    assert len(names) == len(set(names))


def test_massive_tickers_are_unique() -> None:
    tickers = [f.massive_ticker for f in FACTOR_UNIVERSE]
    assert len(tickers) == len(set(tickers))


def test_get_factor_by_name_roundtrip() -> None:
    spec = FACTOR_UNIVERSE[0]
    assert get_factor_by_name(spec.name) is spec


def test_get_factor_by_name_unknown_raises() -> None:
    import pytest

    with pytest.raises(KeyError):
        get_factor_by_name("Not A Real Factor")


def test_factorspec_is_frozen() -> None:
    import dataclasses

    import pytest

    spec = FACTOR_UNIVERSE[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        spec.name = "mutated"  # type: ignore[misc]
