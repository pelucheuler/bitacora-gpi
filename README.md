# Bitácora del Proyecto Productivo GPI

App web para que cada grupo de aprendices lleve la bitácora de su empresa proyecto:

- **Aprendices**: cargan evidencias por competencia (fotos, datos de la empresa, notas, Excel), reciben de la IA varias *posibles* situaciones problémicas con preguntas guía, hacen su propio análisis y lo envían al instructor. Al final suben la PPT y reciben recomendaciones y oportunidades de mejora.
- **Instructor técnico de cada competencia**: ve las evidencias y el análisis, da **visto bueno** o pide **ajustes** con observaciones (queda el historial).
- **Cualquier instructor**: ve el tablero con el avance de todos los grupos, valida la nota de la PPT (avance o final) con la rúbrica unificada y descarga el **expediente** del grupo.
- **Líder** (usted): crea grupos, asigna el instructor de cada competencia y cambia los roles.

Todo queda guardado en Supabase (base de datos y archivos), así que no se pierde y cualquier instructor puede consultarlo.

| Pieza | Para qué | Costo |
|---|---|---|
| Supabase | Base de datos, fotos/archivos e inicio de sesión | Gratis (500 MB de datos, 1 GB de archivos) |
| Streamlit Community Cloud | Publica la app en una dirección web | Gratis |
| GitHub | Guarda el código para que Streamlit lo publique | Gratis |
| IA | Describir fotos, proponer problemas, revisar PPT | Gemini gratis (automático, con cupo diario), claude.ai de cada uno (copiar y pegar) o Claude por API (pago por uso) |

---

## Instalación (una sola vez, unos 30 minutos)

### 1. Crear la base de datos en Supabase

1. Entre a <https://supabase.com>, cree una cuenta y pulse **New project**.
   - Nombre: `bitacora-gpi`. Región: la más cercana (por ejemplo *South America (São Paulo)*).
   - Anote la contraseña de la base de datos en un lugar seguro (no la necesita la app).
   - Si aparece la opción **Data API**, déjela activada.
2. Cuando el proyecto esté listo, vaya a **SQL Editor → New query**, pegue **todo** el contenido de `supabase_schema.sql` y pulse **Run**. Debe decir *Success*.
3. Vaya a **Authentication → Sign In / Providers → Email** y **desactive "Confirm email"**. Así los aprendices entran apenas crean la cuenta. (El correo gratuito de Supabase envía muy pocos mensajes por hora y no alcanzaría para un grupo completo.)
4. Si ya había ejecutado `supabase_schema.sql` antes del 20 de noviembre, ejecute también `actualizacion_v2.sql` (agrega la contraseña temporal). Si lo ejecuta por primera vez ahora, no hace falta: ya viene incluido.
5. En **Project Settings → API Keys** copie dos datos: la **Project URL** (`https://….supabase.co`) y la clave **anon public** (o **publishable**).
   ⚠️ Nunca use la clave *service_role* / *secret* en la app.

### 2. Decidir cómo usar la IA

La app elige sola según la clave que ponga en los Secrets de Streamlit: si hay `ANTHROPIC_API_KEY` usa Claude; si no, y hay `GEMINI_API_KEY`, usa Gemini; si no hay ninguna, usa el modo copiar/pegar en claude.ai.

**Opción recomendada para empezar: Gemini gratis (automático).**

1. Entre a <https://aistudio.google.com> con una cuenta de Google y acepte los términos.
2. Pulse **Get API key → Create API key** (si pide proyecto, deje el que crea por defecto). Copie la clave (empieza por `AIza`).
3. En Streamlit: su app → **⋮ → Settings → Secrets**, agregue esta línea debajo de las de Supabase y guarde:

   ```toml
   GEMINI_API_KEY = "AIza...su clave..."
   ```

   La app se reinicia sola y desde ese momento los botones dicen **"🤖 … con IA"**.

Cupo gratuito aproximado (Google lo cambia sin aviso; véalo en <https://aistudio.google.com/rate-limit>):
- **Revisar una PPT** usa el modelo Gemini Flash: unas **20 revisiones al día** y 5 por minuto para todo el proyecto. Cada PPT va en una sola solicitud con su texto y sus imágenes.
- **Fotos, alternativas de problema y retroalimentación** usan Gemini Flash-Lite: unas 500 al día.
- Si se acaba el cupo de Flash, la app intenta con Flash-Lite; si también se acaba, avisa y hay que esperar al día siguiente (se renueva a medianoche de California, 3 a. m. de Colombia).

⚠️ **Privacidad**: en el plan gratuito, Google puede usar lo que se envía (texto de la PPT, fotos de la empresa) para mejorar sus productos, y personas de Google pueden revisarlo. No suba datos confidenciales de la empresa ni datos personales. Si las empresas lo exigen, use el plan pago de Gemini o Claude por API.

**Opción sin clave: con la cuenta de claude.ai de cada uno (copiar y pegar).** Si no pone ninguna clave. En cada lugar donde la app usa IA aparece un recuadro **"Instrucciones para Claude"**:

1. La app prepara las instrucciones (con la rúbrica, las evidencias o el texto de la PPT).
2. Usted abre <https://claude.ai> con su cuenta, conversación nueva, pega las instrucciones (o adjunta el .txt) y, según el caso, adjunta las fotos o la PPT guardada como **PDF**.
3. Copia la respuesta completa de Claude y la pega en la app, que la guarda igual que si fuera automática (nota propuesta por objetivo, recomendaciones, oportunidades de mejora, extensión para 15 minutos y problemáticas sugeridas).

Funciona para: describir fotos, proponer alternativas de problema, retroalimentar el análisis y revisar la PPT (avance o final). Con el plan gratuito de claude.ai una PPT final grande puede agotar el límite del día; con Pro alcanza de sobra.

**Opción Claude por API (pago por uso).** Si más adelante quiere que todo sea con un clic, cree una clave en <https://console.anthropic.com> (Billing → cargar saldo y poner límite; API Keys → Create Key) y agréguela en los Secrets de Streamlit como `ANTHROPIC_API_KEY`. La app cambia sola al modo automático. Costo aproximado: describir 5 fotos USD 0,05; proponer alternativas USD 0,10–0,20; PPT final de 35 diapositivas con ~40 imágenes USD 1–1,50.

### 3. Subir el código a GitHub

1. Cree una cuenta en <https://github.com> y un repositorio nuevo, por ejemplo `bitacora-gpi` (puede ser privado).
2. En el repositorio pulse **Add file → Upload files** y arrastre **todo el contenido** de esta carpeta (`app.py`, `requirements.txt`, `supabase_schema.sql`, `README.md` y las carpetas `gpi` y `.streamlit`). Pulse **Commit changes**.
   - El código no tiene claves; las claves van solo en el paso 4.

### 4. Publicar la app en Streamlit Community Cloud

1. Entre a <https://share.streamlit.io> con su cuenta de GitHub y pulse **Create app → Deploy a public app from GitHub**.
2. Repositorio: `bitacora-gpi`, rama `main`, archivo principal `app.py`.
3. Abra **Advanced settings → Secrets** y pegue (con sus datos):

   ```toml
   SUPABASE_URL = "https://xxxxxxxx.supabase.co"
   SUPABASE_ANON_KEY = "la clave anon / publishable"
   ```

   (Agregue también `GEMINI_API_KEY = "AIza..."` para usar Gemini, o `ANTHROPIC_API_KEY = "sk-ant-..."` para Claude por API.)

4. Pulse **Deploy**. En uno o dos minutos tendrá la dirección de la app (algo como `https://bitacora-gpi.streamlit.app`).

### 5. Primer ingreso y configuración

1. Abra la app, pestaña **Crear cuenta**, y regístrese con su correo.
2. En Supabase, **SQL Editor**, ejecute esta línea con su correo para quedar como líder:

   ```sql
   update public.perfiles set rol = 'lider' where correo = 'su_correo@ejemplo.com';
   ```

3. Recargue la app. En **Administración**:
   - **Grupos**: cree cada grupo con su empresa proyecto. La app le da un **código** (ej. `A3F9C1`) para que los aprendices se unan.
   - **Usuarios y roles**: cuando sus compañeros instructores creen su cuenta, cámbieles el rol a *instructor*.
   - **Instructores por competencia**: asigne el instructor técnico de cada una de las 8 competencias (puede aplicar la misma asignación a todos los grupos).
4. Los aprendices crean su cuenta, van a **Mi cuenta** y escriben el código del grupo.
5. **Si alguien olvida su contraseña**: en **Administración → Usuarios y roles → Contraseña temporal** usted le asigna una, se la entrega, y la persona la cambia en **Mi cuenta**. (No depende del correo de Supabase.)

---

## Uso diario

**Aprendices** → *Bitácora del grupo*: elijan la competencia, agreguen evidencias (la IA puede describir las fotos; ustedes corrigen), en *Situación problémica* pidan alternativas, elijan una, respondan las preguntas guía, pidan retroalimentación y **envíen al instructor**. En *Presentación* suban la PPT (.pptx) para recibir recomendaciones; la nota aparece cuando el instructor la valida.

**Instructor técnico** → *Tablero*: muestra lo pendiente de su visto bueno. Abra el grupo, revise evidencias y análisis, y en *Visto bueno* elija **Visto bueno** o **Requiere ajustes** con observaciones (opcionalmente con nota de la rúbrica).

**Revisar una PPT sin clave de API** → *Presentación*: suba el .pptx, siga los pasos del recuadro (instrucciones + PDF en claude.ai) y pegue la respuesta; queda como revisión pendiente de validación.

**Validar una PPT** → *Presentación*: elija la revisión pendiente, ajuste los niveles (1 a 4) donde no esté de acuerdo con la IA, edite recomendaciones y oportunidades de mejora, y pulse **Validar y publicar la nota**. En la PPT final la IA también compara la presentación con los vistos buenos y observaciones de la bitácora.

**Informe de revisión** → *Presentación*, sobre cada revisión: **⬇ Informe en Word** (.doc, se abre y edita en Word) o **⬇ Informe para PDF** (ábralo e *Imprimir → Guardar como PDF*). Los aprendices descargan el informe sin la nota hasta que el instructor la valide.

**Tablero** → tres pestañas: *Notas de las presentaciones* (nota por objetivo de la última PPT final de cada grupo, promedios y gráfico por competencia), *Bitácora y vistos buenos* (avance del trimestre en la app) y *Descargar datos* (Excel con 3 hojas o CSV, listo para Power BI: Obtener datos → Libro de Excel).

**Muchos grupos** → en el menú lateral los instructores filtran por **Ficha** y **Solo mis grupos** (los que crearon o donde son instructor técnico), y el selector de grupo permite escribir para buscar. El Tablero usa los mismos filtros.

**Crear grupos sin el líder** → los instructores crean grupos en *Administración*. Los aprendices también pueden: en **Mi cuenta → ¿Su grupo aún no existe?** un integrante lo crea (nombre, ficha, empresa) y comparte el código; si ya existía un grupo de esa ficha con la misma empresa, la app lo une a ese en lugar de duplicarlo.

**Expediente** → botón *📄 Expediente* en la bitácora: descarga un HTML con todo (evidencias con miniaturas, análisis, vistos buenos, nota final). Ábralo y use *Imprimir → Guardar como PDF*.

Rúbrica unificada: Contexto y problema 15 %, Aplicación técnica 35 %, Datos y cálculos 20 %, Propuesta de solución e indicadores 20 %, Comunicación y formato 10 %. Nota = 1 + 4/3·(Σ peso·nivel − 1). Aprueba con 3,5 o más y ningún criterio en nivel 1; en la final, promedio de los 8 objetivos y todos aprobados.

## Imagen institucional e instructivos

- **Colores**: la app usa la paleta institucional del SENA (verde `#39A900`, azul oscuro `#00304D`, verde oscuro `#007832`) y la letra Work Sans. Se cambian en `.streamlit/config.toml` y `gpi/marca.py`.
- **Logo**: guarde el logo oficial del SENA como `assets/logo_sena.png` (PNG, fondo transparente). Aparece en el ingreso, la barra lateral, la pestaña del navegador y los informes descargables. Sin ese archivo la app funciona igual.
- **Instructivos**: `instructivos/` trae el de aprendices y el de instructores en Word y PDF. Dentro de la app están en el menú **Ayuda** y en la pestaña **¿Cómo funciona?** de la pantalla de ingreso. Para cambiarlos, edite los `.md` (los ve la app) y vuelva a generar el Word/PDF.

---

## Bueno saber

- **Supabase gratis se pausa** si pasa una semana sin uso. Los datos no se pierden: entre a supabase.com y pulse **Restore project**.
- **La app de Streamlit se duerme** si nadie la usa por un tiempo; al abrirla, pulse *"Yes, get this app back up"* y espere un minuto.
- **Archivos**: las fotos se reducen automáticamente (~300 KB). 1 GB alcanza para unas 3.000 fotos. Las PPT de más de 45 MB (por ejemplo con video) no se guardan como archivo, pero sí su contenido y la evaluación.
- **Privacidad**: las fotos y documentos de la empresa están en un almacenamiento privado; solo los integrantes del grupo y los instructores con cuenta pueden verlos.
- **Copia de seguridad**: en Supabase, *Table Editor* → cada tabla → *Export to CSV*. Y el expediente de cada grupo al cierre del trimestre.
- **Permisos** (aplicados en la base de datos, no solo en la app): un aprendiz solo ve su grupo; solo el instructor asignado (o el líder) da visto bueno en su competencia; solo instructores validan notas; solo el líder cambia roles.

## Archivos

```
app.py                  la app (pantallas)
gpi/catalogo.json       8 objetivos/competencias, RAP, evidencias esperadas y rúbrica
gpi/ia.py               instrucciones a la IA (fotos, alternativas, retroalimentación, PPT)
gpi/pptx_lector.py      lectura de la PPT y de sus imágenes
gpi/datos.py            conexión con Supabase
gpi/expediente.py       expediente e informe de revisión descargables
gpi/reportes.py         tablas del tablero y Excel para Power BI
gpi/marca.py            colores institucionales SENA y logo
assets/                 aquí va el logo oficial (logo_sena.png)
instructivos/           instructivos para aprendices e instructores (md, Word, PDF)
supabase_schema.sql     tablas, permisos y almacenamiento (se pega en Supabase)
actualizacion_v2.sql    solo para quien ya había instalado la versión 1 (contraseña temporal)
actualizacion_v3.sql    aprendices crean su grupo + corrección de seguridad de roles
requirements.txt        librerías de Python
.streamlit/config.toml  colores SENA, letra y tamaño máximo de archivos
```

Para cambiar competencias, evidencias esperadas o la rúbrica, edite `gpi/catalogo.json` en GitHub; Streamlit vuelve a publicar la app solo.
