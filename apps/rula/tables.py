"""Tablas oficiales de RULA.

Fuente: McAtamney L. y Corlett E. N. (1993). RULA: a survey method for the investigation
of work-related upper limb disorders. Applied Ergonomics, 24(2), 91-99.

Las tablas A y B se compararon celda por celda con el articulo (tablas 1 y 2). La tabla C
es la figura 6, cuya zona oscura es ilegible en el escaneo disponible: esas celdas se
tomaron de la hoja de trabajo RULA de Neese Consulting, basada en el mismo articulo, que
coincide con todas las celdas legibles.

No modificar estos valores sin una referencia: RNF-003 exige fidelidad al metodo.
"""

# TABLE_A[brazo - 1][antebrazo - 1][muneca - 1][giro - 1]
TABLE_A = (
    (
        ((1, 2), (2, 2), (2, 3), (3, 3)),
        ((2, 2), (2, 2), (3, 3), (3, 3)),
        ((2, 3), (3, 3), (3, 3), (4, 4)),
    ),
    (
        ((2, 3), (3, 3), (3, 4), (4, 4)),
        ((3, 3), (3, 3), (3, 4), (4, 4)),
        ((3, 4), (4, 4), (4, 4), (5, 5)),
    ),
    (
        ((3, 3), (4, 4), (4, 4), (5, 5)),
        ((3, 4), (4, 4), (4, 4), (5, 5)),
        ((4, 4), (4, 4), (4, 5), (5, 5)),
    ),
    (
        ((4, 4), (4, 4), (4, 5), (5, 5)),
        ((4, 4), (4, 4), (4, 5), (5, 5)),
        ((4, 4), (4, 5), (5, 5), (6, 6)),
    ),
    (
        ((5, 5), (5, 5), (5, 6), (6, 7)),
        ((5, 6), (6, 6), (6, 7), (7, 7)),
        ((6, 6), (6, 7), (7, 7), (7, 8)),
    ),
    (
        ((7, 7), (7, 7), (7, 8), (8, 9)),
        ((8, 8), (8, 8), (8, 9), (9, 9)),
        ((9, 9), (9, 9), (9, 9), (9, 9)),
    ),
)

# TABLE_B[cuello - 1][tronco - 1][piernas - 1]
TABLE_B = (
    ((1, 3), (2, 3), (3, 4), (5, 5), (6, 6), (7, 7)),
    ((2, 3), (2, 3), (4, 5), (5, 5), (6, 7), (7, 7)),
    ((3, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 7)),
    ((5, 5), (5, 6), (6, 7), (7, 7), (7, 7), (8, 8)),
    ((7, 7), (7, 7), (7, 8), (8, 8), (8, 8), (8, 8)),
    ((8, 8), (8, 8), (8, 8), (8, 9), (9, 9), (9, 9)),
)

# TABLE_C[puntaje C - 1][puntaje D - 1]. La ultima fila es 8+ y la ultima columna 7+.
TABLE_C = (
    (1, 2, 3, 3, 4, 5, 5),
    (2, 2, 3, 4, 4, 5, 5),
    (3, 3, 3, 4, 4, 5, 6),
    (3, 3, 3, 4, 5, 6, 6),
    (4, 4, 4, 5, 6, 7, 7),
    (4, 4, 5, 6, 6, 7, 7),
    (5, 5, 6, 6, 7, 7, 7),
    (5, 5, 6, 7, 7, 7, 7),
)
