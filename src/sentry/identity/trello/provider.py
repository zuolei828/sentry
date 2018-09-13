from __future__ import absolute_import
from time import time
from sentry import options

from sentry.identity.base import Provider
from sentry.pipeline import PipelineView
from sentry.web.helpers import render_to_response
from sentry import http
from django import forms


def make_request(url):
    session = http.build_session()
    resp = session.get(
        url,
        verify=False
    )
    resp.raise_for_status()
    resp = resp.json()

    return resp


def get_api_key():
    return options.get('trello.api-key')


SCOPES = (
    'read',
    'write',
    'account',
)


class TrelloIdentityProvider(Provider):
    key = 'trello'
    name = 'Trello'

    auth_expiration_time = '1hour'
    application_name = 'Sentry Trello Integration'
    redirect_uri = '/extensions/trello/setup/'
    # &return_url={return_url}'
    authorize_url = 'https://trello.com/1/authorize?expiration={expiration}&name={app_name}&scope={scopes}&response_type=token&key={api_key}'
    scopes = SCOPES

    def get_pipeline_views(self):
        authorize_url = self.authorize_url.format(
            expiration=self.auth_expiration_time,
            app_name=self.application_name,
            scopes=','.join(self.scopes),
            api_key=get_api_key(),
            # return_url=absolute_uri(self.redirect_uri),
        )
        return [
            TrelloAuthorizationView(
                authorize_url=authorize_url,
            )
        ]

    def build_identity(self, data):
        user = data['user_info']

        return {
            'type': 'trello',
            'id': user['id'],
            'email': user['email'],
            'email_verified': True,
            'name': user['fullName'],
            'scopes': sorted(','.join(self.scopes)),
            'data': {
                'access_token': data['token'],
                'api_key': get_api_key(),
                'scopes': sorted(','.join(self.scopes)),
            },
        }


class TrelloAuthorizationView(PipelineView):
    def __init__(self, authorize_url, *args, **kwargs):
        super(TrelloAuthorizationView, self).__init__(*args, **kwargs)
        self.authorize_url = authorize_url

    def dispatch(self, request, pipeline):
        token = request.POST.get('token')
        if token is None:
            return render_to_response(
                template='sentry/integrations/trello-config.html',
                context={
                    'form': TrelloConfigurationForm(),
                    'auth_url': self.authorize_url,
                },
                request=request,
            )
        token_info = make_request(
            u'https://api.trello.com/1/tokens/%s?token=%s&key=%s' %
            (token, token, get_api_key()))
        for entity in token_info['permissions']:
            if entity['modelType'] == 'Member':
                user_info = make_request(u'https://api.trello.com/1/members/%s' % entity['idModel'])
                break
        data = {
            'access_token': token,
            'api_key': get_api_key(),
            'scopes': ','.join(SCOPES),
            'expiration': time() + 60 * 60 * 60,
        }
        pipeline.bind_state('data', data)
        pipeline.bind_state('token_info', token_info)
        pipeline.bind_state('user_info', user_info)
        return pipeline.next_step()


class TrelloConfigurationForm(forms.Form):
    token = forms.CharField()
