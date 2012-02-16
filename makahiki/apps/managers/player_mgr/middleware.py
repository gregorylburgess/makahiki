"""
This middleware tracks how many days in a row the user has come to the site.
"""

import datetime

class LoginTrackingMiddleware(object):
    """
    This middleware tracks how many days in a row the user has come to the site.
    """

    def process_request(self, request):
        """Checks if the user is logged in and updates the tracking field."""
        user = request.user
        if user.is_authenticated():
            profile = request.user.get_profile()
            last_visit = request.user.get_profile().last_visit_date
            today = datetime.date.today()

            # Look for a previous login.
            if last_visit and (today - last_visit) == datetime.timedelta(
                days=1):
                profile.last_visit_date = today
                profile.daily_visit_count += 1
                profile.save()
            elif not last_visit or (today - last_visit) > datetime.timedelta(
                days=1):
                # Reset the daily login count.
                profile.last_visit_date = today
                profile.daily_visit_count = 1
                profile.save()

        return None
