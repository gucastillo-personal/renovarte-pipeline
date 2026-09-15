# Reglas de flujo de trabajo

## Nunca mergear Pull Requests

Claude puede crear ramas `feature/*`, commitear, pushear, abrir PRs y esperar
los checks — pero el merge final a `main` lo ejecuta siempre una persona
humana, sin excepción, aunque todos los checks requeridos estén en verde. No
uses `gh pr merge` ni equivalentes.
