from django.db import models
from widgets.smartgrid.models import CommitmentMember, ActivityMember, Activity, Category, \
                                     Commitment, ConfirmationCode, TextPromptQuestion, \
                                     QuestionChoice
from django.contrib import admin
from django import forms
from django.forms.models import BaseInlineFormSet
from django.forms.util import ErrorList

from django.forms import TextInput, Textarea

from django.core.urlresolvers import reverse

### Commitment Admin
class CommitmentAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Basic Information", {
            'fields': ('name', 'slug', 'title', 'description', 'social_bonus', 'duration',
                       'depends_on', 'depends_on_text', 'energy_related', 'mobile_restricted',
                       ('is_canopy', 'is_group')),
            }),
        ("Points", {"fields": ("point_value",)}),
        ("Ordering", {"fields": ("priority", "category")}),
        )
    prepopulated_fields = {"slug": ("name",)}

    list_display = ["title", "category", "priority", ]

    actions = ["delete_selected", "increment_priority", "decrement_priority"]

    def delete_selected(self, request, queryset):
        _ = request
        for obj in queryset:
            obj.delete()

    delete_selected.short_description = "Delete the selected objects."

    def increment_priority(self, request, queryset):
        _ = request
        for obj in queryset:
            obj.priority += 1
            obj.save()

    increment_priority.short_description = "Increment selected objects' priority by 1."

    def decrement_priority(self, request, queryset):
        _ = request
        for obj in queryset:
            obj.priority -= 1
            obj.save()

    decrement_priority.short_description = "Decrement selected objects' priority by 1."

admin.site.register(Commitment, CommitmentAdmin)

# Category Admin
admin.site.register(Category)

class CommitmentMemberAdmin(admin.ModelAdmin):
    """Override to use custom delete method."""
    readonly_fields = ("social_email", "social_email2")
    actions = ["delete_selected"]

    def delete_selected(self, request, queryset):
        _ = request
        for obj in queryset:
            obj.delete()

    delete_selected.short_description = "Delete the selected objects."

admin.site.register(CommitmentMember, CommitmentMemberAdmin)

### Activity Admin
class ActivityAdminForm(forms.ModelForm):
    num_codes = forms.IntegerField(required=False,
        label="Number of codes",
        help_text="Number of confirmation codes to generate",
        initial=0
    )

    def __init__(self, *args, **kwargs):
        """
        Override to change number of codes help text if we are editing an activity and add in a list of RSVPs.
        """
        super(ActivityAdminForm, self).__init__(*args, **kwargs)
        # Instance points to an instance of the model.
        # Check if it is created and if it has a code confirmation type.
        if self.instance and self.instance.created_at and self.instance.confirm_type == "code":
            self.fields["num_codes"].help_text = "Number of additional codes to generate <a href=\""
            self.fields["num_codes"].help_text += reverse("widgets.smartgrid.views.view_codes",
                args=(self.instance.type, self.instance.slug,))
            self.fields["num_codes"].help_text += "\" target=\"_blank\">View codes</a>"

        if self.instance and self.instance.created_at and (
        self.instance.type == "event" or self.instance.type == "excursion"):
            url = reverse("widgets.smartgrid.views.view_rsvps",
                args=(self.instance.type, self.instance.slug,))
            self.fields[
            "event_max_seat"].help_text += " <a href='%s' target='_blank'>View RSVPs</a>" % url

    class Meta:
        model = Activity

    def clean(self):
        """
          Validates the admin form data based on a set of constraints.

          #1 Events must have an event date.
          #2 If the verification type is "image" or "code", then a confirm prompt is required.
          #3 If the verification type is "text", then additional questions are required
             (Handled in the formset class below).
          #4 Publication date must be before expiration date.
          #5 If the verification type is "code", then the number of codes is required.
          #6 Either points or a point range needs to be specified.
        """

        # Data that has passed validation.
        cleaned_data = self.cleaned_data

        #1 Check that an event has an event date.
        is_event = cleaned_data.get("type") == "event"
        event_date = cleaned_data.get("event_date")
        has_date = cleaned_data.has_key("event_date") #Check if this is in the data dict.
        if is_event and has_date and not event_date:
            self._errors["event_date"] = ErrorList([u"Events require an event date."])
            del cleaned_data["event_date"]

        #2 Check the verification type.
        confirm_type = cleaned_data.get("confirm_type")
        prompt = cleaned_data.get("confirm_prompt")
        if confirm_type != "text" and len(prompt) == 0:
            self._errors["confirm_prompt"] = ErrorList(
                [u"This confirmation type requires a confirmation prompt."])
            del cleaned_data["confirm_type"]
            del cleaned_data["confirm_prompt"]

        #4 Publication date must be before the expiration date.
        if cleaned_data.has_key("pub_date") and cleaned_data.has_key("expire_date"):
            pub_date = cleaned_data.get("pub_date")
            expire_date = cleaned_data.get("expire_date")

            if pub_date >= expire_date:
                self._errors["expire_date"] = ErrorList(
                    [u"The expiration date must be after the pub date."])
                del cleaned_data["expire_date"]

        #5 Number of codes is required if the verification type is "code"
        has_codes = cleaned_data.has_key("num_codes")
        num_codes = cleaned_data.get("num_codes")
        if not self.instance.created_at and confirm_type == "code" and has_codes and not num_codes:
            self._errors["num_codes"] = ErrorList(
                [u"The number of codes is required for this confirmation type."])
            del cleaned_data["num_codes"]

        #6 Either points or a point range needs to be specified.
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
        activity = super(forms.ModelForm, self).save(commit=False)

        activity.save()

        # If the activity's confirmation type is text, make sure to save the questions.
        if self.cleaned_data.get("confirm_type") == "text":
            self.save_m2m()

        # Generate confirmation codes if needed.
        elif self.cleaned_data.get("confirm_type") == "code" and self.cleaned_data.get(
            "num_codes") > 0:
            ConfirmationCode.generate_codes_for_activity(activity,
                self.cleaned_data.get("num_codes"))

        return activity


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
    model = QuestionChoice
    fieldset = (
        (None, {
            'fields': ('question', 'choice'),
            'classes': ['wide', ],
            })
        )
    extra = 4


class TextQuestionInline(admin.TabularInline):
    model = TextPromptQuestion
    fieldset = (
        (None, {
            'fields': ('question', 'answer'),
            'classes': ['wide', ],
            })
        )
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2, 'cols': 80})},
        }

    extra = 3
    formset = TextQuestionInlineFormSet


class ActivityAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Basic Information", {
            'fields': (
            'name', 'slug', 'type', 'title', 'description', 'duration', ('pub_date', 'expire_date'),
            ('event_date', 'event_max_seat', 'event_location'), ('depends_on', 'depends_on_text'),
            'energy_related', 'mobile_restricted', ('is_canopy', 'is_group')),
            }),
        ("Points",
             {"fields": ("point_value", 'social_bonus', ("point_range_start", "point_range_end",))})
        ,
        ("Ordering", {"fields": ("priority", "category")}),
        ("Confirmation Type", {'fields': ('confirm_type', 'num_codes', 'confirm_prompt')}),
        )
    prepopulated_fields = {"slug": ("name",)}
    form = ActivityAdminForm
    inlines = [TextQuestionInline, QuestionChoiceInline]

    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '100'})},
        }

    list_display = ["title", "type", "category", "priority", "pub_date", "event_date", "expire_date", ]

    actions = ["delete_selected", "increment_priority", "decrement_priority"]

    def delete_selected(self, request, queryset):
        _ = request
        for obj in queryset:
            obj.delete()

    delete_selected.short_description = "Delete the selected objects."

    def increment_priority(self, request, queryset):
        _ = request
        for obj in queryset:
            obj.priority += 1
            obj.save()

    increment_priority.short_description = "Increment selected objects' priority by 1."

    def decrement_priority(self, request, queryset):
        _ = request
        for obj in queryset:
            obj.priority -= 1
            obj.save()

    decrement_priority.short_description = "Decrement selected objects' priority by 1."

admin.site.register(Activity, ActivityAdmin)

### Activity Member admin.
class ActivityMemberAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        """Override to dynamically change the form if the activity specifies a point range.."""

        super(ActivityMemberAdminForm, self).__init__(*args, **kwargs)
        # Instance points to an instance of the model.
        member = self.instance
        if self.instance and member and member.activity.has_variable_points:
            activity = member.activity
            message = "Specify the number of points to award.  This value must be between %d and %d"
            message = message % (activity.point_range_start, activity.point_range_end)
            self.fields["points_awarded"].help_text = message

    class Meta:
        model = ActivityMember

    def clean(self):
        """Custom validator that checks values for variable point activities."""

        # Data that has passed validation.
        cleaned_data = self.cleaned_data
        status = cleaned_data.get("approval_status")

        activity = self.instance.activity
        if status == "approved" and activity.has_variable_points:
            # Check if the point value is filled in.
            if not cleaned_data.has_key("points_awarded"):
                self._errors["points_awarded"] = ErrorList(
                    [u"This activity requires that you specify the number of points to award."])

            # Check if the point value is valid.
            elif cleaned_data["points_awarded"] < activity.point_range_start or cleaned_data[
                                                                                "points_awarded"] > activity.point_range_end:
                message = "The points to award must be between %d and %d" % (
                activity.point_range_start, activity.point_range_end)
                self._errors["points_awarded"] = ErrorList([message])
                del cleaned_data["points_awarded"]
        elif status == "approved" and cleaned_data.has_key("points_awarded"):
            self._errors["points_awarded"] = ErrorList(
                [u"This field is only required for activities with variable point values."])
            del cleaned_data["points_awarded"]

        return cleaned_data


class ActivityMemberAdmin(admin.ModelAdmin):
    radio_fields = {"approval_status": admin.HORIZONTAL}
    fields = (
    "user", "activity", "question", "full_response", "image", "admin_comment", "approval_status",)
    readonly_fields = ("question", "full_response", "social_email", "social_email2",)
    list_display = (
    "activity", "submission_date", "approval_status", "short_question", "short_response")
    list_filter = ["approval_status", "activity__type"]
    actions = ["delete_selected"]
    date_hierarchy = "submission_date"
    ordering = ["submission_date"]

    form = ActivityMemberAdminForm

    def short_question(self, obj):
        return "%s" % (obj.question)

    short_question.short_description = 'Question'

    def short_response(self, obj):
        return "%s %s" % (obj.response, obj.image)

    short_response.short_description = 'Response'

    def full_response(self, obj):
        return "%s" % (obj.response).replace("\n", "<br/>")

    full_response.short_description = 'Response'
    full_response.allow_tags = True

    def changelist_view(self, request, extra_context=None):
        """
        Set the default filter of the admin view to pending.
        Based on iridescent's answer to http://stackoverflow.com/questions/851636/default-filter-in-django-admin
        """
        test = request.META['HTTP_REFERER'].split(request.META['PATH_INFO'])
        if test[-1] and not test[-1].startswith('?'):
            if not request.GET.has_key('approval_status__exact'):
                q = request.GET.copy()
                q['approval_status__exact'] = 'pending'
                q['activity__type__exact'] = 'activity'
                request.GET = q
                request.META['QUERY_STRING'] = request.GET.urlencode()
        return super(ActivityMemberAdmin, self).changelist_view(request,
            extra_context=extra_context)

    def delete_selected(self, request, queryset):
        _ = request
        for obj in queryset:
            obj.delete()

    delete_selected.short_description = "Delete the selected objects."

    def get_form(self, request, obj=None, **kwargs):
        """Override to remove the points_awarded field if the activity does not have variable points."""
        if obj and obj.activity.has_variable_points:
            self.fields = ("user", "activity", "question", "response", "image",
                           "admin_comment", "approval_status", "points_awarded", "social_email")
        else:
            self.fields = ("user", "activity", "question", "response", "image",
                           "admin_comment", "approval_status")

        return super(ActivityMemberAdmin, self).get_form(request, obj, **kwargs)

admin.site.register(ActivityMember, ActivityMemberAdmin)
