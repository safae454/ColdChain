from .models import Dht11
from .serializers import DHT11serialize
from rest_framework.decorators import api_view
from rest_framework import generics
from rest_framework.response import Response
from django.core.mail import send_mail
from django.conf import settings
import telebot

SEUIL_TEMPERATURE = 27
DELAI_NOUVELLE_ALERTE = 120  # secondes sans mesure avant de considérer un nouvel épisode


@api_view(['GET'])
def Dlist(request):
    all_data = Dht11.objects.all()
    data = DHT11serialize(all_data, many=True).data
    return Response({'data': data})


class Dhtviews(generics.CreateAPIView):
    queryset = Dht11.objects.all()
    serializer_class = DHT11serialize

    def perform_create(self, serializer):
        mesure = serializer.save()
        temperature = mesure.temperature

        if temperature <= SEUIL_TEMPERATURE:
            return

        # Y avait-il déjà un dépassement juste avant cette mesure ?
        precedente = Dht11.objects.exclude(pk=mesure.pk).order_by('-id').first()
        deja_en_alerte = (
            precedente is not None
            and precedente.temperature > SEUIL_TEMPERATURE
            and (mesure.date - precedente.date).total_seconds() <= DELAI_NOUVELLE_ALERTE
        )
        if deja_en_alerte:
            return  # alerte déjà envoyée pour ce dépassement

        message = f"Alerte ! Temperature = {temperature} °C"

        try:
            send_mail(
                subject="Alerte Temperature",
                message=message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[settings.ALERT_EMAIL_TO],
                fail_silently=False,
            )
        except Exception as e:
            print("Erreur Gmail :", e)

        try:
            bot = telebot.TeleBot(settings.TELEGRAM_TOKEN)
            bot.send_message(settings.TELEGRAM_CHAT_ID, message)
        except Exception as e:
            print("Erreur Telegram :", e)