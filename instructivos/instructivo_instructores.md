# Instructivo para instructores

**Bitácora del Proyecto Productivo · Tecnología en Gestión de la Producción Industrial (SENA)**

La bitácora reúne, por grupo y empresa proyecto, las evidencias que suben los aprendices para cada una de las 8 competencias, su análisis de la situación problémica, el visto bueno de cada instructor técnico y la revisión de las presentaciones. La IA propone; **el instructor siempre decide y valida**.

Dirección de la app: **https://bitacora-gpi-sena.streamlit.app**

## 1. Roles

| Rol | Qué puede hacer |
|---|---|
| Aprendiz | Crear o unirse a su grupo, subir evidencias, hacer el análisis, subir la PPT y ver recomendaciones. |
| Instructor | Ver todos los grupos y el tablero, dar visto bueno en las competencias que tiene asignadas, evaluar y validar presentaciones, crear grupos y asignar instructores. |
| Líder | Todo lo anterior, más cambiar roles de usuarios, asignar contraseñas temporales y dar visto bueno en cualquier competencia. |

## 2. Primer ingreso

1. Cree su cuenta en la pestaña **Crear cuenta** (nombre, correo y contraseña).
2. Toda cuenta nueva queda como **aprendiz**. Pida al instructor líder que lo cambie a **instructor** en Administración › Usuarios y roles.
3. Vuelva a ingresar. Verá en el menú: **Tablero, Bitácora del grupo, Presentación, Administración, Mi cuenta y Ayuda**.

## 3. Organizar los grupos (Administración)

**Grupos.** Cree un grupo con nombre, ficha, empresa y sector; la app genera un **código** para que los aprendices se unan desde Mi cuenta. Los aprendices también pueden crear su propio grupo, así que no es obligatorio que usted los cree todos. En la tabla puede corregir datos o desactivar grupos (columna **Activo**) y pulsar **Guardar cambios de grupos**.

**Instructores por competencia.** Elija el grupo y asigne el instructor técnico de cada objetivo. Marque **Aplicar esta misma asignación a todos los grupos activos** si la asignación es igual para toda la ficha. Solo el instructor asignado (o el líder) puede dar el visto bueno de esa competencia.

**Integrantes.** Revise quién está en cada grupo, agregue o quite aprendices.

**Usuarios y roles (solo líder).** Cambie roles con **Guardar roles**. Si alguien olvidó su contraseña, use **Contraseña temporal**: entréguesela por un canal privado y pídale que la cambie en Mi cuenta.

## 4. Encontrar grupos rápido

En la barra lateral, use el filtro de **Ficha** y la casilla **Solo mis grupos** (los que usted creó o donde es instructor técnico de alguna competencia). En la lista **Grupo** puede escribir para buscar por nombre o empresa.

## 5. Tablero

El **Tablero** muestra el avance de todos los grupos filtrados, en tres pestañas:

- **📈 Notas de las presentaciones:** nota final validada por grupo, aprobación y promedio por objetivo con gráfica.
- **📒 Bitácora y vistos buenos:** estado de cada objetivo por grupo (sin iniciar, en proceso, enviado, ajustes, visto bueno) y la lista **Pendientes de su visto bueno**, con acceso directo a cada uno.
- **⬇ Descargar datos (Excel / Power BI):** Excel con 3 hojas y CSV de notas por objetivo, listos para alimentar un tablero en Power BI.

## 6. Revisar la bitácora y dar visto bueno

1. Abra **Bitácora del grupo** y elija el grupo y la **Competencia / objetivo**. Los 8 cuadros de arriba muestran el estado de cada objetivo.
2. En **📎 Evidencias** revise fotos, datos y documentos. Las evidencias de **General** sirven para todas las competencias.
3. En **🔎 Situación problémica** lea la alternativa elegida por el grupo, sus respuestas a las preguntas guía, el planteamiento, las causas, el indicador y los datos que van a recolectar.
4. En **✅ Visto bueno del instructor** elija **✅ Visto bueno** o **🔁 Requiere ajustes**, escriba observaciones (obligatorias si pide ajustes) y pulse **Guardar**. Si quiere, marque **Calificar también con la rúbrica** para dejar niveles y nota parcial.
5. El historial queda guardado, con fecha e instructor.

El botón **📄 Expediente › Preparar expediente** genera el documento completo del grupo (evidencias, análisis, vistos buenos y revisiones) en HTML para imprimir o guardar como PDF.

## 7. Evaluar la presentación

1. Abra **Presentación**, elija **PPT final (los 8 objetivos)** o **Avance de un objetivo** y los minutos de exposición.
2. Deje marcada **Leer también las imágenes de las diapositivas** si la PPT tiene tablas o gráficas pegadas como imagen.
3. Suba el **.pptx** y pulse **🤖 Evaluar con IA**. Puede tardar uno o dos minutos.
4. Revise la propuesta: niveles por criterio y objetivo, justificación con número de diapositiva, evidencias encontradas y faltantes, recomendaciones y oportunidades de mejora.
5. En **Validar**, ajuste los niveles (1 a 4) donde no esté de acuerdo; la nota se recalcula sola. Edite las recomendaciones, oportunidades de mejora y observaciones.
6. Pulse **✅ Validar y publicar la nota**. Solo entonces los aprendices ven la nota.
7. Descargue el **informe de revisión** en Word o PDF para el registro.

## 8. Rúbrica y criterios de calificación

| Criterio | Peso |
|---|---|
| Contexto y problema | 15 % |
| Aplicación técnica | 35 % |
| Datos y cálculos | 20 % |
| Propuesta de solución e indicadores | 20 % |
| Comunicación y formato | 10 % |

- Niveles de 1 a 4. Nota = 1 + 4/3 × (promedio ponderado − 1), en escala 1.0 a 5.0.
- Un objetivo aprueba con **3.5 o más** y sin criterios en nivel 1.
- La PPT final aprueba con promedio de los 8 objetivos de 3.5 o más **y** todos los objetivos aprobados.
- Calibración de la IA: el nivel 1 se reserva para cuando no hay evidencia; en caso de duda se elige el nivel superior; los anexos, la extensión y los vistos buenos pendientes no restan.
- Extensión orientativa: presentación final de 15 minutos, 20 a 25 diapositivas; avance de 15 minutos, 12 a 18.

## 9. Sobre la IA

- La app usa **Gemini** (plan gratuito), con cupo diario limitado. Si se agota, intente más tarde o al día siguiente; el resto de la app sigue funcionando.
- La IA propone situaciones problémicas, retroalimentación y una nota sugerida. **No reemplaza el criterio del instructor.**
- En el plan gratuito, Google puede usar los datos enviados para mejorar sus modelos: evite subir información confidencial de la empresa sin autorización.

## 10. Buenas prácticas

- Asigne los instructores por competencia al inicio del trimestre.
- Revise semanalmente **Pendientes de su visto bueno** en el Tablero.
- Escriba observaciones concretas: qué falta, con qué dato y para cuándo.
- Valide la nota el mismo día de la sustentación y descargue el informe.
- Nunca comparta contraseñas ni claves de la app por chat; las contraseñas temporales se entregan en privado.
