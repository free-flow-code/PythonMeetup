from django.db import models

# Create your models here.
class Client(models.Model):
    chat_id = models.CharField(max_length=20, verbose_name='ID чата клиента')
    first_name = models.CharField(max_length=40, verbose_name='Имя клиента', null=True, blank=True)
    last_name = models.CharField(max_length=100, verbose_name="Фамилия клиента", null=True, blank=True)
    created_at = models.DateTimeField(verbose_name="Создано", auto_now_add=True)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f'{self.chat_id}: {self.first_name} {self.last_name}'


class Event(models.Model):
    name = models.CharField(max_length=150, verbose_name='Название мероприятия')
    description = models.TextField(verbose_name='Описание мероприятия', blank=True, null=True)
    date = models.DateField(verbose_name='Дата мероприятия')
    start_time = models.TimeField(verbose_name='Время начала мероприятия')
    visitors = models.ManyToManyField(
        Client,
        through='Visitor',
        related_name='events',
        verbose_name='Посетители',
    )

    class Meta:
        verbose_name = 'Мероприятие'
        verbose_name_plural = 'Мероприятия'

    def __str__(self):
        return f'{self.name} {self.date} {self.start_time}'


class Visitor(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name='Клиент')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, verbose_name='Мероприятие')
    created_at = models.DateTimeField(verbose_name='Записан', auto_now_add=True)

    class Meta:
        verbose_name = 'Посетитель'
        verbose_name_plural = 'Посетители'

    def __str__(self):
        return f' {self.event.name}: {self.client.first_name} {self.client.last_name}'


class Presentation(models.Model):
    name = models.CharField(max_length=150, verbose_name='Название презентации')
    annotation = models.TextField(verbose_name='Аннотация')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, verbose_name='Мероприятие', related_name='presentations')
    start_time = models.TimeField(verbose_name='Время начала презентации')
    end_time = models.TimeField(verbose_name='Время окончания презентации')
    is_finished = models.BooleanField(verbose_name='Завершен', default=False)
    speaker = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name='Спикер', related_name='presentations')

    class Meta:
        verbose_name = 'Доклад'
        verbose_name_plural = 'Доклады'

    def __str__(self):
        return f'{self.name}: {self.event.name}'


class Question(models.Model):
    question_number = models.IntegerField(verbose_name='Номер вопроса')
    text = models.TextField(verbose_name='Текст вопроса')
    presentation = models.ForeignKey(Presentation, on_delete=models.CASCADE, verbose_name='Презентация', related_name='questions')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name='Клиент', related_name='questions')
    created_at = models.DateTimeField(verbose_name='Задан', auto_now_add=True)
    # is_closed = models.BooleanField(verbose_name='Закрыт', default=False)

    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'

    def __str__(self):
        return f'{self.text}, {self.client.first_name} {self.client.last_name}'

class Likes(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name='Вопрос', related_name='likes')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name='Клиент', related_name='likes')
    created_at = models.DateTimeField(verbose_name='Поставлен', auto_now_add=True)

    class Meta:
        verbose_name = 'Лайк'
        verbose_name_plural = 'Лайки'

    def __str__(self):
        return f'{self.question.text}: {self.client.first_name} {self.client.last_name}'
