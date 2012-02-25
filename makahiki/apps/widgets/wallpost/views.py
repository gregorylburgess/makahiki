from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.template.context import RequestContext
from django.template.loader import render_to_string
from managers.team_mgr.models import Post
from widgets.news.forms import WallForm
import simplejson as json

# Number of posts to load at a time.
DEFAULT_POST_COUNT = 10

def supply(request, page_name):
    user = request.user
    team = user.get_profile().team


    if page_name == "energy":
        if request.GET.has_key("last_post"):
            posts = Post.objects.filter(
                        team=team,
                        style_class="user_post",
                        id__lt=int(request.GET["last_post"])).select_related(
                            'user__profile').order_by("-id")
        else:
            posts = Post.objects.filter(team=team, style_class="user_post").select_related(
                'user__profile').order_by("-id")

        title = "Organize with your team peeps"
        description = "Got ideas on how to conserve energy? Share it with your team:"
    else:
        if request.GET.has_key("last_post"):
            posts = Post.objects.filter(
                        team=team,
                        id__lt=int(request.GET["last_post"])).select_related(
                            'user__profile').order_by("-id")
        else:
            posts = Post.objects.filter(team=team).select_related('user__profile').order_by("-id")

        title = "News Feed"
        description = ""

    post_count = posts.count()
    posts = posts[:DEFAULT_POST_COUNT]
    is_more_posts = True if post_count > DEFAULT_POST_COUNT else False

    return {
        "page_name": page_name,
        "title": title,
        "description": description,
        "posts": posts,
        "more_posts": is_more_posts,
        "wall_form": WallForm(),
        }

@login_required
def post(request):
    if request.is_ajax() and request.method == "POST":
        form = WallForm(request.POST)
        if form.is_valid():
            wall_post = Post(
                user=request.user,
                team=request.user.get_profile().team,
                text=form.cleaned_data["post"]
            )
            wall_post.save()

            # Render the post and send it as a response.
            template = render_to_string("user_post.html", {"post": wall_post},
                context_instance=RequestContext(request))
            return HttpResponse(json.dumps({
                "contents": template,
                }), mimetype="application/json")

        # At this point there is a form validation error.
        return HttpResponse(json.dumps({
            "message": "This should not be blank."
        }), mimetype="application/json")

    raise Http404


@login_required
def more_posts(request):
    if request.is_ajax():
        view_objects = {}
        view_objects["wallpost"] = supply(request, request.GET["page_name"])
        template = render_to_string("news_posts.html", {
            "view_objects": view_objects,
            }, context_instance=RequestContext(request))

        return HttpResponse(json.dumps({
            "contents": template,
            }), mimetype='application/json')

    raise Http404