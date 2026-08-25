"""Configuración del sistema, leída del entorno o de backend/.env."""

from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Contraseña de fábrica de las cuentas del seed. Si sigue siendo esta, el
# arranque avisa por log que hay que cambiarla.
PASSWORD_SEED_POR_DEFECTO = "anorak1234"


class Settings(BaseSettings):
    """Parámetros de configuración. Todo tiene default para que los tests
    corran sin `.env` y sin variables de entorno definidas."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Base de datos ────────────────────────────────────────────────────────
    # En producción va la URL del **session pooler** de Supabase:
    # `aws-0-<región>.pooler.supabase.com`, puerto 5432. La URL directa
    # (db.<ref>.supabase.co) resuelve solo a IPv6 y Railway sale por IPv4:
    # falla con "Network is unreachable".
    #
    # El puerto 6543 del mismo host es el *transaction* pooler, que es otra
    # cosa: rompe las consultas preparadas de asyncpg salvo que se desactive
    # el caché a mano. Ver docs/despliegue.md §2.
    database_url: str = "sqlite+aiosqlite:///./local.db"

    # ── Sesión ───────────────────────────────────────────────────────────────
    jwt_secret_key: str = "dev-secret-key-cambiar-en-produccion"
    # Una jornada de local con margen: quien abre a la mañana no queda afuera
    # a media tarde en el medio de una venta.
    jwt_expire_hours: int = 12

    environment: str = "development"

    # Contraseña inicial de las cuentas creadas por el seed. Definirla en
    # Railway para no dejar la de fábrica.
    seed_password: str = PASSWORD_SEED_POR_DEFECTO

    # ── Caja ─────────────────────────────────────────────────────────────────
    # El fondo que queda en el cajón para dar vuelto. La apertura lo propone y
    # quien abre puede corregirlo. Va como parámetro y no clavado en el código
    # para que cambiarlo sea una variable de entorno.
    fondo_fijo_sugerido: Decimal = Decimal("20000.00")

    # ── Facturación electrónica ──────────────────────────────────────────────
    # Apagada hasta tener los certificados. Con esto en false el servicio de
    # ARCA no se instancia y los endpoints fiscales devuelven 503.
    arca_habilitado: bool = False
    arca_env: str = "homologacion"
    arca_cuit: str = ""
    arca_punto_venta: int = 1

    # ── Cloudflare R2 ────────────────────────────────────────────────────────
    # Sin consumidor hasta que vuelva a haber un módulo que guarde imágenes.
    # Queda declarado porque es parte del stack elegido y el rubro no cambió.
    r2_endpoint_url: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "anorak-imagenes"

    frontend_url: str = "http://localhost:5173"

    # ── Datos del emisor (para tickets y comprobantes) ───────────────────────
    emisor_razon_social: str = "Anorak"
    emisor_cuit: str = ""
    emisor_condicion_iva: str = "Responsable Inscripto"


settings = Settings()
