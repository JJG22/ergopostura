-- ErgoPostura: guion de demostración en SQL para la exposición (MySQL 8.4)
--
-- Úselo en la base LOCAL (Docker, puerto 3307) con datos de demostración. Ejecute cada
-- bloque por separado: en Workbench, ponga el cursor en la consulta y pulse Ctrl+Enter.
--
-- Las partes 1 a 4 solo leen. La parte 5 intenta guardar datos inválidos dentro de una
-- transacción que se deshace con ROLLBACK: cada intento DEBE fallar, y ese error es lo que
-- se quiere mostrar (la base protege sus reglas aunque alguien se salte la aplicación).

-- =====================================================================================
-- 1. La estructura: tablas, columnas y restricciones
-- =====================================================================================

-- 1.1 Las 26 tablas de la base.
SHOW TABLES;

-- 1.2 Las columnas de una tabla, con su tipo y si aceptan NULL.
DESCRIBE companies_company;

-- 1.3 La sentencia que crea la tabla, con llaves, índices únicos y restricciones CHECK.
SHOW CREATE TABLE companies_company;

-- 1.4 Todas las restricciones CHECK del sistema: reglas que MySQL hace cumplir por sí mismo.
SELECT tc.TABLE_NAME AS tabla, cc.CONSTRAINT_NAME AS restriccion, cc.CHECK_CLAUSE AS condicion
FROM information_schema.CHECK_CONSTRAINTS AS cc
JOIN information_schema.TABLE_CONSTRAINTS AS tc
  ON tc.CONSTRAINT_SCHEMA = cc.CONSTRAINT_SCHEMA AND tc.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
WHERE cc.CONSTRAINT_SCHEMA = DATABASE()
ORDER BY tc.TABLE_NAME, cc.CONSTRAINT_NAME;

-- 1.5 Las llaves foráneas y qué pasa al borrar el registro padre.
-- RESTRICT/NO ACTION: no se puede borrar un padre con hijos (no se pierde historia).
SELECT TABLE_NAME AS tabla, CONSTRAINT_NAME AS llave, REFERENCED_TABLE_NAME AS referencia, DELETE_RULE AS al_borrar
FROM information_schema.REFERENTIAL_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = DATABASE()
  AND TABLE_NAME NOT LIKE 'auth\_%' AND TABLE_NAME NOT LIKE 'django\_%'
ORDER BY TABLE_NAME;

-- =====================================================================================
-- 2. Las migraciones: cómo cambia la estructura sin tocarla a mano
-- =====================================================================================

-- 2.1 Las últimas migraciones aplicadas. Django las registra en esta tabla.
SELECT app, name AS migracion, applied - INTERVAL 5 HOUR AS aplicada_hora_colombia
FROM django_migrations
ORDER BY applied DESC
LIMIT 10;

-- =====================================================================================
-- 3. Los datos
-- =====================================================================================

-- 3.1 Empresas: persona jurídica con NIT o natural con cédula (nunca las dos).
SELECT name AS empresa,
       IF(person_type = 'natural', 'Persona natural', 'Persona jurídica') AS tipo_persona,
       nit, cedula, IF(is_active, 'Activa', 'Inactiva') AS estado
FROM companies_company
ORDER BY name;

-- 3.2 Las fotografías se guardan en la base como BLOB, ya optimizadas.
SELECT ph.id, p.name AS postura, ph.content_type AS tipo, ph.width AS ancho, ph.height AS alto,
       ROUND(LENGTH(ph.data) / 1024) AS tamano_kb
FROM evaluations_posturephoto AS ph
JOIN evaluations_posture AS p ON p.id = ph.posture_id
ORDER BY ph.id
LIMIT 10;

-- 3.3 Resultado RULA de cada postura: puntaje de 1 a 7 y nivel de acción de 1 a 4.
SELECT e.id AS evaluacion, p.name AS postura, r.grand_score AS puntaje, r.action_level AS nivel,
       CASE r.action_level WHEN 1 THEN 'Verde' WHEN 4 THEN 'Rojo' ELSE 'Amarillo' END AS semaforo
FROM evaluations_rulaassessment AS r
JOIN evaluations_posture AS p ON p.id = r.posture_id
JOIN evaluations_evaluation AS e ON e.id = p.evaluation_id
ORDER BY r.grand_score DESC, e.id
LIMIT 10;

-- 3.4 Recomendaciones: cuántas escribió el ingeniero y cuántas tomó de la IA.
SELECT IF(from_ai, 'Con apoyo de IA', 'Del ingeniero') AS origen,
       COUNT(*) AS total,
       SUM(attended_at IS NOT NULL) AS atendidas
FROM evaluations_recommendation
GROUP BY from_ai;

-- =====================================================================================
-- 4. Seguridad vista desde la base
-- =====================================================================================

-- 4.1 Las contraseñas no se guardan: solo su hash (algoritmo$iteraciones$sal$hash).
SELECT email, role AS rol, LEFT(password, 30) AS inicio_del_hash, must_change_password AS debe_cambiarla
FROM accounts_user
ORDER BY role, email;

-- 4.2 Lo que ve una empresa: solo sus evaluaciones terminadas. La aplicación aplica este mismo
-- filtro en cada consulta; cambie el 1 por el id de otra empresa para comparar.
SELECT e.id, pos.name AS puesto, e.status AS estado
FROM evaluations_evaluation AS e
JOIN companies_position AS pos ON pos.id = e.position_id
JOIN companies_area AS a ON a.id = pos.area_id
JOIN companies_site AS s ON s.id = a.site_id
WHERE s.company_id = 1 AND e.status = 'terminada';

-- =====================================================================================
-- 5. Las reglas en acción: cada intento DEBE fallar
-- =====================================================================================

START TRANSACTION;

-- 5.1 NIT con formato inválido -> Error 3819: viola company_nit_format.
INSERT INTO companies_company (created_at, updated_at, person_type, name, nit, cedula, is_active, municipality_id)
SELECT NOW(), NOW(), 'juridica', 'Prueba NIT inválido', '123', NULL, 1, id FROM geography_municipality LIMIT 1;

-- 5.2 Persona natural con NIT en vez de cédula -> Error 3819: viola company_document_matches_person_type.
INSERT INTO companies_company (created_at, updated_at, person_type, name, nit, cedula, is_active, municipality_id)
SELECT NOW(), NOW(), 'natural', 'Prueba natural con NIT', '900999999', NULL, 1, id FROM geography_municipality LIMIT 1;

-- 5.3 NIT repetido -> Error 1062: entrada duplicada (índice único).
INSERT INTO companies_company (created_at, updated_at, person_type, name, nit, cedula, is_active, municipality_id)
SELECT NOW(), NOW(), 'juridica', 'Prueba NIT repetido', c.nit, NULL, 1, c.municipality_id
FROM companies_company AS c WHERE c.nit IS NOT NULL LIMIT 1;

-- 5.4 Puntaje RULA fuera de 1 a 7 -> Error 3819: viola assessment_grand_score_range.
UPDATE evaluations_rulaassessment SET grand_score = 9 ORDER BY id LIMIT 1;

-- 5.5 Borrar una empresa que tiene sedes, contratos o cuentas -> Error 1451: una llave foránea lo impide.
DELETE FROM companies_company WHERE id = (SELECT company_id FROM companies_site ORDER BY id LIMIT 1);

ROLLBACK;
