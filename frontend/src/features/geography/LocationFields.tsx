import { useEffect, useState } from "react";

import { api, withQuery } from "../../api/client";
import { SelectField, type Option } from "../../components/forms";

interface Place {
  id: number;
  name: string;
}

// El catálogo no cambia mientras la aplicación está abierta: se pide una sola vez.
let departments: Promise<Place[]> | null = null;
const municipalities = new Map<string, Promise<Place[]>>();

function loadDepartments(): Promise<Place[]> {
  departments ??= api<Place[]>("/geography/departments/").catch((error: unknown) => {
    departments = null;
    throw error;
  });
  return departments;
}

function loadMunicipalities(department: string): Promise<Place[]> {
  let request = municipalities.get(department);
  if (!request) {
    request = api<Place[]>(withQuery("/geography/municipalities/", { department }));
    request.catch(() => municipalities.delete(department));
    municipalities.set(department, request);
  }
  return request;
}

const toOptions = (places: Place[]): Option[] => places.map((p) => ({ value: String(p.id), label: p.name }));

/**
 * Departamento > municipio. Solo se guarda el municipio; el departamento limita la lista,
 * y el servidor rechaza un municipio que no pertenezca al departamento elegido.
 */
export function LocationFields({ department, municipality, onChange, errors }: {
  department: string;
  municipality: string;
  onChange: (next: { department: string; municipality: string }) => void;
  errors: { department?: string | undefined; municipality?: string | undefined };
}) {
  const [departmentOptions, setDepartmentOptions] = useState<Option[]>([]);
  const [municipalityOptions, setMunicipalityOptions] = useState<Option[]>([]);
  const [loadError, setLoadError] = useState<string | undefined>();

  useEffect(() => {
    loadDepartments().then((places) => setDepartmentOptions(toOptions(places))).catch(() => setLoadError("No se pudo cargar la lista."));
  }, []);

  useEffect(() => {
    if (!department) {
      setMunicipalityOptions([]);
      return;
    }
    let current = true;
    loadMunicipalities(department)
      .then((places) => current && setMunicipalityOptions(toOptions(places)))
      .catch(() => current && setLoadError("No se pudo cargar la lista."));
    return () => {
      current = false;
    };
  }, [department]);

  return (
    <>
      <SelectField id="department" label="Departamento" value={department} options={departmentOptions}
        placeholder="Selecciona un departamento" error={errors.department ?? loadError}
        onChange={(event) => onChange({ department: event.target.value, municipality: "" })} />
      <SelectField id="municipality" label="Municipio" value={municipality} options={municipalityOptions}
        placeholder={department ? "Selecciona un municipio" : "Selecciona primero un departamento"}
        disabled={!department} error={errors.municipality}
        onChange={(event) => onChange({ department, municipality: event.target.value })} />
    </>
  );
}
