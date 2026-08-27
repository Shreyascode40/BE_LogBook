from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView

from be_logbook.accounts.serializers import CustomTokenObtainPairSerializer
from be_logbook.accounts.serializers import UserDetailSerializer


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RefreshView(TokenRefreshView):
    pass


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserDetailSerializer(request.user, context={"request": request})
        return Response({"success": True, "data": serializer.data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # JWTs are stateless; the client is responsible for discarding tokens.
        return Response(
            {"success": True, "message": "Logged out."}, status=status.HTTP_200_OK
        )
