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
| admin@ergopostura.test | Administrador | Todo, incluidos los usuarios; no aplica RULA, pero puede reabrir evaluaciones |
| ingeniero@ergopostura.test | Ingeniero industrial | Todas las empresas, que puede crear y editar; visitas en solo lectura; aplica RULA |
| empresa@ergopostura.test | Empresa | Solo su empresa, sin editar; registra y edita sus visitas; ve sus evaluaciones terminadas |
| evaluador@ergopostura.test | Evaluador | Todas las visitas en solo lectura; aplica RULA; sin acceso al módulo de empresas |
| consulta@ergopostura.test | Consulta de resultados | Evaluaciones terminadas e indicadores de todas las empresas |
| tareas@ergopostura.test | Responsable de tarea | Recomendaciones por atender de todas las empresas, sin acceso a las fotografías |
| evaluador2@ergopostura.test | Evaluador | Igual que el otro evaluador; sirve para probar que cada uno edita solo sus evaluaciones |
| empresa2@ergopostura.test | Empresa | Solo Textiles Antioquia S.A.; sirve para probar que una empresa no ve a otra |

`seed_demo` crea datos ficticios para probar el sistema a mano:

- Seis empresas en cinco departamentos, una de ellas inactiva, con sus sedes, áreas y puestos.
- Por cada puesto, una visita pasada con su evaluación terminada y otra futura, en horas distintas para llenar el calendario.
- Evaluaciones con los cuatro niveles de acción de RULA, calculados con el motor real, y algunas en curso.
- Recomendaciones atendidas y pendientes para el seguimiento.
- En lugar de fotografías, figuras de perfil dibujadas con los ángulos de cada postura.

Se puede ejecutar varias veces sin duplicar nada: solo completa los puestos que aún no tienen evaluaciones. Se niega a ejecutarse con `DEBUG` desactivado.

## Publicar en Render

El archivo `render.yaml` define el servicio web y la base de datos.

1. En Render, elige **New > Blueprint** y conecta este repositorio.
2. Completa las variables que pide:
   - `DJANGO_ADMIN_EMAIL` y `DJANGO_ADMIN_PASSWORD`: tu cuenta de administrador.
   - `DEMO_SEED_PASSWORD` (opcional): crea las cuentas de demostración con esa clave. Debe ser distinta a la de este README.
3. Cada `git push` a `main` vuelve a desplegar la aplicación.

**Límites del plan gratis:**

- El servicio se apaga tras 15 minutos sin tráfico y tarda cerca de un minuto en volver.
- La base de datos tiene 1 GB y **expira 30 días después de crearla**; tras 14 días más de gracia, Render la borra.
- No hay disco persistente. Por eso las fotografías se guardan en PostgreSQL.

## Comandos útiles

```powershell
docker compose exec web python manage.py test --settings=config.settings.test
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py sync_geography   # actualiza municipios desde api-colombia.com
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
  geography/       Departamentos y municipios de api-colombia.com
  companies/       Empresa > sede > área > puesto, y reglas del NIT
  visits/          Visitas acordadas: calendario por mes o semana, y agenda
  evaluations/     Evaluación, posturas, fotografías, análisis y recomendaciones
  indicators/      Indicadores por empresa y comparación entre áreas
  tasks/           Tareas pendientes del proceso
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
- **Ubicación del catálogo oficial:** empresas y sedes eligen departamento y luego municipio, de los datos de [api-colombia.com](https://api-colombia.com). Se guarda una copia en `apps/geography/data/colombia.json` que la migración carga, así que los formularios funcionan aunque la API no responda. `sync_geography` la actualiza sin borrar nada, y un municipio en uso no se puede eliminar.
- **Nombres sin repetir por nivel:** no puede haber dos sedes iguales en una empresa, ni dos áreas iguales en una sede, ni dos puestos iguales en un área. No distingue mayúsculas.
- **Jerarquía coherente:** la empresa de un puesto se obtiene recorriendo la cadena; ese dato no se duplica (RNF-002).
- **Calendario de visitas:** vista por mes y por semana, con un color por empresa. Quien registra visitas puede crear una desde un día o una hora libre; los días y horas pasados no lo ofrecen. Cada rol ve solo las visitas de su alcance.
- **Visitas coherentes:** solo se guarda el puesto; la sede y la empresa salen de la jerarquía. No se aceptan fechas pasadas ni dos visitas al mismo puesto en la misma fecha y hora.
- **Evaluaciones trazables:** solo su autor la modifica, y solo mientras está en curso. Terminada queda de solo lectura; únicamente el administrador puede reabrirla.
- **Para terminar una evaluación:** toda postura debe tener su análisis RULA, y desde el nivel de acción 2, al menos una recomendación.
- **Fotografías protegidas:** se guardan en PostgreSQL y solo las recibe quien puede ver la evaluación. Se reducen a 1600 px y se les quitan los metadatos, como la ubicación GPS.
- **Nada se pierde por accidente:** no se puede borrar un nivel que tenga hijos (RNF-001).
- **Acceso:** sin permiso se responde 403, y los datos de otra empresa responden 404.
- **Panel de administración con la marca del sistema:** `/admin/` usa la paleta y el logo de ErgoPostura, el mismo inicio y cierre de sesión que el resto del sistema, y no muestra los grupos de Django, porque los permisos salen del rol.

## Avance frente a los requisitos

| Requisitos | Estado |
|---|---|
| RF-001, 002, 003, 005 (empresas, sedes, áreas, puestos) | Listo |
| RF-006 (visitas) | Listo |
| RNF-001, 002 (persistencia e integridad) | Listo para lo construido; se extiende en cada módulo |
| RF-007 a 014 (evaluación, actividad, fotografías, posturas) | Listo |
| RF-015, 016 (segmentos y ángulos manuales) | Listo |
| RF-017 a 021, RNF-004 (puntuación, riesgo y semáforo) | Listo |
| RF-022 (recomendaciones del evaluador) | Listo |
| RF-023 a 025 (consulta y resumen) | Listo |
| RNF-003 (fidelidad al método) | Implementado; faltan casos de referencia aprobados |
| RF-004 (contexto del trabajador) | Campo de texto opcional, sin datos personales; falta acordar el contenido |
| RF-026, 027 (indicadores y comparación) | Listo |
| RF-028 (informe imprimible y en PDF) | Listo |
| RF-029 (tareas pendientes) | Listo |

## Decisiones tomadas

| Decisión | Resultado |
|---|---|
| D1, método | RULA |
| D2, medición de ángulos | Manual, en grados |
| D3, puntuaciones | Las calcula el sistema a partir de lo que registra el evaluador |
| D4, semáforo | Nivel 1 verde, niveles 2 y 3 amarillo, nivel 4 rojo; siempre con el texto del nivel |
| D5, recomendaciones | Las escribe el evaluador después de ver el resultado |
| D6, indicadores | Puestos por color de riesgo, por empresa y por área. Cuenta la evaluación terminada más reciente de cada puesto y su postura de mayor riesgo; no se promedia ni se hace ranking |
| D7, informe | Vista para imprimir o guardar como PDF desde el navegador, solo de evaluaciones terminadas |
| D8, tareas | Evaluaciones en curso de cada profesional y recomendaciones por atender, que marcan la empresa o el responsable de tarea |
| D9, cuentas de trabajadores | El trabajador es la persona evaluada y no usa el sistema |
| Quién aplica RULA | El ingeniero industrial o el evaluador |

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
- **Casos de referencia:** RNF-003 pide casos aprobados; hoy solo hay casos calculados a mano y ejemplos publicados.
