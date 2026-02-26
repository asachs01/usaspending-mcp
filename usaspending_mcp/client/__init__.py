"""Client package — API wrapper and lazy cache with registered loaders."""

from usaspending_mcp.client import api
from usaspending_mcp.client.cache import cache


def _register_loaders() -> None:
    """Connect cache keys to their API loader functions."""
    cache.register_loader("agencies", api.get_agencies)
    cache.register_loader("naics_codes", api.get_naics_codes)
    cache.register_loader("psc_codes", api.get_psc_codes)
    cache.register_loader("cfda_programs", api.get_cfda_programs)

    async def _load_fiscal_year():
        return api.get_current_fiscal_year()

    cache.register_loader("fiscal_year", _load_fiscal_year)


_register_loaders()
