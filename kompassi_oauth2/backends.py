from django.contrib.auth.models import User, Group
from django.conf import settings


def user_attrs_from_kompassi(kompassi_user):
    if settings.KOMPASSI_ACCESS_GROUP is not None:
        is_active = settings.KOMPASSI_ACCESS_GROUP in kompassi_user['groups']
    else:
        is_active = True

    return dict((django_key, accessor_func(kompassi_user)) for (django_key, accessor_func) in [
        ('username', lambda u: u['username']),
        ('email', lambda u: u['email']),
        ('first_name', lambda u: u['first_name']),
        ('last_name', lambda u: u['surname']),
        ('is_superuser', lambda u: settings.KOMPASSI_ADMIN_GROUP in u['groups']),
        ('is_staff', lambda u: settings.KOMPASSI_ADMIN_GROUP in u['groups']),
        ('is_active', lambda u: is_active),
        ('groups', lambda u: [Group.objects.get_or_create(name=group_name)[0] for group_name in u['groups']]),
    ])


class KompassiOAuth2AuthenticationBackend(object):
    def authenticate(self, oauth2_session=None, **kwargs):
        if oauth2_session is None:
            # Not ours (password login)
            return None

        response = oauth2_session.get(settings.KOMPASSI_API_V2_USER_INFO_URL)
        response.raise_for_status()
        kompassi_user = response.json()

        user, created = User.objects.get_or_create(username=kompassi_user['username'])

        user_attrs = user_attrs_from_kompassi(kompassi_user)
        groups = user_attrs.pop('groups', Group.objects.none())
        user.groups.set(groups)
        for key, value in user_attrs.items():
            setattr(user, key, value)
        user.save()

        if user.is_active:
            return user
        else:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesDotExist:
            return None
