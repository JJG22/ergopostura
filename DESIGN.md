---
name: ErgoPostura
description: Evaluación ergonómica RULA para empresas, con la forma de un cartel de prevención laboral.
colors:
  paper-white: "#ffffff"
  poster-ink: "#121418"
  signal-blue: "#0b4a8f"
  signal-blue-deep: "#093c74"
  signal-blue-pale: "#a9c6e6"
  field-grey: "#e9eaec"
  rule-grey: "#d4d6da"
  muted-ink: "#616366"
  body-ink: "#36393e"
  risk-green: "#1e7a46"
  risk-amber: "#c99700"
  risk-amber-text: "#8a6700"
  risk-orange: "#c2531a"
  risk-red: "#b3121f"
typography:
  display:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(36px, 6.2vw, 92px)"
    fontWeight: 800
    lineHeight: 0.96
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "4.5rem"
    fontWeight: 800
    lineHeight: 0.98
    letterSpacing: "-0.03em"
    fontVariation: "'wdth' 104"
  title:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "-0.03em"
    fontVariation: "'wdth' 104"
  numeral:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "3.75rem"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "-0.03em"
    fontFeature: "'tnum'"
    fontVariation: "'wdth' 104"
  body:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  body-sm:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.43
  label:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 500
    lineHeight: 1.3
  button:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: 1
rounded:
  none: "0px"
  print: "2px"
  dot: "9999px"
spacing:
  s-1: "4px"
  s-2: "8px"
  s-3: "12px"
  s-4: "16px"
  s-5: "24px"
  s-6: "32px"
  s-7: "48px"
  s-8: "64px"
  s-9: "96px"
  s-10: "128px"
components:
  button-primary:
    backgroundColor: "{colors.signal-blue}"
    textColor: "{colors.paper-white}"
    typography: "{typography.button}"
    rounded: "{rounded.print}"
    height: "44px"
    padding: "0 20px"
  button-primary-hover:
    backgroundColor: "{colors.signal-blue-deep}"
    textColor: "{colors.paper-white}"
  button-secondary:
    backgroundColor: "{colors.paper-white}"
    textColor: "{colors.poster-ink}"
    typography: "{typography.button}"
    rounded: "{rounded.print}"
    height: "44px"
    padding: "0 20px"
  button-secondary-hover:
    backgroundColor: "{colors.poster-ink}"
    textColor: "{colors.paper-white}"
  button-inverse:
    backgroundColor: "{colors.paper-white}"
    textColor: "{colors.signal-blue-deep}"
    typography: "{typography.button}"
    rounded: "{rounded.print}"
    height: "44px"
    padding: "0 20px"
  button-inverse-hover:
    backgroundColor: "{colors.field-grey}"
    textColor: "{colors.signal-blue-deep}"
  button-inverse-outline:
    backgroundColor: "{colors.signal-blue}"
    textColor: "{colors.paper-white}"
    typography: "{typography.button}"
    rounded: "{rounded.print}"
    height: "44px"
    padding: "0 20px"
  button-ghost:
    textColor: "{colors.signal-blue}"
    typography: "{typography.button}"
    height: "36px"
    padding: "0 4px"
  input-text:
    backgroundColor: "{colors.paper-white}"
    textColor: "{colors.poster-ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.print}"
    height: "44px"
    padding: "0 14px"
  card-surface:
    backgroundColor: "{colors.paper-white}"
    rounded: "{rounded.print}"
    padding: "24px"
  header-band:
    backgroundColor: "{colors.signal-blue}"
    textColor: "{colors.paper-white}"
    height: "64px"
  poster-band:
    backgroundColor: "{colors.signal-blue}"
    textColor: "{colors.paper-white}"
    padding: "64px 32px"
  risk-chip-green:
    backgroundColor: "{colors.risk-green}"
    textColor: "{colors.paper-white}"
    height: "20px"
    padding: "0 6px"
  risk-chip-amber:
    backgroundColor: "{colors.risk-amber}"
    textColor: "{colors.poster-ink}"
    height: "20px"
    padding: "0 6px"
  risk-chip-red:
    backgroundColor: "{colors.risk-red}"
    textColor: "{colors.paper-white}"
    height: "20px"
    padding: "0 6px"
---

# Design System: ErgoPostura

## Overview

**Creative North Star: "El cartel de prevención laboral"**

Cada pantalla se lee como un cartel de seguridad industrial del estilo tipográfico internacional: un campo de color plano que ocupa una región entera, una frase grande en grotesca pesada y una foto de trabajo real impresa sobre el azul. El sistema es papel blanco, tinta de imprenta y un solo azul de señal obligatoria; nada brilla, nada flota, nada se difumina. La autoridad viene de la escala y del contraste, no de efectos.

Hay dos densidades del mismo mundo. La portada pública (modo persuadir) trabaja a tamaño de cartel: campos a sangre, una sección por pantalla, titulares de hasta 92 px. La aplicación (modo operar) conserva el mismo vocabulario a tamaño de formulario: franja azul arriba, una banda de cartel azul al inicio del panel, tablas y fichas blancas bajo reglas de tinta. El panel técnico de Django hereda la paleta y la tipografía, en una versión más tenue.

La escala RULA de 1 a 7 es la firma del sistema: una tira impresa de siete casillas en cuatro tintas de riesgo, cada una con su trama, que reaparece en la portada (regla vertical del primer pliego, regla grande de la escala, tercer paso del proceso) y en la aplicación (escala del puntaje en cada postura). La dirección proviene de la semilla seed:ab5ed8ade45fd4eb (forma: cartel de seguridad laboral tipo Suva).

**Key Characteristics:**
- Campos planos de azul de señal a sangre; sin degradados, vidrio ni sombras difusas.
- Una sola familia, Archivo: 800 con eje de ancho para títulos y cifras, 400/500 para texto.
- Esquinas rectas: 0 en la portada, 2 px en la aplicación y el panel técnico.
- Reglas de tinta de 2 a 4 px como estructura, en lugar de cajas.
- Fotos en blanco y negro sobreimpresas en azul por multiplicación.
- El riesgo nunca va solo con color: tinta, trama, número y texto juntos.

## Colors

Tres tintas de imprenta y un gris de campo; el verde, ámbar, naranja y rojo existen solo para el riesgo RULA.

### Primary
- **Azul de señal obligatoria** (signal-blue): el único color de acción y de campo. Llena la franja superior de la aplicación, la banda de cartel del panel, la mitad izquierda del primer pliego de la portada, el fondo de cada fotomontaje, el botón principal, los enlaces y el anillo de foco. Su variante profunda (signal-blue-deep) es solo el estado hover y el texto de los botones inversos.
- **Azul pálido de señal** (signal-blue-pale): el brazo móvil del logo cuando va sobre azul (favicon, logo claro).

### Neutral
- **Papel blanco** (paper-white): fondo de página, fichas, menús y el botón inverso sobre el campo azul.
- **Tinta de cartel** (poster-ink): texto, reglas gruesas, borde del botón secundario, numerales de paso.
- **Gris de campo** (field-grey): fondo de las secciones alternas de la portada y relleno de hover de filas.
- **Gris de regla** (rule-grey): borde de 1 px de fichas, tablas y campos en reposo.
- **Tinta tenue** (muted-ink) y **tinta de cuerpo** (body-ink): texto secundario y de etiquetas. La aplicación usa la escala completa de tintas ink-50 a ink-950 y de azules brand-50 a brand-950 definida en el tema.

### Tertiary (riesgo RULA, nunca acción)
- **Verde de riesgo** (risk-green), puntajes 1 y 2: liso, sin trama.
- **Ámbar de riesgo** (risk-amber), puntajes 3 y 4: rayado a 45°; el número va en tinta, no en blanco. Como texto sobre blanco se usa risk-amber-text.
- **Naranja de riesgo** (risk-orange), puntajes 5 y 6: rayado cruzado (45° y −45°).
- **Rojo de riesgo** (risk-red), puntaje 7: rayado horizontal.

### Named Rules
**The One Signal Rule.** El azul de señal es el único color que invita a actuar. Si algo se puede pulsar y tiene color, es azul (o blanco sobre azul).

**The Risk-Only Inks Rule.** Verde, ámbar, naranja y rojo están reservados para el riesgo RULA. Los estados que no son riesgo (contratos, visitas) se expresan en tinta, gris o azul: un estado «rojo» se imprime en tinta negra, un estado «verde» en gris de campo.

**The Never-Color-Alone Rule.** Cada tinta de riesgo lleva su trama, su número y su texto. Una escala o insignia de riesgo que se lea solo por el color está rota.

## Typography

**Display Font:** Archivo (con ui-sans-serif, system-ui)
**Body Font:** Archivo (con ui-sans-serif, system-ui)

**Character:** Una sola grotesca con eje de ancho hace todo el trabajo: en 800 y ligeramente ensanchada (104 % en la aplicación, 110 % en los titulares de sección de la portada) es la voz del cartel; en 400 y 500 es el texto de formulario. El interletrado se cierra a −0.03 em en todo lo que es grande.

### Hierarchy
- **Display** (800, clamp de 36 a 92 px, 0.96): solo el titular del primer pliego de la portada, en blanco sobre el campo azul, a ancho normal.
- **Headline** (800, 72 px en escritorio y 2.8 rem en teléfono, 0.98): el saludo de la banda azul del panel y los titulares de sección de la portada.
- **Title** (800, 20 a 30 px): títulos de fichas, ventanas y secciones de la aplicación; nombres en la tarjeta destacada.
- **Numeral** (800, 40 a 72 px, cifras tabulares): métricas del panel, puntaje RULA, día del calendario, casillas de la escala.
- **Body** (400, 16 px, 1.5): párrafos de la portada y entradillas; las entradillas sobre azul usan blanco al 85–88 %.
- **Body small** (400, 14 a 15 px): tablas, metadatos, descripciones de la aplicación.
- **Label** (500, 13 px): etiquetas de campo y encabezados de métrica. Sin mayúsculas sostenidas ni interletrado abierto.

### Named Rules
**The One Family Rule.** Archivo es la única familia. La jerarquía sale del peso, el ancho y el tamaño, nunca de una segunda fuente.

**The Tabular Numbers Rule.** Toda cifra que se compara (puntajes, métricas, fechas en tablas, códigos) usa cifras tabulares.

## Layout

La portada sigue el kit de taste-skill (tipo de negocio: servicio): una sección por pantalla, retícula de 12 columnas con medianil de 24 px (12 px en teléfono), fondos planos alternados entre blanco y gris de campo, y la escala de espacios s-1 a s-10 (4 a 128 px). El primer pliego divide la pantalla: campo azul a la izquierda (6 columnas) y la foto impresa a la derecha con la regla RULA vertical de 64 px (40 px en teléfono) en su borde. Bajo 1024 px las columnas se apilan y las fotos bajan a 16:9 o 21:9 para que cada sección siga cabiendo en su pantalla.

La aplicación usa un contenedor de 1280 px (max-w-7xl) con márgenes de 16, 24 y 32 px según el ancho. La franja azul de 64 px queda fija arriba; la navegación completa aparece desde 1280 px y por debajo se abre como hoja lateral. El panel abre con una banda azul a ancho de ventana (64 px de alto interior en escritorio) que contiene el saludo y una ficha blanca destacada; debajo, la fila de métricas bajo una regla de 2 px, con divisiones de 1 px entre celdas. Las fichas usan 24 px de relleno y se separan 20 a 40 px.

### Named Rules
**The One Screen Per Section Rule.** En la portada cada sección cabe en una pantalla en todos los anchos; si no cabe, se acorta la foto o se oculta el texto secundario, no se deja desbordar.

## Elevation & Depth

El sistema es plano. La profundidad se construye con campos de color (azul contra blanco contra gris de campo) y con reglas de tinta, nunca con sombras. Hay una sola excepción: lo que flota de verdad sobre la página (el menú de la cuenta y las ventanas modales) lleva la sombra flotante, siempre junto a un borde de tinta o una regla azul superior de 6 px.

### Shadow Vocabulary
- **Float** (`box-shadow: 0 2px 4px rgb(18 20 24 / 0.08), 0 16px 32px -12px rgb(18 20 24 / 0.28)`): solo menús desplegables y ventanas modales.

### Named Rules
**The Flat Poster Rule.** Fichas, botones, tablas y bandas no tienen sombra. Si una superficie no flota sobre otra, no proyecta sombra.

## Shapes

Esquinas rectas en todo: 0 px en la portada, 2 px en la aplicación y el panel técnico (el tema fija todos los radios de Tailwind en 2 px). Solo los puntos indicadores (estado, ocupado, alerta) y el giro de carga son redondos; los avatares de iniciales son cuadrados. La estructura se dibuja con reglas: 2 px de tinta bajo la navegación de la portada, sobre las métricas y en el pie; 3 px sobre cada paso del proceso; 4 px como subrayado de la sección activa en la franja azul; 6 px de azul en el borde superior de las ventanas. Las fichas de contenido llevan 1 px de gris de regla; las piezas destacadas, 1 px de tinta.

## Components

### Buttons
Rectángulos macizos, sin redondeo perceptible, con una presión de 1 px al hacer clic.
- **Shape:** esquinas rectas (2 px en la aplicación, 0 en la portada); 44 px de alto (48 px en la portada).
- **Primary:** azul de señal con texto blanco, 600 a 14 px, 20 px de relleno lateral.
- **Hover / Focus:** el azul se oscurece al tono profundo en 150 ms; foco con contorno azul de 2 px separado 2 px.
- **Secondary:** blanco con borde de tinta de 1 px; en hover se invierte a tinta con texto blanco.
- **Inverse / Inverse outline:** sobre el campo azul, el botón principal es blanco con texto azul; el secundario es un contorno blanco que se rellena de blanco en hover.
- **Ghost:** texto azul subrayado (subrayado al 30 % que se completa en hover), para acciones de fila como «Ver».

### Chips
- **Insignias de estado:** rectángulos de 2 px de relleno vertical, 12 px semibold; contorno azul con texto azul (programada), contorno de tinta (en curso, por vencer), gris de campo (terminada, vencido). Pueden llevar un punto redondo de 6 px.
- **Insignia de riesgo:** casilla de 20 px con la tinta y la trama del nivel y el texto «Nivel N» en blanco (en tinta sobre ámbar), seguida del significado en la tinta del nivel.

### Cards / Containers
- **Corner Style:** 2 px.
- **Background:** papel blanco.
- **Shadow Strategy:** ninguna (ver Elevation & Depth).
- **Border:** 1 px de gris de regla; las piezas destacadas usan 1 px de tinta o una regla de 2 px de tinta bajo su encabezado.
- **Internal Padding:** 24 px (28 px en la ficha destacada de la banda azul).

### Inputs / Fields
- **Style:** blanco, 1 px de gris de regla, 44 px de alto, 14 px de relleno, 2 px de esquina; etiqueta de 13 px en 500 encima.
- **Focus:** el borde pasa a azul de señal y una línea azul de 1 px lo duplica; sin halos difusos.
- **Error / Disabled:** borde y mensaje de validación en rojo de error (el red-700 de Tailwind, distinto del rojo de riesgo) con aviso para lectores de pantalla; los errores de validación son la única excepción a la reserva de colores de riesgo; el selector de archivo es un botón secundario con el nombre del archivo al lado.

### Navigation
- **Aplicación:** franja azul de 64 px fija arriba con el logo claro; enlaces en blanco al 80 % que pasan a blanco; la sección activa lleva una barra blanca de 4 px bajo la palabra. En teléfono, una hoja blanca desde la derecha con encabezado azul y la fila activa en azul macizo.
- **Portada:** franja blanca con regla de tinta de 2 px debajo, enlaces de ancla a la izquierda, «Ingresar» y el botón principal a la derecha.

### La escala RULA impresa (signature)
Siete casillas iguales, separadas 3 a 4 px, en las cuatro tintas de riesgo con su trama y el número en Archivo 800 tabular dentro de cada casilla. Aparece como regla vertical en el borde de la foto del primer pliego, como regla horizontal grande en la sección de la escala y como cuarto panel del proceso. En la aplicación se reduce a una tira de barras de 12 px sobre una regla de tinta de 2 px, con la casilla del puntaje elevada a 24 px y su número subrayado.

### Fotomontaje azul (signature)
La foto pasa a blanco y negro (grises, contraste 1.15, brillo 1.08) y se multiplica sobre el azul de señal, de modo que el azul hace de tercera tinta. En la foto de medición se aclara (contraste 0.95, brillo 2.1) para que las líneas blancas de los ángulos se lean encima.

### Fila de métricas
Celdas sin caja bajo una regla de tinta de 2 px, separadas por divisiones de 1 px de gris de regla; etiqueta de 14 px, cifra en numeral 800 y detalle de 12 px. La celda enlazada se aclara a ink-50 en hover y su flecha pasa a azul.

## Do's and Don'ts

### Do:
- **Do** llenar regiones enteras con azul de señal plano y poner encima el titular en blanco y el botón inverso.
- **Do** acompañar cada tinta de riesgo con su trama (liso, 45°, cruzado, horizontal), su número y su texto.
- **Do** imprimir las fotos de trabajo en blanco y negro multiplicadas sobre el azul.
- **Do** separar con reglas de tinta de 2 a 4 px en lugar de cajas y sombras.
- **Do** usar Archivo 800 con ancho extendido y interletrado de −0.03 em para títulos y cifras, y cifras tabulares en toda comparación.
- **Do** repetir la escala RULA 1-7 como tira impresa donde se hable del resultado.

### Don't:
- **Don't** usar degradados, vidrio, desenfoques de fondo ni sombras difusas; la única sombra es la flotante de menús y ventanas.
- **Don't** redondear esquinas más de 2 px ni hacer botones en píldora; solo los puntos indicadores son redondos.
- **Don't** usar verde, ámbar, naranja o rojo para acciones o estados que no sean riesgo RULA.
- **Don't** mostrar el riesgo solo con color.
- **Don't** añadir una segunda familia tipográfica.
