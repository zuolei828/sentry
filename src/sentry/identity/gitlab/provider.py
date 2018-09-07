from __future__ import absolute_import

# from sentry.identity.base import Provider
# from uuid import uuid4


# class GitlabIdentityProvider(OAuth2Provider):
#     key = 'gitlab'
#     name = 'Gitlab'

#     # TODO(epurkhiser): This identity provider is actually used for authorizing
#     # the Slack application through their Workspace Token OAuth flow, not a
#     # standard user access token flow.
#     oauth_access_token_url = 'https://slack.com/api/oauth.token'
#     oauth_authorize_url = 'https://slack.com/oauth/authorize'

#     oauth_scopes = (
#         'identity.basic',
#         'identity.email',
#     )

#     def get_oauth_client_id(self):
#         return options.get('gitlab.client-id')

#     def build_identity(self, data):
#         data = data['data']

#         return {
#             'type': 'gitlab',
#             'id': data['user']['id'],
#             'email': data['user']['email'],
#             'scopes': sorted(data['scope'].split(',')),
#             'data': self.get_oauth_data(data),
#         }


# class OauthView(PipelineView):
#     oauth_token_url = u'{domain_name}/oauth/token'
#     oauth_code_url = u'{base_url}oauth/authorize?client_id={client_id}&redirect_uri={redirect_url}&response_type=code&state={state}'

#     def dispatch(self, request, pipeline):
#         domain_name = pipeline.fetch_state(key='domain_name')
#         state = self.generate_state()
#         pipeline.bind_state('state', state)
#         code = self.request_oauth_code(domain_name)
#         token = self.request_oauth_token(domain_name, code)

#     def request_oauth_code(self, domain_name):
#         session = http.build_session()

#         resp = session.get(
#             self.oauth_code_url.format(
#                 base_url=domain_name,
#                 client_id=self.get_oauth_client_id,
#                 redirect_url=self.redirect_uri,
#                 state=state,
#             ),
#             headers={
#                 'Accept': 'application/json',
#             },
#         )
#         resp.raise_for_status()
#         return resp.json()

#     def request_oauth_token(self, domain_name, code):
#         session = http.build_session()
#         resp = session.post(
#             self.oauth_token_url.format(
#                 base_url=domain_name,
#             ),
#             body={

#                 'client_id': self.get_oauth_client_id(),
#                 'client_secret': self.get_oauth_client_secret(),
#                 'redirect_uri': self.redirect_uri,
#                 'code': code,
#                 'grant_type': 'authorization_code',
#             },
#             headers={
#                 'Accept': 'application/json',
#             },
#         )
#         resp.raise_for_status()
#         return resp.json()

#     def generate_state(self):
#         return uuid4().hex + uuid4().hex


# class AccountConfigView(PipelineView):
#     def dispatch(self, request, pipeline):
#         if 'domain_name' in request.POST:
#             account_id = request.POST['domain_name']
#             pipeline.bind_state('account', account)
#             return pipeline.next_step()

#         return render_to_response(
#             template='sentry/integrations/vsts-config.html',
#             context={
#                 'form': AccountForm(),
#             },
#             request=request,
#         )


# class AccountForm(forms.Form):
#     domain_name = forms.CharField()


# class BitbucketLoginView(PipelineView):

#     def dispatch(self, request, pipeline):
#         jwt = request.GET.get('jwt')
#         if jwt is None:
#             return self.redirect(
#                 'https://bitbucket.org/site/addons/authorize?descriptor_uri=%s' % (
#                     absolute_uri('/extensions/bitbucket/descriptor/'),
#                 ))
#         return pipeline.next_step()
