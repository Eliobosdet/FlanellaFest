from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group


class NewUserOrganizer(UserCreationForm):
    user_group_name = "Organizer"

    def save(self, commit=True):
        user = super().save(commit)
        g = Group.objects.get(name="Organizer")
        g.user_set.add(user)
        return user
