from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from .models import Clientes


class ClienteJWTAuthentication(JWTAuthentication):
    """Autentica el token JWT contra la tabla clientes, no contra auth_user."""

    def get_user(self, validated_token):
        try:
            cliente_id = validated_token['id_cliente']
        except KeyError:
            raise AuthenticationFailed('Token inválido: falta id_cliente')

        try:
            cliente = Clientes.objects.get(id_cliente=cliente_id, activo=True)
        except Clientes.DoesNotExist:
            raise AuthenticationFailed('Cliente no encontrado o inactivo')

        cliente.is_authenticated = True
        return cliente