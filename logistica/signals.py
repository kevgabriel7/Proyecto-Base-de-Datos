# logistica/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Seguimiento, Envios


@receiver(post_save, sender=Seguimiento)
def actualizar_estado_envio(sender, instance, created, **kwargs):
    """
    Cada vez que se crea un nuevo registro de Seguimiento,
    actualiza el estado actual del Envío relacionado.
    """
    if created:
        Envios.objects.filter(pk=instance.id_envio_id).update(
            id_estado_actual=instance.id_estado_id
        )