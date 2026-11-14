"""Conteos de la estructura de una empresa (sedes, areas, puestos y trabajadores activos)."""
from .models import Company


def structure_counts(company: Company) -> dict[str, int]:
    """Requiere la empresa cargada con selectors.with_structure para no repetir consultas."""
    sites = list(company.sites.all())
    areas = [area for site in sites for area in site.areas.all()]
    positions = [position for area in areas for position in area.positions.all()]
    workers = [worker for position in positions for worker in position.workers.all() if worker.is_active]
    return {"sites": len(sites), "areas": len(areas), "positions": len(positions), "workers": len(workers)}
