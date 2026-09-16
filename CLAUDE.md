# Reglas de flujo de trabajo

Estas reglas aplican a cualquier sesión de Claude Code (o cualquier agente)
que trabaje en este repo, no solo a la sesión que las escribió.

## Nunca mergear Pull Requests

El merge final a `main` lo ejecuta siempre una persona humana, sin
excepción, aunque todos los checks requeridos estén en verde. No uses
`gh pr merge` ni equivalentes.

## Aprobación humana obligatoria antes de actuar

- Ningún agente puede instalar herramientas, paquetes o dependencias (brew,
  npm, pnpm, pip, uv, vercel CLI, gh CLI, etc.) ni ejecutar scripts que no
  sean de solo lectura, sin pedir aprobación humana explícita antes de
  hacerlo.
- Antes de cada `git commit` y antes de cada `git push` hay que pedir
  aprobación humana explícita — no alcanza con que el humano haya aprobado
  la tarea en general; cada commit y cada push necesitan su propio ok.
