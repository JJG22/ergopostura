# ErgoPostura

Sistema con el que un ingeniero industrial presta el servicio de evaluación ergonómica (método RULA)
a empresas cliente: contratos, visitas, evaluaciones y seguimiento.
Django 5.2, MySQL 8.4, HTMX y Docker.

## Cómo ejecutarlo

Requisito: [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose exec web python manage.py seed_demo
```

Abre http://localhost:8000.

### Roles

| Rol | Quién es | Qué hace | Qué no hace |
|---|---|---|---|
| Soporte técnico | Los desarrolladores | Crea la cuenta del ingeniero, da soporte a todas las cuentas (datos, contraseña temporal, activar o desactivar) y abre el panel técnico en modo consulta | No ve empresas, contratos, visitas ni evaluaciones; no agenda ni evalúa |
| Ingeniero industrial | Quien presta el servicio | Registra empresas, sedes, áreas, puestos y trabajadores; gestiona los contratos; crea los accesos de las empresas; registra si cada visita se hizo; evalúa con RULA | No agenda visitas: las agenda la empresa |
| Empresa cliente | La empresa que contrata | Agenda, reprograma y cancela visitas en sus sedes; ve sus resultados, su contrato y sus indicadores; marca recomendaciones como atendidas | No ve otras empresas ni evaluaciones en curso |

### Cómo se presta el servicio

1. Soporte crea la cuenta del ingeniero con una **contraseña temporal**. Al primer ingreso el sistema obliga a cambiarla.
2. El ingeniero registra la empresa y su estructura, sube el **contrato** en PDF y crea el **acceso de la empresa** (correo y contraseña temporal).
3. La empresa **agenda la visita** en el calendario: dentro de la vigencia del contrato, de lunes a sábado entre 7:00 y 18:00, con al menos una hora de anticipación y sin cruzarse con otra visita del ingeniero. Las visitas de otras empresas le aparecen como «Ocupado».
4. El ingeniero ve la visita en su calendario con su nivel: *Programada*, *Cercana* (3 días o menos), *Hoy*, *En curso*, *Por cerrar* (ya pasó y falta registrarla), *Realizada* o *Cancelada*.
5. Al terminar la visita la registra como **realizada**. Solo entonces puede crear evaluaciones: **sin visita realizada no hay evaluación**, y el puesto debe ser de la sede visitada.
6. La empresa ve las evaluaciones terminadas y atiende las recomendaciones.

### Datos de demostración (solo en tu computador)

`seed_demo` crea datos ficticios con ese flujo completo. Todas las cuentas usan la clave `ErgoDemo2026!`:

| Correo | Rol |
|---|---|
| admin@ergopostura.test | Soporte técnico |
| ingeniero@ergopostura.test | Ingeniero industrial |
| empresa@ergopostura.test | Empresa: Café Montaña S.A.S. |
| empresa2@ergopostura.test | Empresa: Textiles Antioquia S.A. (sirve para probar que una empresa no ve a otra) |

Incluye seis empresas (una inactiva), trabajadores, un contrato con PDF por empresa (uno por vencer y otro vencido), visitas realizadas, por cerrar, futuras y canceladas, evaluaciones con los cuatro niveles de RULA y recomendaciones atendidas y pendientes. Se puede ejecutar varias veces sin duplicar nada. **Se niega a ejecutarse en producción**: allí el sistema arranca solo con la cuenta de soporte.

## Publicar en Render

La aplicación publicada está en **https://ergopostura.onrender.com**.


La aplicación corre en Render y la base de datos MySQL en [Aiven](https://aiven.io). Render no ofrece MySQL administrado.

1. En Aiven, crea un servicio MySQL y copia su **Service URI** (empieza por `mysql://` e incluye la contraseña).
2. En Render, elige **New > Blueprint** y conecta este repositorio. No lo crees como *Web Service* suelto: así no lee `render.yaml`.
3. Completa las variables que pide:
   - `DATABASE_URL`: la Service URI de Aiven.
   - `DJANGO_ADMIN_EMAIL` y `DJANGO_ADMIN_PASSWORD`: la cuenta de soporte. Es la única que se crea sola; las demás se crean desde la aplicación.
   - `ANTHROPIC_API_KEY` (opcional): activa la lectura de contratos con IA. Sin ella, los contratos funcionan sin resumen automático.
4. Cada `git push` a `main` vuelve a desplegar la aplicación.

**Límites:**

- El plan gratis de Render apaga el servicio tras 15 minutos sin tráfico y tarda cerca de un minuto en volver.
- La base de Aiven usa créditos de prueba por 30 días, creada el 8 de noviembre de 2026. Al terminar se apaga, salvo que se agregue un método de pago (plan Developer, 5 USD al mes).
- Render no tiene disco persistente en el plan gratis. Por eso las fotografías y los contratos se guardan en MySQL.

## Ver la base con MySQL Workbench

Con `docker compose up` corriendo, crea una conexión con host `127.0.0.1`, puerto `3307`, y el usuario y la contraseña de `MYSQL_USER` y `MYSQL_PASSWORD` de tu `.env`.

## Base de datos y SQL

- [docs/sql/esquema.sql](docs/sql/esquema.sql): estructura completa de la base en MySQL.
- [docs/sql/consultas.sql](docs/sql/consultas.sql): consultas principales con nombre y descripción.
- [docs/modelo-entidad-relacion.png](docs/modelo-entidad-relacion.png): modelo entidad-relación.
- [docs/diagrama-navegacion.png](docs/diagrama-navegacion.png): pantallas y navegación por rol.
- [docs/bpmn-as-is.png](docs/bpmn-as-is.png) y [docs/bpmn-to-be.png](docs/bpmn-to-be.png): proceso actual y proceso propuesto en BPMN.
- [docs/vistas/](docs/vistas/): pantallazos de las vistas de cada rol, con datos de demostración.

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
  companies/       Empresa > sede > área > puesto > trabajador, y reglas del NIT
  contracts/       Contratos con su PDF, vigencias y lectura con IA (Claude)
  visits/          Visitas que agenda la empresa: reglas, niveles, calendario y agenda
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
- **Calendario de visitas:** vista por mes y por semana, con un color por empresa y el nivel de cada visita. La empresa agenda desde un día o una hora libre; los horarios de otras empresas le aparecen como «Ocupado», sin ningún dato de ellas.
- **Agenda sin cruces:** dos visitas no se cruzan aunque se agenden al mismo tiempo: el formulario lo revisa y al guardar se vuelve a revisar con la agenda bloqueada en la base de datos.
- **Un contrato a la vez:** las vigencias de los contratos de una empresa no se cruzan; al renovar se registra uno nuevo. No se puede acortar ni eliminar un contrato si deja visitas programadas sin cobertura.
- **Evaluación con visita:** toda evaluación exige una visita realizada (también en la base de datos) y un puesto de la sede visitada.
- **Evaluaciones trazables:** solo su autor la modifica, y solo mientras está en curso. Terminada queda de solo lectura; el ingeniero puede reabrirla.
- **Para terminar una evaluación:** toda postura debe tener su análisis RULA, y desde el nivel de acción 2, al menos una recomendación.
- **Fotografías protegidas:** se guardan en MySQL y solo las recibe quien puede ver la evaluación. Se reducen a 1600 px y se les quitan los metadatos, como la ubicación GPS.
- **Nada se pierde por accidente:** no se puede borrar un nivel que tenga hijos (RNF-001).
- **Acceso:** sin permiso se responde 403, y los datos de otra empresa responden 404.
- **Cuentas:** contraseña temporal que se cambia al primer ingreso; las cuentas se desactivan en vez de borrarse; nadie se desactiva a sí mismo; el ingeniero solo gestiona cuentas de empresa.
- **Trabajadores:** son datos personales (Ley 1581 de 2012). Solo los ven el ingeniero y su empresa, y el documento no se repite dentro de una empresa.
- **Panel técnico:** `/admin/` usa la marca de ErgoPostura y el mismo inicio de sesión. Las cuentas se gestionan desde la aplicación; los datos del negocio se ven solo en modo consulta.

## Avance frente a los requisitos

| Requisitos | Estado |
|---|---|
| RF-001, 002, 003, 005 (empresas, sedes, áreas, puestos) | Listo |
| RF-006 (visitas) | Listo: las agenda la empresa y las cierra el ingeniero |
| RNF-001, 002 (persistencia e integridad) | Listo para lo construido; se extiende en cada módulo |
| RF-007 a 014 (evaluación, actividad, fotografías, posturas) | Listo |
| RF-015, 016 (segmentos y ángulos manuales) | Listo, con sugerencia opcional de ángulos con IA |
| RF-017 a 021, RNF-004 (puntuación, riesgo y semáforo) | Listo |
| RF-022 (recomendaciones del ingeniero) | Listo |
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
| D3, puntuaciones | Las calcula el sistema a partir de lo que registra el ingeniero |
| D4, semáforo | Nivel 1 verde, niveles 2 y 3 amarillo, nivel 4 rojo; siempre con el texto del nivel |
| D5, recomendaciones | Las escribe el ingeniero después de ver el resultado |
| D6, indicadores | Puestos por color de riesgo, por empresa y por área. Cuenta la evaluación terminada más reciente de cada puesto y su postura de mayor riesgo; no se promedia ni se hace ranking |
| D7, informe | Vista para imprimir o guardar como PDF desde el navegador, solo de evaluaciones terminadas |
| D8, tareas | Evaluaciones en curso del ingeniero y recomendaciones por atender, que marca la empresa |
| D9, trabajadores | Se registran por puesto y se puede indicar quién fue observado; no tienen cuenta |
| Quién aplica RULA | El ingeniero industrial, siempre a partir de una visita realizada |

## Lectura de contratos con IA

En *Contratos*, la IA (Claude, de Anthropic) lee el PDF y da un resumen: tipo de contrato, servicio, empresa, NIT, encargado, vigencia y duración, valor, obligaciones, terminación, tratamiento de datos y lo que conviene revisar.

- **Al registrar:** el botón *Leer contrato* llena los campos del formulario, marcados como «Sugerido por IA», y propone la empresa por su NIT. Nada se guarda hasta pulsar *Guardar*.
- **En el detalle:** el resumen se compara con lo registrado y marca lo que no coincide. Si el NIT del documento no es el de la empresa, lo avisa.
- **Cada documento se lee una sola vez:** la lectura se guarda por la huella del archivo y no se vuelve a pagar.
- **Respuesta con formato fijo:** se pide un JSON con esquema (salida estructurada) y cada campo se valida otra vez en el servidor. El texto del contrato se trata como dato, nunca como instrucción.
- **Privacidad:** el PDF se envía a la API de Anthropic para leerlo. Se activa con `ANTHROPIC_API_KEY`; el modelo se cambia con `CONTRACT_AI_MODEL` (por defecto `claude-opus-5-5`).

## Sugerencia de ángulos con IA

En la pantalla de análisis RULA, el botón **Sugerir** detecta el cuerpo en la fotografía con [MediaPipe Pose](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker) y propone los cinco ángulos del lado evaluado.

- **Corre en el navegador.** La fotografía no se envía a ningún servicio. La librería (versión fija 0.10.14, desde jsDelivr) y el modelo (desde Google) se descargan solo al pulsar el botón; sin internet, se registran los ángulos a mano.
- **No reemplaza al ingeniero (D2).** Los valores llenan el formulario marcados como «Sugerido por IA» y nada se guarda hasta que el ingeniero pulsa *Calcular y guardar*. El puntaje lo siguen dando las tablas del artículo, con los valores registrados.
- **Queda constancia (RNF-003).** Se guarda lo sugerido aparte de lo registrado, y el detalle y el informe muestran qué ángulos corrigió el ingeniero.
- **Límites:** necesita una foto de perfil del lado evaluado y avisa si parece de frente. Giros, inclinaciones laterales, abducción y apoyos no se ven de perfil y los registra el ingeniero.
- El cálculo está en `static/js/pose-angles.js`, separado de la interfaz (`pose-assist.js`).

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
- **Carga estática o repetida de menos de 2 kg:** el artículo no la define. El ingeniero debe elegir una de las categorías publicadas.
- **Brazo apoyado:** si el ajuste de -1 deja el puntaje en 0, se mantiene en 1, el mínimo de la tabla.
- **Casos de referencia:** RNF-003 pide casos aprobados; hoy solo hay casos calculados a mano y ejemplos publicados.
