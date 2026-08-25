# Anorak

Sistema de gestión para un local de ropa en Argentina: facturación contra
ARCA y moneda en pesos.

El alcance de los módulos de negocio se está redefiniendo. Hoy el sistema
tiene ingreso, usuarios y auditoría automática — ver
[docs/handoff.md](docs/handoff.md).

## Puesta en marcha

```bash
# Backend
cd backend
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env          # y completar
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload      # http://localhost:8000

# Frontend (en otra terminal)
cd frontend
pnpm install
pnpm dev                                      # http://localhost:5173
```

Al arrancar por primera vez, el backend crea la cuenta `admin@anorak.com.ar`
con la contraseña de `SEED_PASSWORD`. Cambiala apenas entres.

## Verificar antes de commitear

```bash
cd backend  && .venv/bin/ruff check app tests alembic \
            && .venv/bin/black --check app tests alembic \
            && .venv/bin/mypy app && .venv/bin/pytest
cd frontend && pnpm exec tsc -b && pnpm exec eslint . && pnpm test && pnpm build
```

## Documentación

| Archivo | Para qué |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Stack, comandos, reglas del proyecto y errores ya resueltos |
| [docs/arquitectura.md](docs/arquitectura.md) | El porqué de cada decisión y qué alternativa se descartó |
| [docs/handoff.md](docs/handoff.md) | El estado real: qué está hecho, qué falta |
| [docs/despliegue.md](docs/despliegue.md) | Cómo poner el sistema en producción, paso a paso |
| [CHANGELOG.md](CHANGELOG.md) | Qué cambió, por módulo |
| `docs/manual/` | Manual para quien atiende el local (`mkdocs serve`) |
