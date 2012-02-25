import re

from django import forms
from django.contrib.localflavor.us.forms import USPhoneNumberField

from managers.player_mgr.models import Profile
from widgets.smartgrid.models import TextReminder

class ProfileForm(forms.Form):
    def __init__(self, *args, **kwargs):
        """
        Override for init to take a user argument.
        """
        self.user = kwargs.pop('user', None)
        super(ProfileForm, self).__init__(*args, **kwargs)

    display_name = forms.CharField(required=True, max_length=20, min_length=1)

    # Event notifications
    contact_email = forms.EmailField(required=False)
    contact_text = USPhoneNumberField(required=False, widget=forms.TextInput(attrs={
        "style": "width: 100px",
        }))
    contact_carrier = forms.ChoiceField(choices=TextReminder.TEXT_CARRIERS)


    def clean_display_name(self):
        """
        Check if this profile name is valid
        """
        name = self.cleaned_data['display_name'].strip()
        # Remove extra whitespace from the name.
        spaces = re.compile(r'\s+')
        name = spaces.sub(' ', name)

        # Check for name that is just whitespace.
        if name == '':
            raise forms.ValidationError('This field is required')

        # Check for duplicate name
        if Profile.objects.exclude(user=self.user).filter(name=name).count() > 0:
            raise forms.ValidationError("%s is taken.  Please use another name.")

        return name

  
