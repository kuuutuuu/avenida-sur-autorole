# Avenida Sur - Autorole Forastero

Bot minimo para Discord que asigna el rol **Forastero** a los nuevos miembros de Avenida Sur.

- `on_member_join`: asigna el rol al instante.
- Catch-up al arrancar: asigna el rol a miembros sin ningun rol.
- Endpoints HTTP: `/` (health) y `/status` (estado de conexion).

Variables de entorno: `DISCORD_TOKEN`, `GUILD_ID`, `ROLE_ID`, `PORT` (Render lo define).
