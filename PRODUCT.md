# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Empresas que aún no son clientes** (audiencia principal de la portada): responsables de seguridad y salud en el trabajo, talento humano o gerencia de empresas colombianas que evalúan si contratar un servicio de ergonomía para sus puestos. Llegan a decidir si el servicio es serio y si les sirve.
- **Ingeniero industrial** (usuario principal de la aplicación): presta el servicio. Registra empresas, sedes, áreas, puestos y trabajadores; gestiona contratos; confirma visitas; evalúa posturas con RULA en campo y en oficina; redacta recomendaciones; revisa indicadores.
- **Empresa cliente**: agenda visitas en el calendario, consulta resultados, informes e indicadores de sus áreas, y sigue las recomendaciones pendientes.
- **Soporte técnico**: crea y mantiene las cuentas. No ve evaluaciones, visitas ni contratos.

## Product Purpose

ErgoPostura organiza un servicio de evaluación ergonómica de puestos de trabajo de principio a fin: contrato con cada empresa, visitas agendadas por la empresa, evaluación de cada postura con el método RULA (con fotografías como evidencia), recomendaciones, informe imprimible y seguimiento. El éxito es que una empresa entienda el riesgo postural de cada puesto y sepa qué hacer y qué tan pronto.

## Positioning

Un solo método, aplicado igual en cada puesto: RULA convierte la observación de una postura en un puntaje de 1 a 7 y un nivel de acción. El cliente no recibe una opinión, recibe un resultado trazable (ángulos medidos, fotografía, puntaje, recomendación) y un lugar donde seguirlo.

## Operating Context

- Visitas presenciales a sedes de las empresas; el ingeniero fotografía posturas y mide ángulos (con sugerencia de ángulos por IA sobre la foto, siempre revisada por el ingeniero).
- La empresa agenda la visita en el calendario; sin contrato vigente no puede agendar. Sin visita realizada no hay evaluación.
- Informe de evaluación imprimible y en PDF.
- Contratos en PDF con lectura asistida por IA (opcional según configuración del servidor).
- Español de Colombia, zona horaria de Bogotá. Departamentos y municipios de Colombia.

## Capabilities and Constraints

- Cliente React (Vite, TypeScript, Tailwind) en `/app/`, servido por Django como API REST en `/api/v1/`; panel técnico en `/admin/`.
- Base de datos MySQL (requisito del curso, con sentencias SQL documentadas en `docs/sql/`). Despliegue en Render con cada push a `main`.
- Permisos por rol aplicados en el servidor; la interfaz muestra a cada rol solo lo suyo.
- La portada de ingreso (`/app/ingresar`) es la única página pública; el resto exige sesión.
- Proyecto académico (Proyecto Nuclear I); la documentación de `docs/` debe describir la versión actual.

## Brand Commitments

- Nombre: ErgoPostura. Se presenta solo la marca; no se muestra a ninguna persona.
- El método es RULA y se nombra como tal.

## Evidence on Hand

- No hay fotografías publicables de puestos reales, clientes, casos, testimonios ni cifras de resultados. No se deben inventar.
- La evidencia disponible es el propio producto: la escala RULA, el flujo del servicio y las pantallas de la aplicación (con datos de demostración ficticios de `seed_demo`, que no deben presentarse como clientes reales).

## Product Principles

1. Un resultado vale por su trazabilidad: puntaje, ángulos, foto y recomendación siempre juntos.
2. Cada rol ve lo que le corresponde y nada más.
3. El riesgo se comunica con número y texto, nunca solo con color.
4. Lo que se promete en la portada es lo que la aplicación hace hoy.

## Accessibility & Inclusion

- El color del riesgo siempre va acompañado del nivel y su texto (RNF-004).
- Uso en escritorio y en teléfono (el ingeniero trabaja en campo).
