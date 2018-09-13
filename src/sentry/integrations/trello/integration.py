from __future__ import absolute_import

from django.utils.translation import ugettext as _
from django import forms

from sentry.integrations import Integration, IntegrationFeatures, IntegrationProvider, IntegrationMetadata

from sentry import http
from sentry.pipeline import NestedPipelineView
from sentry.identity.pipeline import IdentityProviderPipeline
from sentry.pipeline import PipelineView
from sentry.web.helpers import render_to_response
from sentry.utils.http import absolute_uri

DESCRIPTION = """
Fill me in
"""

metadata = IntegrationMetadata(
    description=DESCRIPTION.strip(),
    author='The Sentry Team',
    noun=_('Installation'),
    issue_url='https://github.com/getsentry/sentry/issues/new?title=Trello%20Integration:%20&labels=Component%3A%20Integrations',
    source_url='https://github.com/getsentry/sentry/tree/master/src/sentry/integrations/trello',
    aspects={},
)


class OrganizationsForm(forms.Form):
    def __init__(self, organizations, *args, **kwargs):
        super(OrganizationsForm, self).__init__(*args, **kwargs)
        self.fields['organization'] = forms.ChoiceField(
            choices=[(org['id'], org['displayName']) for org in organizations],
            label='Organization',
            help_text='Trello organization.',
        )


class OrganizationConfigView(PipelineView):
    def dispatch(self, request, pipeline):
        organization = request.POST.get('organization')
        if organization is None:
            identity = pipeline.fetch_state('identity')
            user_id = identity['user_info']['id']
            key = identity['data']['api_key']
            token = identity['data']['access_token']
            organizations = make_request(
                u'https://api.trello.com/1/members/%s/organizations?key=%s&token=%s' %
                (user_id, key, token))
            pipeline.bind_state('organizations', organizations)
            return render_to_response(
                template='sentry/integrations/trello-config.html',
                context={
                    'form': OrganizationsForm(organizations),
                    'auth_url': None,
                },
                request=request,
            )
        organizations = pipeline.fetch_state('organizations')
        organization = self.get_organization_from_id(organization, organizations)
        pipeline.bind_state('organization', organization)
        return pipeline.next_step()

    def get_organization_from_id(self, organization_id, organizations):
        for organization in organizations:
            if organization['id'] == organization_id:
                return organization
        return None


class TrelloIntegration(Integration):
    def get_client(self):
        pass


def make_request(self, url):
    session = http.build_session()
    resp = session.get(
        url,
        verify=False
    )
    resp.raise_for_status()
    resp = resp.json()

    return resp


class TrelloIntegrationProvider(IntegrationProvider):
    key = 'trello'
    name = 'Trello'
    metadata = metadata
    api_version = '1.0'
    integration_cls = TrelloIntegration
    redirect_url = '/extensions/vsts/setup/'
    features = frozenset([IntegrationFeatures.ISSUE_BASIC])
    setup_dialog_config = {
        'width': 600,
        'height': 800,
    }

    def get_pipeline_views(self):
        identity_pipeline_config = {
            'redirect_url': absolute_uri(self.redirect_url),
        }
        identity_pipeline_view = NestedPipelineView(
            bind_key='identity',
            provider_key=self.key,
            pipeline_cls=IdentityProviderPipeline,
            config=identity_pipeline_config,
        )
        return [
            identity_pipeline_view,
            OrganizationConfigView,
        ]

    def build_integration(self, state):
        user = state['identity']['user_info']
        organization = state['organization']
        scopes = state['identity']['scopes']

        return {
            'name': organization['displayName'],
            'external_id': organization['id'],
            'metadata': {
                'domain_name': organization['url'],
                'scopes': scopes,
            },
            'user_identity': {
                'type': 'trello',
                'external_id': user['id'],
                'scopes': scopes,
                'data': state['identity']['data'],
            },
        }
