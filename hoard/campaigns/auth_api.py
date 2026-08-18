from __future__ import annotations

from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class CsrfView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        return Response({'csrfToken': get_token(request._request)})


@method_decorator(csrf_protect, name='dispatch')
class LoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request: Request) -> Response:
        username = request.data.get('username')
        password = request.data.get('password')
        if not isinstance(username, str) or not isinstance(password, str):
            return Response({'detail': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(request._request, username=username, password=password)
        if user is None:
            return Response({'detail': 'Invalid username or password.'}, status=status.HTTP_400_BAD_REQUEST)
        login(request._request, user)
        return Response({'id': user.pk, 'username': user.get_username()})


class LogoutView(APIView):
    def post(self, request: Request) -> Response:
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionView(APIView):
    def get(self, request: Request) -> Response:
        return Response({'id': request.user.pk, 'username': request.user.get_username()})
