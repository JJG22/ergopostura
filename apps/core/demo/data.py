"""Catalogo de datos ficticios. Todo nombre de empresa, NIT y persona es inventado.

Los ajustes de postura se eligieron para que el calculo real de RULA produzca los cuatro
niveles de accion: asi los indicadores, el semaforo y las tareas tienen que mostrar.
"""
from apps.accounts.models import Role
from apps.rula.scoring import Load

DEMO_PASSWORD = "ErgoDemo2026!"

# correo, nombre, apellido, rol, NIT de la empresa (solo para el rol Empresa)
USERS = (
    ("admin@ergopostura.test", "Ana", "Soporte", Role.ADMIN, None),
    ("ingeniero@ergopostura.test", "Andrés", "Ríos", Role.ENGINEER, None),
    ("empresa@ergopostura.test", "Marta", "Salazar", Role.COMPANY, "900123456"),
    ("empresa2@ergopostura.test", "Diana", "Restrepo", Role.COMPANY, "890900123"),
)

# Nombres inventados para los trabajadores de los puestos.
FIRST_NAMES = (
    "Carolina", "Jhon Fredy", "Luz Marina", "Wilson", "Paola Andrea", "Édgar", "Yenny", "Mauricio",
    "Natalia", "Fabio", "Lorena", "Germán", "Sandra Milena", "Julián", "Ángela", "Óscar",
)
LAST_NAMES = (
    "Gómez Arango", "Henao Ríos", "Muñoz Cárdenas", "Ospina Vélez", "Castaño Giraldo", "Zapata Mejía",
    "Londoño Duque", "Restrepo Toro", "Valencia Cruz", "Agudelo Marín", "Quintero Patiño", "Rendón Salazar",
)

# Servicio contratado, igual para todas las empresas de la demostracion.
CONTRACT_SERVICE = (
    "Evaluación ergonómica de puestos de trabajo con el método RULA, informe por puesto con "
    "nivel de riesgo y recomendaciones, y seguimiento de las acciones de mejora."
)

# NIT, razon social, municipio, departamento, activa, contacto, sedes
# sede: nombre, municipio, departamento, direccion, areas
# area: nombre, puestos; puesto: nombre, descripcion
COMPANIES = (
    (
        "900123456", "Café Montaña S.A.S.", "Armenia", "Quindío", True, "Marta Salazar",
        (
            ("Planta Armenia", "Armenia", "Quindío", "Km 3 vía al Edén", (
                ("Empaque", (
                    ("Operario de empaque", "Empaca bolsas de café de 500 g y 2,5 kg en cajas."),
                    ("Operario de sellado", "Alimenta la selladora y revisa el cierre de cada bolsa."),
                )),
                ("Administración", (
                    ("Digitador", "Registra pedidos y facturas en el computador."),
                )),
            )),
            ("Bodega Calarcá", "Calarcá", "Quindío", "Calle 40 # 25-10", (
                ("Almacenamiento", (
                    ("Auxiliar de bodega", "Recibe, ubica y despacha bultos de café en estibas."),
                )),
            )),
        ),
    ),
    (
        "901234567", "Muebles del Eje Ltda.", "Pereira", "Risaralda", True, "Héctor Patiño",
        (
            ("Taller Dosquebradas", "Dosquebradas", "Risaralda", "Zona industrial La Badea", (
                ("Corte", (("Operario de sierra", "Corta tableros de madera en la sierra escuadradora."),)),
                ("Ensamble", (("Ensamblador", "Arma estructuras de muebles con atornillador neumático."),)),
                ("Pintura", (("Pintor", "Lija y aplica laca con pistola en cabina."),)),
            )),
        ),
    ),
    (
        "890900123", "Textiles Antioquia S.A.", "Medellín", "Antioquia", True, "Diana Restrepo",
        (
            ("Planta Itagüí", "Itagüí", "Antioquia", "Carrera 50 # 12 Sur-80", (
                ("Confección", (
                    ("Operaria de máquina plana", "Cose prendas en máquina plana durante turnos de 8 horas."),
                    ("Revisora de calidad", "Inspecciona prendas terminadas sobre una mesa de pie."),
                )),
                ("Corte", (("Cortador", "Extiende y corta tela con cortadora vertical."),)),
            )),
            ("Oficina Medellín", "Medellín", "Antioquia", "Calle 10 # 43-20", (
                ("Atención al cliente", (("Asesor comercial", "Atiende clientes en mostrador y por teléfono."),)),
            )),
        ),
    ),
    (
        "900555123", "Logística del Pacífico S.A.S.", "Cali", "Valle del Cauca", True, "Óscar Valencia",
        (
            ("CEDI Yumbo", "Yumbo", "Valle del Cauca", "Autopista Cali-Yumbo Km 6", (
                ("Recepción", (("Auxiliar de recepción", "Descarga cajas de los camiones a las estibas."),)),
                ("Despacho", (
                    ("Alistador", "Toma productos de estanterías y arma pedidos."),
                    ("Montacarguista", "Opera el montacargas para ubicar estibas en altura."),
                )),
            )),
        ),
    ),
    (
        "800234567", "Clínica Santa Lucía", "Bogotá D.C.", "Bogotá", True, "Patricia Rojas",
        (
            ("Sede Norte", "Bogotá D.C.", "Bogotá", "Calle 134 # 7-30", (
                ("Hospitalización", (("Auxiliar de enfermería", "Moviliza pacientes y cambia ropa de cama."),)),
                ("Facturación", (("Facturador", "Revisa y factura servicios en el computador."),)),
            )),
        ),
    ),
    (
        # Empresa inactiva: no se ofrece para nuevas visitas ni para nueva estructura.
        "901777888", "Agroindustrial del Caribe S.A.S.", "Barranquilla", "Atlántico", False, "Luis Fontalvo",
        (
            ("Planta Soledad", "Soledad", "Atlántico", "Vía 40 # 85-12", (
                ("Producción", (("Operario de línea", "Clasifica fruta en la banda transportadora."),)),
            )),
        ),
    ),
)

# Ajustes de postura. clave: (nombre, duracion, unidad, datos RULA, recomendaciones)
POSTURES = {
    "digitar": (
        "Digitación en escritorio", 4, "horas",
        dict(upper_arm_angle=15, lower_arm_angle=80, wrist_angle=5, neck_angle=5, trunk_angle=0,
             trunk_supported_seated=True, arm_supported=True),
        (),
    ),
    "mostrador": (
        "Atención de pie en mostrador", 2, "horas",
        dict(upper_arm_angle=10, lower_arm_angle=90, wrist_angle=0, neck_angle=10, trunk_angle=5),
        (),
    ),
    "coser": (
        "Costura en máquina plana", 50, "minutos",
        dict(upper_arm_angle=30, lower_arm_angle=70, wrist_angle=15, wrist_twist_near_end=True, neck_angle=30,
             trunk_angle=15, trunk_supported_seated=True, arm_static_or_repeated=True),
        ("Ajustar la altura de la silla para que los codos queden a la altura de la mesa.",
         "Hacer pausas activas de cuello y muñecas cada hora."),
    ),
    "empacar": (
        "Empaque en mesa baja", 30, "minutos",
        dict(upper_arm_angle=50, lower_arm_angle=110, wrist_angle=20, neck_angle=25, trunk_angle=25,
             arm_static_or_repeated=True, body_static_or_repeated=True),
        ("Elevar la mesa de empaque unos 15 cm para reducir la flexión del tronco.",
         "Rotar al trabajador entre empaque y sellado cada dos horas."),
    ),
    "levantar": (
        "Levantamiento de cajas desde el piso", 15, "minutos",
        dict(upper_arm_angle=95, shoulder_raised=True, lower_arm_angle=120, wrist_angle=20,
             wrist_bent_from_midline=True, neck_angle=25, neck_twisted=True, trunk_angle=65, trunk_twisted=True,
             legs_supported_and_balanced=False, arm_load=Load.HEAVY_INTERMITTENT.name,
             body_load=Load.HEAVY_INTERMITTENT.name),
        ("Ubicar las cajas sobre estibas elevadas para no tomarlas del piso.",
         "Capacitar en levantamiento seguro y usar carretilla para cargas de más de 10 kg.",
         "Evitar giros del tronco reorganizando la zona de descarga."),
    ),
    "estanteria": (
        "Alcance a estantería alta", 10, "minutos",
        dict(upper_arm_angle=100, shoulder_raised=True, upper_arm_abducted=True, lower_arm_angle=50,
             wrist_angle=10, neck_angle=-10, trunk_angle=10, arm_load=Load.MEDIUM_INTERMITTENT.name,
             body_load=Load.MEDIUM_INTERMITTENT.name),
        ("Ubicar los productos de mayor rotación entre la altura de la cadera y los hombros.",
         "Proveer una escalera de plataforma para los niveles superiores."),
    ),
    "paciente": (
        "Movilización de paciente en cama", 5, "minutos",
        dict(upper_arm_angle=60, lower_arm_angle=100, wrist_angle=10, neck_angle=30, trunk_angle=45,
             trunk_twisted=True, arm_load=Load.SHOCK_OR_RAPID_FORCE.name, body_load=Load.HEAVY_INTERMITTENT.name),
        ("Usar sábana deslizante y hacer la movilización entre dos personas.",
         "Ajustar la altura de la cama antes de mover al paciente."),
    ),
}

# Puesto -> posturas que se evaluan en el
POSITION_POSTURES = {
    "Operario de empaque": ("empacar", "levantar"),
    "Operario de sellado": ("empacar",),
    "Digitador": ("digitar",),
    "Auxiliar de bodega": ("levantar", "estanteria"),
    "Operario de sierra": ("empacar",),
    "Ensamblador": ("coser",),
    "Pintor": ("estanteria",),
    "Operaria de máquina plana": ("coser",),
    "Revisora de calidad": ("mostrador",),
    "Cortador": ("empacar",),
    "Asesor comercial": ("mostrador", "digitar"),
    "Auxiliar de recepción": ("levantar",),
    "Alistador": ("estanteria", "levantar"),
    "Montacarguista": ("digitar",),
    "Auxiliar de enfermería": ("paciente",),
    "Facturador": ("digitar",),
    "Operario de línea": ("mostrador",),
}

ACTIVITIES = {
    "empacar": "Toma producto de la banda, lo empaca en cajas y las arruma junto a la mesa.",
    "levantar": "Levanta cajas de 12 a 18 kg desde el piso y las ubica en estibas.",
    "digitar": "Trabaja en computador con teclado y mouse durante la mayor parte del turno.",
    "estanteria": "Toma y ubica productos en los niveles superiores de la estantería.",
    "coser": "Cose piezas de forma continua, con ciclos cortos y repetitivos.",
    "mostrador": "Atiende a las personas de pie, revisa documentos y entrega productos.",
    "paciente": "Cambia de posición a pacientes encamados y arregla la ropa de cama.",
}
