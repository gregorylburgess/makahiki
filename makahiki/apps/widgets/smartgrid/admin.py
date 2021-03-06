"""Admin definition for Smart Grid Game widget."""
from django.db import models
from django.http import HttpResponseRedirect
from apps.managers.cache_mgr import cache_mgr
from apps.managers.challenge_mgr import challenge_mgr
from apps.utils import utils
from apps.widgets.smartgrid.models import ActionMember, Activity, Category, Event, \
                                     Commitment, ConfirmationCode, TextPromptQuestion, \
                                     QuestionChoice, Level, Action, Filler, \
                                     EmailReminder, TextReminder
from apps.widgets.smartgrid.views import action_admin, action_admin_list

from django.contrib import admin
from django import forms
from django.forms.models import BaseInlineFormSet
from django.forms.util import ErrorList
from django.forms import TextInput, Textarea
from django.core.urlresolvers import reverse


class TextQuestionInlineFormSet(BaseInlineFormSet):
    """Custom formset model to override validation."""

    def clean(self):
        """Validates the form data and checks if the activity confirmation type is text."""

        # Form that represents the activity.
        activity = self.instance
        if not activity.pk:
            # If the activity is not saved, we don't care if this validates.
            return

        # Count the number of questions.
        count = 0
        for form in self.forms:
            try:
                if form.cleaned_data:
                    count += 1
            except AttributeError:
                pass

        if activity.confirm_type == "text" and count == 0:
            # Why did I do this?
            # activity.delete()
            raise forms.ValidationError(
                "At least one question is required if the activity's confirmation type is text.")

        elif activity.confirm_type != "text" and count > 0:
            # activity.delete()
            raise forms.ValidationError("Questions are not required for this confirmation type.")


class QuestionChoiceInline(admin.TabularInline):
    """Question Choice admin."""
    model = QuestionChoice
    fieldset = (
        (None, {
            'fields': ('question', 'choice'),
            'classes': ['wide', ],
            })
        )
    extra = 4


class TextQuestionInline(admin.TabularInline):
    """Text Question admin."""
    model = TextPromptQuestion
    fieldset = (
        (None, {
            'fields': ('question', 'answer'),
            })
        )
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2, 'cols': 70})},
        }

    extra = 1
    formset = TextQuestionInlineFormSet


class ActivityAdminForm(forms.ModelForm):
    """Activity Admin Form."""
    class Meta:
        """Meta"""
        model = Activity

    def clean_unlock_condition(self):
        """Validates the unlock conditions of the action."""
        data = self.cleaned_data["unlock_condition"]
        utils.validate_form_predicates(data)
        return data

    def clean(self):
        """
        Validates the admin form data based on a set of constraints.
            1.  If the verification type is "image" or "code", then a confirm prompt is required.
            2.  Publication date must be before expiration date.
            3.  Either points or a point range needs to be specified.
        """

        # Data that has passed validation.
        cleaned_data = self.cleaned_data

        #1 Check the verification type.
        confirm_type = cleaned_data.get("confirm_type")
        prompt = cleaned_data.get("confirm_prompt")
        if confirm_type != "text" and len(prompt) == 0:
            self._errors["confirm_prompt"] = ErrorList(
                [u"This confirmation type requires a confirmation prompt."])
            del cleaned_data["confirm_type"]
            del cleaned_data["confirm_prompt"]

        #2 Publication date must be before the expiration date.
        if "pub_date" in cleaned_data and "expire_date" in cleaned_data:
            pub_date = cleaned_data.get("pub_date")
            expire_date = cleaned_data.get("expire_date")

            if expire_date and pub_date >= expire_date:
                self._errors["expire_date"] = ErrorList(
                    [u"The expiration date must be after the pub date."])
                del cleaned_data["expire_date"]

        #3 Either points or a point range needs to be specified.
        points = cleaned_data.get("point_value")
        point_range_start = cleaned_data.get("point_range_start")
        point_range_end = cleaned_data.get("point_range_end")
        if not points and not (point_range_start or point_range_end):
            self._errors["point_value"] = ErrorList(
                [u"Either a point value or a range needs to be specified."])
            del cleaned_data["point_value"]
        elif points and (point_range_start or point_range_end):
            self._errors["point_value"] = ErrorList(
                [u"Please specify either a point_value or a range."])
            del cleaned_data["point_value"]
        elif not points:
            point_range_start = cleaned_data.get("point_range_start")
            point_range_end = cleaned_data.get("point_range_end")
            if not point_range_start:
                self._errors["point_range_start"] = ErrorList(
                    [u"Please specify a start value for the point range."])
                del cleaned_data["point_range_start"]
            elif not point_range_end:
                self._errors["point_range_end"] = ErrorList(
                    [u"Please specify a end value for the point range."])
                del cleaned_data["point_range_end"]
            elif point_range_start >= point_range_end:
                self._errors["point_range_start"] = ErrorList(
                    [u"The start value must be less than the end value."])
                del cleaned_data["point_range_start"]
                del cleaned_data["point_range_end"]

        return cleaned_data

    def save(self, *args, **kwargs):
        activity = super(ActivityAdminForm, self).save(*args, **kwargs)
        activity.type = "activity"
        activity.save()
        cache_mgr.clear()

        # If the activity's confirmation type is text, make sure to save the questions.
        if self.cleaned_data.get("confirm_type") == "text":
            self.save_m2m()

        return activity


class EventAdminForm(forms.ModelForm):
    """Event Admin Form."""
    num_codes = forms.IntegerField(required=False,
        label="Number of codes",
        help_text="Number of confirmation codes to generate",
        initial=0
    )

    def __init__(self, *args, **kwargs):
        """
        Override to change number of codes help text if we are editing an activity and add in a
        list of RSVPs.
        """
        super(EventAdminForm, self).__init__(*args, **kwargs)

        # Instance points to an instance of the model.
        # Check if it is created and if it has a code confirmation type.
        if self.instance and self.instance.type:
            url = reverse("activity_view_codes", args=(self.instance.type, self.instance.slug,))
            self.fields["num_codes"].help_text = "Number of additional codes to generate " \
                "<a href=\"%s\" target=\"_blank\">View codes</a>" % url

            url = reverse("activity_view_rsvps", args=(self.instance.type, self.instance.slug,))
            self.fields["event_max_seat"].help_text += \
                " <a href='%s' target='_blank'>View RSVPs</a>" % url

    class Meta:
        """Meta"""
        model = Event

    def clean_unlock_condition(self):
        """Validates the unlock conditions of the action."""
        data = self.cleaned_data["unlock_condition"]
        utils.validate_form_predicates(data)
        return data

    def clean(self):
        """
        Validates the admin form data based on a set of constraints.

            1.  Events must have an event date.
            2.  Publication date must be before expiration date.
        """

        # Data that has passed validation.
        cleaned_data = self.cleaned_data

        #1 Check that an event has an event date.
        event_date = cleaned_data.get("event_date")
        has_date = "event_date" in cleaned_data   # Check if this is in the data dict.
        if has_date and not event_date:
            self._errors["event_date"] = ErrorList([u"Events require an event date."])
            del cleaned_data["event_date"]

        #2 Publication date must be before the expiration date.
        if "pub_date" in cleaned_data and "expire_date" in cleaned_data:
            pub_date = cleaned_data.get("pub_date")
            expire_date = cleaned_data.get("expire_date")

            if expire_date and pub_date >= expire_date:
                self._errors["expire_date"] = ErrorList(
                    [u"The expiration date must be after the pub date."])
                del cleaned_data["expire_date"]

        return cleaned_data

    def save(self, *args, **kwargs):
        event = super(EventAdminForm, self).save(*args, **kwargs)
        if event.is_excursion:
            event.type = "excursion"
        else:
            event.type = "event"
        event.save()

        cache_mgr.clear()

        # Generate confirmation codes if needed.
        if self.cleaned_data.get("num_codes") > 0:
            ConfirmationCode.generate_codes_for_activity(event,
                self.cleaned_data.get("num_codes"))

        return event


class CommitmentAdminForm(forms.ModelForm):
    """admin form"""
    class Meta:
        """meta"""
        model = Commitment

    def clean_unlock_condition(self):
        """Validates the unlock conditions of the action."""
        data = self.cleaned_data["unlock_condition"]
        utils.validate_form_predicates(data)
        return data

    def save(self, *args, **kwargs):
        commitment = super(CommitmentAdminForm, self).save(*args, **kwargs)
        commitment.type = "commitment"
        commitment.save()
        cache_mgr.clear()

        return commitment


class FillerAdminForm(forms.ModelForm):
    """admin form"""
    class Meta:
        """meta"""
        model = Filler

    def save(self, *args, **kwargs):
        filler = super(FillerAdminForm, self).save(*args, **kwargs)
        filler.type = "filler"
        filler.unlock_condition = "False"
        filler.unlock_condition_text = "This cell is here only to fill out the grid. " \
                                       "There is no action associated with it."
        filler.save()
        cache_mgr.clear()

        return filler


class LevelAdminForm(forms.ModelForm):
    """admin form"""
    class Meta:
        """meta"""
        model = Level

    def clean_unlock_condition(self):
        """Validates the unlock conditions of the action."""
        data = self.cleaned_data["unlock_condition"]
        utils.validate_form_predicates(data)
        return data


class LevelAdmin(admin.ModelAdmin):
    """Level Admin"""
    list_display = ["name", "priority"]
    form = LevelAdminForm


admin.site.register(Level, LevelAdmin)
challenge_mgr.register_game_admin_model("smartgrid", Level)


class CategoryAdmin(admin.ModelAdmin):
    """Category Admin"""
    list_display = ["name", "priority"]
    prepopulated_fields = {"slug": ("name",)}

admin.site.register(Category, CategoryAdmin)
challenge_mgr.register_game_admin_model("smartgrid", Category)


def redirect_urls(model_admin, url_type):
    """change the url redirection."""
    from django.conf.urls import patterns, url
    from functools import update_wrapper

    def wrap(view):
        """wrap the view fuction."""
        def wrapper(*args, **kwargs):
            """return the wrapper."""
            return model_admin.admin_site.admin_view(view)(*args, **kwargs)
        return update_wrapper(wrapper, view)

    info = model_admin.model._meta.app_label, model_admin.model._meta.module_name

    urlpatterns = patterns('',
        url(r'^$',
            wrap(action_admin_list if url_type == "changelist" else model_admin.changelist_view),
            name='%s_%s_changelist' % info),
        url(r'^add/$',
            wrap(model_admin.add_view),
            name='%s_%s_add' % info),
        url(r'^(.+)/history/$',
            wrap(model_admin.history_view),
            name='%s_%s_history' % info),
        url(r'^(.+)/delete/$',
            wrap(model_admin.delete_view),
            name='%s_%s_delete' % info),
        url(r'^(.+)/$',
            wrap(action_admin if url_type == "change" else model_admin.change_view),
            name='%s_%s_change' % info),
    )
    return urlpatterns


class ActionAdmin(admin.ModelAdmin):
    """abstract admin for action."""
    actions = ["delete_selected", "increment_priority", "decrement_priority",
               "change_level", "change_category", "clear_level", "clear_category",
               "clear_level_category"]
    list_display = ["slug", "title", "level", "category", "priority", "type", "point_value"]
    search_fields = ["slug", "title"]
    list_filter = ["type", 'level', 'category']

    def delete_selected(self, request, queryset):
        """override the delete selected."""
        _ = request
        for obj in queryset:
            obj.delete()

    delete_selected.short_description = "Delete the selected objects."

    def increment_priority(self, request, queryset):
        """increment priority."""
        _ = request
        for obj in queryset:
            obj.priority += 1
            obj.save()

    increment_priority.short_description = "Increment selected objects' priority by 1."

    def decrement_priority(self, request, queryset):
        """decrement priority."""
        _ = request
        for obj in queryset:
            obj.priority -= 1
            obj.save()

    decrement_priority.short_description = "Decrement selected objects' priority by 1."

    def clear_level(self, request, queryset):
        """decrement priority."""
        _ = request
        for obj in queryset:
            obj.level = None
            obj.save()

    clear_level.short_description = "Set the level to (None)."

    def clear_category(self, request, queryset):
        """decrement priority."""
        _ = request
        for obj in queryset:
            obj.category = None
            obj.save()

    clear_category.short_description = "Set the category to (None)."

    def clear_level_category(self, request, queryset):
        """decrement priority."""
        _ = request
        for obj in queryset:
            obj.level = None
            obj.category = None
            obj.save()

    clear_level_category.short_description = "Set the level and category to (None)."

    def change_level(self, request, queryset):
        """change level."""
        action_type = queryset[0].type
        selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
        return HttpResponseRedirect(reverse("bulk_change", args=(action_type, "level",)) +
                                    "?ids=%s" % (",".join(selected)))

    change_level.short_description = "Change the level."

    def change_category(self, request, queryset):
        """change level."""
        action_type = queryset[0].type
        selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
        return HttpResponseRedirect(reverse("bulk_change", args=(action_type, "category",)) +
                                    "?ids=%s" % (",".join(selected)))

    change_category.short_description = "Change the category."

    def get_urls(self):
        return redirect_urls(self, "change")


class ActivityAdmin(admin.ModelAdmin):
    """Activity Admin"""
    fieldsets = (
        ("Basic Information",
         {'fields': (('name', ),
                     ('slug', 'related_resource'),
                     ('title', 'duration'),
                     'image',
                     'description',
                     ('video_id', 'video_source'),
                     'embedded_widget',
                     ('pub_date', 'expire_date'),
                     ('unlock_condition', 'unlock_condition_text'),
                     )}),
        ("Points",
         {"fields": (("point_value", "social_bonus"), ("point_range_start", "point_range_end"), )}),
        ("Ordering", {"fields": (("level", "category", "priority"), )}),
        ("Confirmation Type", {'fields': ('confirm_type', 'confirm_prompt')}),
    )
    prepopulated_fields = {"slug": ("name",)}

    form = ActivityAdminForm
    inlines = [TextQuestionInline]
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '80'})},
        }

    def get_urls(self):
        return redirect_urls(self, "changelist")


admin.site.register(Action, ActionAdmin)
challenge_mgr.register_game_admin_model("smartgrid", Action)

admin.site.register(Activity, ActivityAdmin)


class EventAdmin(admin.ModelAdmin):
    """Event Admin"""
    fieldsets = (
        ("Basic Information",
         {'fields': (('name', "is_excursion"),
                     ('slug', 'related_resource'),
                     ('title', 'duration'),
                     'image',
                     'description',
                     ('pub_date', 'expire_date'),
                     ('event_date', 'event_location', 'event_max_seat'),
                     ('unlock_condition', 'unlock_condition_text'),
                     )}),
        ("Points", {"fields": (("point_value", "social_bonus"),)}),
        ("Ordering", {"fields": (("level", "category", "priority"), )}),
        ("Confirmation Code", {'fields': ('num_codes',)}),
        )
    prepopulated_fields = {"slug": ("name",)}

    form = EventAdminForm

    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '80'})},
        }

    def get_urls(self):
        return redirect_urls(self, "changelist")


admin.site.register(Event, EventAdmin)


class CommitmentAdmin(admin.ModelAdmin):
    """Commitment Admin."""
    fieldsets = (
        ("Basic Information", {
            'fields': (('name', ),
                       ('slug', 'related_resource'),
                       ('title', 'duration'),
                       'image',
                       'description',
                       'unlock_condition', 'unlock_condition_text',
                       ),
            }),
        ("Points", {"fields": (("point_value", 'social_bonus'), )}),
        ("Ordering", {"fields": (("level", "category", "priority"), )}),
        )
    prepopulated_fields = {"slug": ("name",)}

    form = CommitmentAdminForm

    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '80'})},
        }

    def get_urls(self):
        """override the url definition."""
        return redirect_urls(self, "changelist")


admin.site.register(Commitment, CommitmentAdmin)


class FillerAdmin(admin.ModelAdmin):
    """Commitment Admin."""
    fieldsets = (
        ("Basic Information", {
            'fields': (('name', ),
                       ('slug', ),
                       ('title', ),
                       ),
            }),
        ("Ordering", {"fields": (("level", "category", "priority"), )}),
        )
    prepopulated_fields = {"slug": ("name",)}

    form = FillerAdminForm

    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '80'})},
        }

    def get_urls(self):
        """override the url definition."""
        return redirect_urls(self, "changelist")


admin.site.register(Filler, FillerAdmin)


class ActionMemberAdminForm(forms.ModelForm):
    """Activity Member admin."""
    def __init__(self, *args, **kwargs):
        """Override to dynamically change the form if the activity specifies a point range.."""

        super(ActionMemberAdminForm, self).__init__(*args, **kwargs)
        # Instance points to an instance of the model.
        member = self.instance
        if member and member.action and not member.action.point_value:
            action = member.action
            message = "Specify the number of points to award.  This value must be between %d and %d"
            message = message % (action.activity.point_range_start, action.activity.point_range_end)
            self.fields["points_awarded"].help_text = message

    class Meta:
        """Meta"""
        model = ActionMember

    def clean(self):
        """Custom validator that checks values for variable point activities."""

        # Data that has passed validation.
        cleaned_data = self.cleaned_data
        status = cleaned_data.get("approval_status")

        action = self.instance.action
        if status == "approved" and not action.point_value:
            # Check if the point value is filled in.
            if "points_awarded" not in cleaned_data:
                self._errors["points_awarded"] = ErrorList(
                    [u"This action requires that you specify the number of points to award."])

            # Check if the point value is valid.
            elif cleaned_data["points_awarded"] < action.activity.point_range_start or \
                 cleaned_data["points_awarded"] > action.activity.point_range_end:
                message = "The points to award must be between %d and %d" % (
                    action.activity.point_range_start, action.activity.point_range_end)
                self._errors["points_awarded"] = ErrorList([message])
                del cleaned_data["points_awarded"]

        return cleaned_data


class ActionMemberAdmin(admin.ModelAdmin):
    """ActionMember Admin."""
    radio_fields = {"approval_status": admin.HORIZONTAL}
    fields = (
        "user", "action", "admin_link", "question", "response", "image", "social_email",
        "approval_status", "admin_comment",)
    readonly_fields = (
        "user", "action", "admin_link", "question", "response", "social_email")
    list_display = (
        "action", "submission_date", "approval_status", "short_question", "short_response")
    list_filter = ["approval_status", "action__type"]
    actions = ["delete_selected"]
    date_hierarchy = "submission_date"
    ordering = ["submission_date"]

    form = ActionMemberAdminForm

    def short_question(self, obj):
        """return the short question."""
        return "%s" % (obj.question)

    short_question.short_description = 'Question'

    def short_response(self, obj):
        """return the short response"""
        return "%s %s" % (obj.response, obj.image)

    short_response.short_description = 'Response'

    def full_response(self, obj):
        """return the full response."""
        return "%s" % (obj.response).replace("\n", "<br/>")

    full_response.short_description = 'Response'
    full_response.allow_tags = True

    def changelist_view(self, request, extra_context=None):
        """
        Set the default filter of the admin view to pending.
        Based on iridescent's answer to
        http://stackoverflow.com/questions/851636/default-filter-in-django-admin
        """
        if 'HTTP_REFERER' in request.META and 'PATH_INFO' in request.META:
            test = request.META['HTTP_REFERER'].split(request.META['PATH_INFO'])
            if test[-1] and not test[-1].startswith('?'):
                if not 'approval_status__exact' in request.GET:
                    q = request.GET.copy()
                    q['approval_status__exact'] = 'pending'
                    request.GET = q
                    request.META['QUERY_STRING'] = request.GET.urlencode()
                if not 'action__type__exact' in request.GET:
                    q = request.GET.copy()
                    q['action__type__exact'] = 'activity'
                    request.GET = q
                    request.META['QUERY_STRING'] = request.GET.urlencode()

        return super(ActionMemberAdmin, self).changelist_view(request,
            extra_context=extra_context)

    def delete_selected(self, request, queryset):
        """override the delete selected."""
        _ = request
        for obj in queryset:
            obj.delete()

    delete_selected.short_description = "Delete the selected objects."

    def get_form(self, request, obj=None, **kwargs):
        """Override to remove the points_awarded field if the action
        does not have variable points."""
        if obj and not obj.action.point_value:
            self.fields = (
                "user", "action", "admin_link", "question", "response", "image", "social_email",
                "approval_status", "points_awarded", "admin_comment")
        else:
            if obj.action.type == "activity":
                self.fields = (
                    "user", "action", "admin_link", "question", "response", "image", "social_email",
                    "approval_status", "points_awarded", "admin_comment")
            else:
                self.fields = (
                        "user", "action", "admin_link", "social_email", "completion_date",
                        "approval_status")

        return super(ActionMemberAdmin, self).get_form(request, obj, **kwargs)

admin.site.register(ActionMember, ActionMemberAdmin)
challenge_mgr.register_game_admin_model("smartgrid", ActionMember)


class EmailReminderAdmin(admin.ModelAdmin):
    """reminder admin"""
    readonly_fields = ('user', 'action', 'sent')
    fields = ("send_at", "email_address", 'user', 'action', 'sent')
    list_display = ('send_at', 'user', 'email_address', 'sent')


class TextReminderAdmin(admin.ModelAdmin):
    """reminder admin"""
    readonly_fields = ('user', 'action', 'sent')
    fields = ("send_at", "text_number", 'user', 'action', 'sent')
    list_display = ('send_at', 'user', 'text_number', 'sent')


admin.site.register(EmailReminder, EmailReminderAdmin)
admin.site.register(TextReminder, TextReminderAdmin)
challenge_mgr.register_sys_admin_model("Notifications", EmailReminder)
challenge_mgr.register_sys_admin_model("Notifications", TextReminder)
