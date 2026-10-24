# web

Proyecto Astro en Vercel: panel de administración, página del invitado, API de sesiones, envío de correos con Resend y limpieza diaria, sobre Supabase. Las reglas duras de la raíz (`../CLAUDE.md`) mandan sobre este archivo.

**Foco:** simpleza, una página del invitado rápida, una API idempotente, la privacidad del correo y el costo.

## Independencia (D36)

- No importa nada de `edge/`. El edge le habla por HTTPS con un token por equipo, y ambos comparten el contrato de datos solo como archivos.
- Dependencias, entorno y secretos propios: `package.json`, su lockfile y `.env`.
- Este archivo debe poder leerse sin el de la raíz, por si algún día `web/` se separa a su propio repositorio.

## Estructura (D35)

- Endpoints delgados en `src/pages/api/` que llaman funciones de `src/lib/` (*transaction script*). Sin capa de repositorios sobre Supabase.
- Componentes interactivos solo donde hacen falta. La página del invitado es casi estática y cacheable.
- La clave de servicio de Supabase solo existe en el servidor y nunca llega al navegador.
- El video no pasa por Vercel: va del edge a R2. La web guarda solo su ubicación.

## Pruebas

Herramienta: Vitest, que es lo habitual con Astro. Confírmala al crear el proyecto.

**Se prueba**
- El *upsert* de sesiones: subir dos veces la misma toma no duplica la fila.
- La autenticación del token del edge.
- La búsqueda por `share_code` y la respuesta cuando el video ya se borró.
- La limpieza: anonimizar correos vencidos y marcar los videos vencidos, con el valor configurable.
- La validación de la carga de subida y que un reenvío no duplique el envío.
- El correo del invitado fuera de los logs.

**No se prueba**
- Componentes ni estilos. A lo sumo hay una prueba de humo de la página del invitado.
- Supabase, Resend ni Vercel en sí.

**Reglas**
- Un cambio pequeño agrega como máximo una prueba, y solo si cambia un comportamiento de la lista. Un bug corregido deja una sola prueba, la que lo habría detectado.
- Se parametriza en vez de repetir.
- Las líneas de pruebas no superan las del código de producción.
- Las pruebas usan un cliente de Supabase falso o una base local de prueba (por decidir). Nunca la base real. Nunca envían correos reales.
- Antes de agregar pruebas, di cuántas y por qué.

## Astro (reglas del generador)

Venían en el `AGENTS.md` que crea `npm create astro`. Se conservan aquí, en un solo archivo.

**Servidor de desarrollo:** arráncalo en segundo plano con `astro dev --background`. Se maneja con `astro dev stop`, `astro dev status` y `astro dev logs`.

**Documentación:** https://docs.astro.build. Consulta estas guías antes de tocar lo relacionado:

- [Páginas, rutas dinámicas y middleware](https://docs.astro.build/en/guides/routing/)
- [Componentes Astro](https://docs.astro.build/en/basics/astro-components/)
- [Componentes de React, Vue, Svelte u otros](https://docs.astro.build/en/guides/framework-components/)
- [Contenido y colecciones](https://docs.astro.build/en/guides/content-collections/)
- [Estilos y Tailwind](https://docs.astro.build/en/guides/styling/)
- [Varios idiomas](https://docs.astro.build/en/guides/internationalization/)
