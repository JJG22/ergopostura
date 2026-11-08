-- ErgoPostura: consultas SQL principales (MySQL 8.4)
--
-- Todas son de solo lectura (SELECT). Ejecútelas una por una.
-- Para ver resultados use la base local con datos de demostración; la base publicada
-- arranca vacía. El NIT 900123456 corresponde a Café Montaña S.A.S. en esos datos.
--
-- Las fechas con hora se guardan en UTC. Colombia está 5 horas atrás y no cambia de horario,
-- por eso las consultas restan 5 horas para mostrar la hora local.
--
-- Antes de ejecutar, deje seleccionada la base en la conexión de Workbench (Default Schema).

-- =====================================================================================
-- 1. Empresas registradas con su ubicación
-- Descripción: lista las empresas con su NIT, municipio, departamento y estado.
-- Tablas: companies_company, geography_municipality, geography_department.
-- =====================================================================================
SELECT
    c.name AS empresa,
    c.nit,
    m.name AS municipio,
    d.name AS departamento,
    IF(c.is_active, 'Activa', 'Inactiva') AS estado
FROM companies_company AS c
JOIN geography_municipality AS m ON m.id = c.municipality_id
JOIN geography_department AS d ON d.id = m.department_id
ORDER BY c.name;

-- =====================================================================================
-- 2. Búsqueda de empresas por nombre o NIT
-- Descripción: encuentra empresas cuyo nombre o NIT contengan el texto buscado.
-- Es la búsqueda del módulo de Empresas. Cambie 'caf' por el texto que desee.
-- Tablas: companies_company.
-- =====================================================================================
SELECT
    c.id,
    c.name AS empresa,
    c.nit
FROM companies_company AS c
WHERE c.name LIKE '%caf%'
   OR c.nit LIKE '%caf%'
ORDER BY c.name;

-- =====================================================================================
-- 3. Estructura de una empresa con número de trabajadores
-- Descripción: muestra sede, área y puesto de una empresa, y cuántos trabajadores activos
-- tiene cada puesto. El LEFT JOIN conserva los puestos sin trabajadores.
-- Tablas: companies_company, companies_site, companies_area, companies_position, companies_worker.
-- =====================================================================================
SELECT
    s.name AS sede,
    a.name AS area,
    p.name AS puesto,
    COUNT(w.id) AS trabajadores_activos
FROM companies_company AS c
JOIN companies_site AS s ON s.company_id = c.id
JOIN companies_area AS a ON a.site_id = s.id
JOIN companies_position AS p ON p.area_id = a.id
LEFT JOIN companies_worker AS w ON w.position_id = p.id AND w.is_active = 1
WHERE c.nit = '900123456'
GROUP BY s.name, a.name, p.name
ORDER BY s.name, a.name, p.name;

-- =====================================================================================
-- 4. Cuentas de usuario por rol
-- Descripción: cuenta los usuarios activos de cada rol del sistema.
-- Tablas: accounts_user.
-- =====================================================================================
SELECT
    CASE u.role
        WHEN 'admin' THEN 'Soporte técnico'
        WHEN 'ingeniero' THEN 'Ingeniero industrial'
        WHEN 'empresa' THEN 'Empresa cliente'
    END AS rol,
    COUNT(*) AS cuentas_activas
FROM accounts_user AS u
WHERE u.is_active = 1
GROUP BY u.role
ORDER BY cuentas_activas DESC;

-- =====================================================================================
-- 5. Contratos y estado de vigencia
-- Descripción: calcula el estado de cada contrato según la fecha actual y los días que
-- le quedan. Un contrato está por vencer cuando le quedan 30 días o menos.
-- Tablas: contracts_contract, companies_company.
-- =====================================================================================
SELECT
    c.name AS empresa,
    ct.code AS contrato,
    ct.start_date AS inicio,
    ct.end_date AS fin,
    CASE
        WHEN CURDATE() < ct.start_date THEN 'Por iniciar'
        WHEN CURDATE() > ct.end_date THEN 'Vencido'
        WHEN DATEDIFF(ct.end_date, CURDATE()) <= 30 THEN 'Por vencer'
        ELSE 'Vigente'
    END AS estado,
    GREATEST(DATEDIFF(ct.end_date, CURDATE()), 0) AS dias_restantes
FROM contracts_contract AS ct
JOIN companies_company AS c ON c.id = ct.company_id
ORDER BY ct.end_date;

-- =====================================================================================
-- 6. Próximas visitas programadas con su nivel
-- Descripción: lista las visitas futuras y las clasifica en Hoy, Cercana (3 días o menos)
-- o Programada, igual que el calendario del ingeniero.
-- Tablas: visits_visit, companies_site, companies_company.
-- =====================================================================================
SELECT
    c.name AS empresa,
    s.name AS sede,
    CAST(DATE_SUB(v.scheduled_at, INTERVAL 5 HOUR) AS DATETIME) AS fecha_hora_colombia,
    v.duration_minutes AS minutos,
    CASE
        WHEN DATE(DATE_SUB(v.scheduled_at, INTERVAL 5 HOUR)) = DATE(DATE_SUB(UTC_TIMESTAMP(), INTERVAL 5 HOUR)) THEN 'Hoy'
        WHEN v.scheduled_at <= DATE_ADD(UTC_TIMESTAMP(), INTERVAL 3 DAY) THEN 'Cercana'
        ELSE 'Programada'
    END AS nivel
FROM visits_visit AS v
JOIN companies_site AS s ON s.id = v.site_id
JOIN companies_company AS c ON c.id = s.company_id
WHERE v.status = 'programada'
  AND v.scheduled_at > UTC_TIMESTAMP()
ORDER BY v.scheduled_at;

-- =====================================================================================
-- 7. Visitas por cerrar
-- Descripción: visitas programadas cuya hora de finalización ya pasó. El ingeniero debe
-- registrar si se realizaron.
-- Tablas: visits_visit, companies_site, companies_company.
-- =====================================================================================
SELECT
    c.name AS empresa,
    s.name AS sede,
    CAST(DATE_SUB(v.scheduled_at, INTERVAL 5 HOUR) AS DATETIME) AS fecha_hora_colombia,
    v.contact_name AS recibe
FROM visits_visit AS v
JOIN companies_site AS s ON s.id = v.site_id
JOIN companies_company AS c ON c.id = s.company_id
WHERE v.status = 'programada'
  AND DATE_ADD(v.scheduled_at, INTERVAL v.duration_minutes MINUTE) <= UTC_TIMESTAMP()
ORDER BY v.scheduled_at;

-- =====================================================================================
-- 8. Número de visitas por empresa y estado
-- Descripción: resume cuántas visitas programadas, realizadas y canceladas tiene cada empresa.
-- Tablas: visits_visit, companies_site, companies_company.
-- =====================================================================================
SELECT
    c.name AS empresa,
    SUM(v.status = 'programada') AS programadas,
    SUM(v.status = 'realizada') AS realizadas,
    SUM(v.status = 'cancelada') AS canceladas,
    COUNT(*) AS total
FROM visits_visit AS v
JOIN companies_site AS s ON s.id = v.site_id
JOIN companies_company AS c ON c.id = s.company_id
GROUP BY c.name
ORDER BY total DESC, c.name;

-- =====================================================================================
-- 9. Evaluaciones terminadas con su mayor nivel de riesgo
-- Descripción: muestra cada evaluación terminada con su postura de mayor riesgo y el color
-- del semáforo. Nunca se promedian puntajes: una evaluación vale lo que su peor postura.
-- Tablas: evaluations_evaluation, evaluations_posture, evaluations_rulaassessment,
-- companies_position, companies_area, companies_site, companies_company.
-- =====================================================================================
SELECT
    CONCAT('EV-', LPAD(e.id, 4, '0')) AS evaluacion,
    c.name AS empresa,
    a.name AS area,
    p.name AS puesto,
    e.evaluated_on AS fecha,
    MAX(r.grand_score) AS puntaje_rula,
    MAX(r.action_level) AS nivel_accion,
    CASE
        WHEN MAX(r.action_level) = 1 THEN 'Verde'
        WHEN MAX(r.action_level) IN (2, 3) THEN 'Amarillo'
        ELSE 'Rojo'
    END AS semaforo
FROM evaluations_evaluation AS e
JOIN evaluations_posture AS po ON po.evaluation_id = e.id
JOIN evaluations_rulaassessment AS r ON r.posture_id = po.id
JOIN companies_position AS p ON p.id = e.position_id
JOIN companies_area AS a ON a.id = p.area_id
JOIN companies_site AS s ON s.id = a.site_id
JOIN companies_company AS c ON c.id = s.company_id
WHERE e.status = 'terminada'
GROUP BY e.id, c.name, a.name, p.name, e.evaluated_on
ORDER BY nivel_accion DESC, e.evaluated_on DESC;

-- =====================================================================================
-- 10. Indicador de riesgo por área
-- Descripción: cuenta los puestos de cada área por color de riesgo. Por cada puesto toma
-- solo su evaluación terminada más reciente, con la función de ventana ROW_NUMBER.
-- Tablas: evaluations_evaluation, evaluations_posture, evaluations_rulaassessment,
-- companies_position, companies_area, companies_site, companies_company.
-- =====================================================================================
WITH riesgo_por_evaluacion AS (
    SELECT
        e.id,
        e.position_id,
        e.evaluated_on,
        MAX(r.action_level) AS nivel
    FROM evaluations_evaluation AS e
    JOIN evaluations_posture AS po ON po.evaluation_id = e.id
    JOIN evaluations_rulaassessment AS r ON r.posture_id = po.id
    WHERE e.status = 'terminada'
    GROUP BY e.id, e.position_id, e.evaluated_on
),
ultima_por_puesto AS (
    SELECT
        position_id,
        nivel,
        ROW_NUMBER() OVER (PARTITION BY position_id ORDER BY evaluated_on DESC, id DESC) AS orden
    FROM riesgo_por_evaluacion
)
SELECT
    c.name AS empresa,
    s.name AS sede,
    a.name AS area,
    SUM(u.nivel = 1) AS puestos_verde,
    SUM(u.nivel IN (2, 3)) AS puestos_amarillo,
    SUM(u.nivel = 4) AS puestos_rojo
FROM ultima_por_puesto AS u
JOIN companies_position AS p ON p.id = u.position_id
JOIN companies_area AS a ON a.id = p.area_id
JOIN companies_site AS s ON s.id = a.site_id
JOIN companies_company AS c ON c.id = s.company_id
WHERE u.orden = 1
GROUP BY c.name, s.name, a.name
ORDER BY puestos_rojo DESC, puestos_amarillo DESC, c.name, a.name;

-- =====================================================================================
-- 11. Recomendaciones pendientes por atender
-- Descripción: lista las recomendaciones de evaluaciones terminadas que la empresa no ha
-- atendido, primero las de mayor riesgo.
-- Tablas: evaluations_recommendation, evaluations_posture, evaluations_rulaassessment,
-- evaluations_evaluation, companies_position, companies_area, companies_site, companies_company.
-- =====================================================================================
SELECT
    c.name AS empresa,
    p.name AS puesto,
    po.name AS postura,
    r.grand_score AS puntaje_rula,
    rec.text AS recomendacion
FROM evaluations_recommendation AS rec
JOIN evaluations_posture AS po ON po.id = rec.posture_id
JOIN evaluations_rulaassessment AS r ON r.posture_id = po.id
JOIN evaluations_evaluation AS e ON e.id = po.evaluation_id
JOIN companies_position AS p ON p.id = e.position_id
JOIN companies_area AS a ON a.id = p.area_id
JOIN companies_site AS s ON s.id = a.site_id
JOIN companies_company AS c ON c.id = s.company_id
WHERE e.status = 'terminada'
  AND rec.attended_at IS NULL
ORDER BY r.grand_score DESC, rec.id;

-- =====================================================================================
-- 12. Visitas realizadas sin evaluación
-- Descripción: encuentra visitas ya realizadas que todavía no tienen evaluación, usando
-- LEFT JOIN e IS NULL.
-- Tablas: visits_visit, evaluations_evaluation, companies_site, companies_company.
-- =====================================================================================
SELECT
    c.name AS empresa,
    s.name AS sede,
    CAST(DATE_SUB(v.scheduled_at, INTERVAL 5 HOUR) AS DATETIME) AS fecha_hora_colombia
FROM visits_visit AS v
JOIN companies_site AS s ON s.id = v.site_id
JOIN companies_company AS c ON c.id = s.company_id
LEFT JOIN evaluations_evaluation AS e ON e.visit_id = v.id
WHERE v.status = 'realizada'
  AND e.id IS NULL
ORDER BY v.scheduled_at DESC;

-- =====================================================================================
-- 13. Verificación: evaluaciones sin una visita realizada en su sede
-- Descripción: comprueba la regla principal del sistema. Debe devolver cero filas: toda
-- evaluación parte de una visita realizada en la sede del puesto evaluado.
-- Tablas: evaluations_evaluation, visits_visit, companies_position, companies_area.
-- =====================================================================================
SELECT
    e.id AS evaluacion,
    v.status AS estado_visita,
    v.site_id AS sede_visita,
    a.site_id AS sede_puesto
FROM evaluations_evaluation AS e
JOIN visits_visit AS v ON v.id = e.visit_id
JOIN companies_position AS p ON p.id = e.position_id
JOIN companies_area AS a ON a.id = p.area_id
WHERE v.status <> 'realizada'
   OR v.site_id <> a.site_id;
