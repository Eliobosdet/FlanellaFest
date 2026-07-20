from django.shortcuts import render
from .forms import *
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy


class CreateOrganizerView(PermissionRequiredMixin, CreateView):
    permission_required = "is_staff"
    form_class = NewUserOrganizer
    template_name = "user_create.html"
    success_url = reverse_lazy("register_organizer")
