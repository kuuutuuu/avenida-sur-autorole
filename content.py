# Textos publicos de Kanciller.
# Los textos aprobados por el usuario no deben cambiarse sin su permiso.

# Fase 1 - /ayuda (APROBADO)
CMD_AYUDA_DESC = "Muestra la lista de comandos"
HELP_TITLE = "📖 Comandos de Kanciller"
HELP_DESCRIPTION = ""  # vacio: el embed muestra solo la lista
HELP_FOOTER = "Avenida Sur · Kanciller"

# Fase 2 - Vestidor (APROBADO)
CMD_VESTIDOR_DESC = "Personaliza tu color y tu apodo"
VESTIDOR_TITLE = "🎨 Vestidor"
VESTIDOR_DESCRIPTION = "Elige un color"
VESTIDOR_SELECT_PLACEHOLDER = "Selecciona un color"
VESTIDOR_CUSTOM_OPTION = "🎨 Color personalizado"
VESTIDOR_CUSTOM_TITLE = "Color personalizado"
VESTIDOR_HEX_LABEL = "Código hexadecimal (ej. #90A4AE)"
VESTIDOR_HEX_PLACEHOLDER = "#90A4AE"
VESTIDOR_NICK_TITLE = "Tu apodo"
VESTIDOR_NAME_LABEL = "Nombre"
VESTIDOR_NAME_PLACEHOLDER = "Ej. Jeffrey Epstein"
VESTIDOR_EMOJIS_LABEL = "Dos emojis"
VESTIDOR_EMOJIS_PLACEHOLDER = "👴🏻🏝️"
VESTIDOR_PREVIEW_TITLE = "Vista previa"
VESTIDOR_PREVIEW_DESCRIPTION = "Así se verá tu apodo: `{apodo}`"
VESTIDOR_SAVE = "Guardar"
VESTIDOR_CANCEL = "Cancelar"
VESTIDOR_SUCCESS = "Listo, se guardo tu apodo"
VESTIDOR_ERR_HEX = "El color debe ser un hex válido, por ejemplo #90A4AE."
VESTIDOR_ERR_EMOJIS = "Debes poner exactamente dos emojis."
VESTIDOR_ERR_LENGTH = "El apodo supera los 32 caracteres. Acórtalo."
VESTIDOR_ERR_OWNER = "No puedo cambiar el apodo del dueño. Copia este texto y ponlo tú: `{apodo}`"
VESTIDOR_ERR_GENERIC = "Error desconocido, dile a Pollita Sucia que agarre la pala"

# Fase 3 - Ojo de Pollita y moderacion (BORRADOR, pendiente de aprobacion)
OJO_CHANNEL = "ojo-de-pollita-👁️"
OJO_T_DELETE = "Mensaje borrado"
OJO_T_EDIT = "Mensaje editado"
OJO_T_JOIN = "Miembro nuevo"
OJO_T_LEAVE = "Miembro salió"
OJO_T_NICK = "Apodo cambiado"
OJO_T_ROLES = "Roles cambiados"
OJO_T_TIMEOUT = "Timeout aplicado"
OJO_T_BURST = "Anti-spam: ráfaga"
OJO_T_DUPS = "Anti-spam: duplicados"
OJO_T_MENTIONS = "Anti-spam: menciones"
OJO_T_INVITE = "Invite bloqueado"
OJO_T_PHISH = "Phishing bloqueado"
OJO_F_AUTOR = "Autor"
OJO_F_CANAL = "Canal"
OJO_F_CONTENIDO = "Contenido"
OJO_F_ANTES = "Antes"
OJO_F_DESPUES = "Después"
OJO_F_MOTIVO = "Motivo"
OJO_F_EDAD = "Edad de la cuenta"
OJO_REASON_BURST = "Anti-spam: ráfaga de mensajes"
OJO_REASON_DUPS = "Anti-spam: mensajes duplicados"
OJO_REASON_MENTIONS = "Anti-spam: muchas menciones"
OJO_REASON_INVITE = "Enlace de invitación bloqueado"
OJO_REASON_PHISH = "Phishing detectado"
OJO_SUSPECT_MOTIVE = "Cuenta con menos de 7 días"

# Fase 4 - Bienvenida en #isla (APROBADO)
WELCOME_MENTION = "¡Bienvenido, {usuario}!"
WELCOME_TEXT = "**Has sido bautizado en las hediondas aguas del dique**"
WELCOME_EMBED_COLOR = 0x4A90E2
WELCOME_VERIFY = "✅ Verificarme"
WELCOME_VERIFIED = "Verificado. Aquí tienes más opciones"
WELCOME_OPT_VESTIDOR = "🎨 Vestidor"
WELCOME_OPT_GUIDE = "🗺️ Guía de canales"
WELCOME_OPT_RULES = "📜 8 Mandamientos"
WELCOME_OPT_PRESENT = "👋 Preséntate"
WELCOME_THREAD_NAME = "Verificación"
WELCOME_GUIDE_TITLE = "🗺️ Guía de canales"
WELCOME_GUIDE = [
    ("#info-🚨", "Anuncios y novedades."),
    ("#comandos-💻", "Comandos de los bots y juegos."),
    ("#area-de-descargas-📶", "Descargas compartidas por los papus."),
    ("#8-mandamientos-📜", "Los ocho mandamientos de nuestro profeta."),
    ("#isla-de-epstein-🏝️", "El chat general para hablar con los papus."),
    ("#juegos-🎮", "Todo sobre videojuegos."),
    ("#música-🎧", "Aquí van los comandos del bot de música."),
    ("#el-truñito-🌲", "El rincón de nuestro truñito, riégalo a menudo."),
    ("🔊 Guevo en el mano 🍆", "Canal AFK."),
    ("🔊 La esquinita del payaso 🎪", "Canal de voz principal."),
]

# Fase 5 - Quote (BORRADOR)
QUOTE_CMD_DESC = "Genera una cita en blanco y negro"
QUOTE_TEXT_DESC = "Texto de la quote"
QUOTE_AUTHOR_DESC = "Autor de la quote (opcional)"
QUOTE_CONTEXT_NAME = "Generar quote"
QUOTE_EMPTY_ERROR = "Ese mensaje no tiene texto para citar."
QUOTE_GENERIC_ERROR = "No pude generar la quote."

# Fase 5 - Encuesta (BORRADOR)
POLL_CMD_DESC = "Crea una encuesta con botones"
POLL_MODAL_TITLE = "Nueva encuesta"
POLL_QUESTION_LABEL = "Pregunta"
POLL_QUESTION_PLACEHOLDER = "¿Qué queremos jugar hoy?"
POLL_OPTIONS_LABEL = "Opciones"
POLL_OPTIONS_PLACEHOLDER = "Una por línea"
POLL_ERROR_OPTIONS = "Pon entre 2 y 10 opciones."
POLL_EMBED_TITLE = "📊 Encuesta"
POLL_VOTE_OK = "Voto registrado."
POLL_CLOSE = "Cerrar encuesta"
POLL_CLOSED = "Encuesta cerrada."
POLL_ONLY_CREATOR = "Solo quien creó la encuesta puede cerrarla."
