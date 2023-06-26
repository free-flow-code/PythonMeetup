from django.contrib import admin
from meetups.models import (
    Client,
    Event,
    Visitor,
    Presentation,
    Likes,
    Question,
    Donate,
    Organizer,
)

admin.site.register(Client)
admin.site.register(Event)
admin.site.register(Visitor)
admin.site.register(Presentation)
admin.site.register(Likes)
admin.site.register(Question)
admin.site.register(Donate)
admin.site.register(Organizer)
