# ErgoPostura

Sistema para gestionar evaluaciones ergonómicas de puestos de trabajo.
Django 5.2, PostgreSQL 16, HTMX y Docker.

## Cómo ejecutarlo

Requisito: [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose exec web python manage.py seed_demo
```

Abre http://localhost:8000. Todos los usuarios de demostración usan la clave `ErgoDemo2026!`:

| Correo | Rol | Qué ve |
|---|---|---|
| admin@ergopostura.test | Administrador | Todo, incluidos los usuarios |
| ingeniero@ergopostura.test | Ingeniero industrial | Todas las empresas, que puede crear y editar; visitas en solo lectura |
| empresa@ergopostura.test | Empresa | Solo su empresa, sin editar; registra y edita sus visitas |
| evaluador@ergopostura.test | Evaluador | Todas las visitas en solo lectura; sin acceso a empresas |
| consulta@ergopostura.test | Consulta de resultados | Su panel; módulo pendiente |
| tareas@ergopostura.test | Responsable de tarea | Su panel; módulo pendiente |

`seed_demo` crea datos ficticios y se niega a ejecutarse con `DEBUG` desactivado.

## Comandos útiles

```powershell
docker compose exec web python manage.py test --settings=config.settings.test
docker compose exec web python manage.py makemigrations
docker compose logs -f web
docker compose down        # conserva la base de datos
docker compose down -v     # BORRA la base de datos
```

## Estructura

```
config/            Configuración por entorno (base, dev, prod, test) y URLs
apps/
  core/            Piezas compartidas: formularios modales, navegación, iconos
  accounts/        Usuarios, roles y política de permisos
  companies/       Empresa > sede > área > puesto, y reglas del NIT
  visits/          Visitas acordadas
  rula/            Cálculo del método RULA, sin dependencias de Django
  dashboard/       Un panel por rol
templates/         HTML por módulo
static/            design-system.css (exportado de Figma, no se edita) y app.css
docker/            Script de arranque del contenedor
```

## Cómo está organizado el código

Cada archivo tiene una sola responsabilidad:

| Archivo | Responsabilidad |
|---|---|
| `views.py` | Atender la petición HTTP; no contiene reglas de negocio |
| `forms.py` | Validar y normalizar lo que escribe el usuario |
| `models.py` | Datos y restricciones de la base de datos |
| `selectors.py` | Consultas de lectura, siempre limitadas al alcance del usuario |
| `permissions.py` | Qué puede hacer cada rol |
| `nit.py` | Reglas del NIT, sin dependencias de Django |

Para extender el sistema sin modificar lo que ya funciona:

- **Permisos de un rol:** `ROLE_CAPABILITIES` en `apps/accounts/permissions.py`.
- **Módulo en el menú:** `NAV_ITEMS` en `apps/core/navigation.py`.
- **Panel de un rol:** `PANELS` en `apps/dashboard/panels.py`.

## Reglas que el sistema garantiza

- **NIT único:** se guarda solo el número base, así que `900.123.456-8`, `900123456-8` y `900123456` son la misma empresa. Se valida el dígito de verificación de la DIAN.
- **Doble protección:** el formulario da un mensaje claro y la base de datos rechaza el duplicado aunque dos personas guarden a la vez.
- **Nombres sin repetir por nivel:** no puede haber dos sedes iguales en una empresa, ni dos áreas iguales en una sede, ni dos puestos iguales en un área. No distingue mayúsculas.
- **Jerarquía coherente:** la empresa de un puesto se obtiene recorriendo la cadena; ese dato no se duplica (RNF-002).
- **Visitas coherentes:** solo se guarda el puesto; la sede y la empresa salen de la jerarquía. No se aceptan fechas pasadas ni dos visitas al mismo puesto en la misma fecha y hora.
- **Nada se pierde por accidente:** no se puede borrar un nivel que tenga hijos (RNF-001).
- **Acceso:** sin permiso se responde 403, y los datos de otra empresa responden 404.

## Avance frente a los requisitos

| Requisitos | Estado |
|---|---|
| RF-001, 002, 003, 005 (empresas, sedes, áreas, puestos) | Listo |
| RF-006 (visitas) | Listo |
| RNF-001, 002 (persistencia e integridad) | Listo para lo construido; se extiende en cada módulo |
| RF-017 a 020, RNF-003 (puntuación y nivel de riesgo RULA) | Motor de cálculo listo y probado; falta conectarlo a la evaluación |
| RF-021, RNF-004 (semáforo) | Lógica lista; la correspondencia de colores espera aprobación (D4) |
| RF-007 a 014 (evaluación, actividad, fotografías, posturas) | Siguiente |
| RF-015, 016 (segmentos y ángulos) | Siguiente: registro manual de ángulos (D2) |
| RF-023 a 025 (consulta y resumen) | Pendiente |
| RF-022 (recomendaciones) | Bloqueado por la decisión D5 |
| RF-004, 026 a 029 | Bloqueado por las decisiones D6 a D9 |

## Decisiones tomadas

| Decisión | Resultado |
|---|---|
| D1, método | RULA |
| D2, medición de ángulos | Manual, en grados |
| D9, cuentas de trabajadores | El trabajador es la persona evaluada y no usa el sistema |

## Método RULA

El cálculo está en `apps/rula/`, en Python puro, sin base de datos.

**Fuente:** McAtamney L. y Corlett E. N. (1993). *RULA: a survey method for the investigation of work-related upper limb disorders.* Applied Ergonomics, 24(2), 91-99.

| Elemento | Cómo se verificó |
|---|---|
| Tablas A y B | Celda por celda contra las tablas 1 y 2 del artículo |
| Tabla C | Contra la figura 6 en las celdas legibles; la zona oscura del escaneo, contra la hoja de trabajo de Neese Consulting |
| Carga o fuerza | Texto y figura 5 del artículo |
| Niveles de acción | Texto del artículo |

Algunas hojas de trabajo simplifican la carga y dan 3 puntos a cualquier carga de más de 10 kg. Aquí se usa el artículo original: más de 10 kg intermitente puntúa 2.

**Puntos que debe validar el responsable metodológico:**

- **Límites entre rangos:** el artículo usa rangos que se tocan, como 0-10° y 10-20°. El límite va al rango inferior, salvo que el texto diga «o más».
- **Tronco en extensión:** el artículo no lo puntúa, así que el sistema lo rechaza en vez de inventar un valor.
- **Carga estática o repetida de menos de 2 kg:** el artículo no la define. El evaluador debe elegir una de las categorías publicadas.
- **Brazo apoyado:** si el ajuste de -1 deja el puntaje en 0, se mantiene en 1, el mínimo de la tabla.
- **Semáforo (D4):** nivel 1 verde, niveles 2 y 3 amarillo, nivel 4 rojo.
- **Casos de referencia:** RNF-003 pide casos aprobados; hoy solo hay casos calculados a mano y ejemplos publicados.
