from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from .models import Event, Attendee, Notification

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'users/register.html', {'form': form})

class EventListView(ListView):
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'
    ordering = ['-date']
    paginate_by = 10

class EventDetailView(DetailView):
    model = Event
    template_name = 'events/event_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['attendees'] = self.object.attendees.all()
        if self.request.user.is_authenticated:
            context['user_rsvp'] = self.object.attendees.filter(user=self.request.user).first()
        return context

class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    template_name = 'events/event_form.html'
    fields = ['title', 'description', 'date', 'location']

    def form_valid(self, form):
        form.instance.organizer = self.request.user
        return super().form_valid(form)

class EventUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Event
    template_name = 'events/event_form.html'
    fields = ['title', 'description', 'date', 'location']

    def test_func(self):
        event = self.get_object()
        return self.request.user == event.organizer

class EventDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Event
    success_url = reverse_lazy('event-list')

    def test_func(self):
        event = self.get_object()
        return self.request.user == event.organizer

def rsvp_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        status = request.POST.get('rsvp_status')
        attendee, created = Attendee.objects.update_or_create(
            user=request.user,
            event=event,
            defaults={'rsvp_status': status}
        )
        messages.success(request, f'Your RSVP status has been updated to {status}')
        Notification.objects.create(
            user=event.organizer,
            event=event,
            message=f"{request.user.username} has RSVP'd {status} to your event {event.title}"
        )
    return redirect('event-detail', pk=pk)

def send_reminder(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.user == event.organizer:
        attendees = event.attendees.filter(rsvp_status='Yes')
        for attendee in attendees:
            Notification.objects.create(
                user=attendee.user,
                event=event,
                message=f"Reminder: {event.title} is coming up on {event.date}"
            )
        messages.success(request, 'Reminders sent successfully')
    else:
        messages.error(request, 'You do not have permission to send reminders for this event')
    return redirect('event-detail', pk=pk)

@login_required
def user_profile(request):
    user_events = Event.objects.filter(organizer=request.user).order_by('-date')
    attended_events = Event.objects.filter(attendees__user=request.user).order_by('-date')
    context = {
        'user_events': user_events,
        'attended_events': attended_events,
    }
    return render(request, 'users/profile.html', context)
