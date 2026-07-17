from typing import Type

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from django_rest_passwordreset.signals import reset_password_token_created

from backend.models import ConfirmEmailToken, User, Order

new_user_registered = Signal()

new_order = Signal()


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
    msg = EmailMultiAlternatives(
        f"Password Reset Token for {reset_password_token.user}",
        reset_password_token.key,
        settings.EMAIL_HOST_USER,
        [reset_password_token.user.email]
    )
    msg.send()


@receiver(post_save, sender=User)
def new_user_registered_signal(sender: Type[User], instance: User, created: bool, **kwargs):
    if created and not instance.is_active:
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=instance.pk)

        msg = EmailMultiAlternatives(
            f"Password Reset Token for {instance.email}",
            token.key,
            settings.EMAIL_HOST_USER,
            [instance.email]
        )
        msg.send()


@receiver(new_order)
def new_order_signal(user_id, **kwargs):
    """
    Отправка уведомлений при новом заказе
    """
    # Получить пользователя
    user = User.objects.get(id=user_id)
    
    # Получить последний заказ пользователя
    order = Order.objects.filter(user_id=user_id).exclude(state='basket').first()
    
    # Посчитать сумму заказа
    total_sum = 0
    if order:
        from django.db.models import Sum, F
        total_sum = order.ordered_items.aggregate(
            total=Sum(F('product_info__price') * F('quantity'))
        )['total'] or 0

    # Отправить уведомление пользователю
    msg_user = EmailMultiAlternatives(
        "Обновление статуса заказа",
        'Заказ сформирован',
        settings.EMAIL_HOST_USER,
        [user.email]
    )
    msg_user.send()
    
    # Отправить уведомление администратору
    admin_email = settings.ADMIN_EMAIL or settings.EMAIL_HOST_USER
    msg_admin = EmailMultiAlternatives(
        "Новый заказ",
        f'Заказ #{order.id} от {user.email} на сумму {total_sum}',
        settings.EMAIL_HOST_USER,
        [admin_email]
    )
    msg_admin.send()
