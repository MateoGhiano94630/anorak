"""
Subida y borrado de imágenes en Cloudflare R2.

R2 habla el protocolo de S3, así que se usa boto3. Ningún test toca este
módulo de verdad: `get_cliente_r2` se mockea en `tests/conftest.py`, que es el
único punto por el que se sale a la red.
"""

import logging
import uuid
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Cuánto vive la dirección con la que el navegador baja una foto. Diez minutos
# alcanzan para mirar una pantalla de catálogo y son poco tiempo para que la
# dirección sirva si se filtra.
SEGUNDOS_URL_FIRMADA = 600

FORMATOS_ACEPTADOS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

# Tres megas por foto. Una foto de prenda sacada con el celular pesa menos, y
# el límite evita que una imagen sin recortar tape la pantalla del mostrador
# en una conexión lenta.
TAMANIO_MAXIMO_BYTES = 3 * 1024 * 1024


class R2NoConfiguradoError(RuntimeError):
    """R2 no tiene credenciales cargadas en este entorno."""


def esta_configurado() -> bool:
    """Dice si hay credenciales de R2 cargadas."""
    return bool(
        settings.r2_endpoint_url
        and settings.r2_access_key_id
        and settings.r2_secret_access_key
    )


def get_cliente_r2() -> Any:
    """Devuelve el cliente de R2. Es el único punto que sale a la red."""
    if not esta_configurado():
        raise R2NoConfiguradoError(
            "El guardado de imágenes no está configurado en este servidor."
        )
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def clave_para(producto_id: uuid.UUID, extension: str) -> str:
    """Arma la clave del objeto: una carpeta por producto."""
    return f"productos/{producto_id}/{uuid.uuid4().hex}.{extension}"


def subir_imagen(clave: str, contenido: bytes, content_type: str) -> None:
    """Guarda una imagen en R2."""
    cliente = get_cliente_r2()
    cliente.put_object(
        Bucket=settings.r2_bucket_name,
        Key=clave,
        Body=contenido,
        ContentType=content_type,
    )


def eliminar_imagen(clave: str) -> None:
    """Borra una imagen de R2.

    No propaga el error: si la foto ya no está, o R2 no contesta, la fila de
    la base igual se borra. Quedarse con una foto huérfana en el bucket
    cuesta centavos; dejar en el sistema una foto que la persona ya borró se
    ve como que el sistema no obedece.
    """
    try:
        get_cliente_r2().delete_object(Bucket=settings.r2_bucket_name, Key=clave)
    except (BotoCoreError, ClientError, R2NoConfiguradoError):
        logger.exception("No se pudo borrar la imagen %s de R2", clave)


def url_firmada(clave: str) -> str:
    """Devuelve una dirección temporal para mostrar la imagen."""
    cliente = get_cliente_r2()
    url: str = cliente.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.r2_bucket_name, "Key": clave},
        ExpiresIn=SEGUNDOS_URL_FIRMADA,
    )
    return url
