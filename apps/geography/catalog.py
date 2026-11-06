"""Carga del catalogo de departamentos y municipios.

La usan la migracion inicial (con la copia guardada en data/colombia.json) y el comando
sync_geography (con la respuesta de la API). Recibe los modelos como parametro porque
una migracion debe usar los modelos historicos, no los importados.
"""
import json
import unicodedata
from pathlib import Path

API_URL = "https://api-colombia.com/api/v1"
SNAPSHOT = Path(__file__).resolve().parent / "data" / "colombia.json"


def normalize(text: str) -> str:
    """Compara nombres sin tildes, mayusculas ni espacios de mas."""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(plain.lower().split())


def read_snapshot() -> dict:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def write_snapshot(data: dict) -> None:
    """Un registro por linea, para que el diff de una actualizacion se pueda leer."""
    lines = ["{", f'"source": {json.dumps(data["source"])},']
    for key, last in (("departments", False), ("municipalities", True)):
        rows = ",\n".join(json.dumps(row, ensure_ascii=False) for row in data[key])
        lines += [f'"{key}": [', rows, "]" if last else "],"]
    lines.append("}")
    SNAPSHOT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def from_api(departments: list[dict], cities: list[dict]) -> dict:
    """Convierte las respuestas de /Department y /City al formato de la copia local."""
    return {
        "source": API_URL,
        "departments": sorted(
            (
                {
                    "id": item["id"],
                    "name": " ".join(item["name"].split()),
                    "capital_id": item.get("cityCapitalId"),
                }
                for item in departments
            ),
            key=lambda item: item["id"],
        ),
        "municipalities": sorted(
            (
                {
                    "id": item["id"],
                    "name": " ".join(item["name"].split()),
                    "department_id": item["departmentId"],
                }
                for item in cities
            ),
            key=lambda item: item["id"],
        ),
    }


def load(data: dict, department_model, municipality_model) -> dict[str, int]:
    """Crea o actualiza cada registro por su id de la API. Nunca borra."""
    created = {"departments": 0, "municipalities": 0}
    departments = {}
    for item in data["departments"]:
        department, is_new = department_model.objects.update_or_create(
            api_id=item["id"], defaults={"name": item["name"]}
        )
        departments[item["id"]] = department
        created["departments"] += is_new

    for item in data["municipalities"]:
        department = departments.get(item["department_id"])
        if department is None:
            continue
        _, is_new = municipality_model.objects.update_or_create(
            api_id=item["id"], defaults={"name": item["name"], "department": department}
        )
        created["municipalities"] += is_new
    return created
