"""This gin's published rates, one set per crop year.

Rates are in the code rather than in the book on purpose. They are published
once a season, they apply to everybody, and a rate that can be edited per book
is a rate that will differ between the office copy and the backup. Changing one
is a release of this package, which is exactly the ceremony it deserves.

The seed price is the one number here that is not really published. It moves
with the oil mill contract, so what is stored is the season's contracted price
and a statement worked out against it says which season's price it used.
"""

from __future__ import annotations

from ginstand.charges.tariff import Basis, Tariff, TariffLine
from ginstand.errors import ScheduleError
from ginstand.units.money import Money, money
from ginstand.warehouse.storage import StorageTariff

TARIFFS: dict[int, Tariff] = {
    2025: Tariff(
        crop_year=2025,
        lines=(
            TariffLine("GIN", "Ginning", Basis.PER_CWT, money("3.75")),
            TariffLine("BAG", "Bagging and ties", Basis.PER_BALE, money("9.50")),
            TariffLine("HAUL", "Module hauling", Basis.PER_MODULE, money("55.00")),
            TariffLine("CLASS", "Classing fee", Basis.PER_BALE, money("1.05")),
            TariffLine("CHECK", "Bale weighing and checking", Basis.PER_BALE, money("0.85")),
            TariffLine(
                "REST", "Moisture restoration", Basis.PER_BALE, money("2.25"), optional=True
            ),
            TariffLine("PICK", "Contamination picking", Basis.PER_MODULE, money("38.00"), True),
            TariffLine("ADMIN", "Season administration", Basis.FLAT, money("40.00")),
        ),
    ),
    2026: Tariff(
        crop_year=2026,
        lines=(
            TariffLine("GIN", "Ginning", Basis.PER_CWT, money("3.95")),
            TariffLine("BAG", "Bagging and ties", Basis.PER_BALE, money("9.90")),
            TariffLine("HAUL", "Module hauling", Basis.PER_MODULE, money("58.00")),
            TariffLine("CLASS", "Classing fee", Basis.PER_BALE, money("1.10")),
            TariffLine("CHECK", "Bale weighing and checking", Basis.PER_BALE, money("0.90")),
            TariffLine(
                "REST", "Moisture restoration", Basis.PER_BALE, money("2.35"), optional=True
            ),
            TariffLine("PICK", "Contamination picking", Basis.PER_MODULE, money("40.00"), True),
            TariffLine("ADMIN", "Season administration", Basis.FLAT, money("42.00")),
        ),
    ),
}

SEED_PRICES: dict[int, Money] = {
    2025: money("210.00"),
    2026: money("225.00"),
}
"""The contracted price for cottonseed, per ton."""

STORAGE: dict[int, StorageTariff] = {
    2025: StorageTariff(
        receiving=money("3.10"),
        per_day=money("0.08"),
        load_out=money("2.40"),
        free_days=10,
        minimum_days=60,
    ),
    2026: StorageTariff(
        receiving=money("3.25"),
        per_day=money("0.085"),
        load_out=money("2.50"),
        free_days=10,
        minimum_days=60,
    ),
}


def _known(crop_year: int, what: str, table: dict[int, object]) -> None:
    if crop_year not in table:
        raise ScheduleError(
            f"no {what} is published for crop year {crop_year}, "
            f"the ones published are {', '.join(str(year) for year in sorted(table))}"
        )


def tariff_for(crop_year: int) -> Tariff:
    """The ginning tariff for a crop year."""
    _known(crop_year, "ginning tariff", dict(TARIFFS))
    return TARIFFS[crop_year]


def seed_price_for(crop_year: int) -> Money:
    """The contracted seed price for a crop year, per ton."""
    _known(crop_year, "seed price", dict(SEED_PRICES))
    return SEED_PRICES[crop_year]


def storage_for(crop_year: int) -> StorageTariff:
    """The warehouse contract for a crop year."""
    _known(crop_year, "storage contract", dict(STORAGE))
    return STORAGE[crop_year]


def published_years() -> tuple[int, ...]:
    """Every crop year with a full set of rates published."""
    return tuple(sorted(set(TARIFFS) & set(SEED_PRICES) & set(STORAGE)))
