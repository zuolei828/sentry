from __future__ import absolute_import, print_function

import copy
import inspect
import logging
import raven
import six
import time

from django.conf import settings
from raven.contrib.django.client import DjangoClient
from raven.utils import get_auth_header
from sentry.utils.cache import memoize

from . import metrics

UNSAFE_FILES = ('sentry/event_manager.py', 'sentry/tasks/process_buffer.py', )


def is_current_event_safe():
    """
    Tests the current stack for unsafe locations that would likely cause
    recursion if an attempt to send to Sentry was made.
    """
    for _, filename, _, _, _, _ in inspect.stack():
        if filename.endswith(UNSAFE_FILES):
            return False
    return True


class SentryInternalClient(DjangoClient):
    request_factory = None

    @memoize
    def project_key(self):
        from django.db import IntegrityError
        from sentry.models import ProjectKey

        key = None
        try:
            if settings.SENTRY_PROJECT_KEY is not None:
                key = ProjectKey.objects.filter(
                    id=settings.SENTRY_PROJECT_KEY,
                    project=settings.SENTRY_PROJECT,
                ).first()
            if key is None and settings.SENTRY_PROJECT:
                key = ProjectKey.get_default(settings.SENTRY_PROJECT)
        except IntegrityError as exc:
            # if the relation fails to query or is missing completely, lets handle
            # it gracefully
            self.error_logger.warn('internal-error.unable-to-fetch-project', extra={
                'project_id': settings.SENTRY_PROJECT,
                'project_key': settings.SENTRY_PROJECT_KEY,
                'error_message': six.text_type(exc),
            })
        if key is None:
            self.error_logger.warn('internal-error.no-project-available', extra={
                'project_id': settings.SENTRY_PROJECT,
                'project_key': settings.SENTRY_PROJECT_KEY,
            })
        return key

    def is_enabled(self):
        if getattr(settings, 'DISABLE_RAVEN', False):
            return False
        return self.project_key is None

    def can_record_current_event(self):
        return self.remote.is_active() or is_current_event_safe()

    def capture(self, *args, **kwargs):
        if not self.can_record_current_event():
            metrics.incr('internal.uncaptured.events')
            self.error_logger.warn('internal-error.unsafe-stacktrace')
            return
        return super(SentryInternalClient, self).capture(*args, **kwargs)

    def send(self, **kwargs):
        # Report the issue to an upstream Sentry if active
        # NOTE: we don't want to check self.is_enabled() like normal, since
        # is_enabled behavior is overridden in this class. We explicitly
        # want to check if the remote is active.
        if self.remote.is_active():
            from sentry import options
            # Append some extra tags that are useful for remote reporting
            super_kwargs = copy.deepcopy(kwargs)
            super_kwargs['tags']['install-id'] = options.get('sentry:install-id')
            super(SentryInternalClient, self).send(**super_kwargs)

        key = self.project_key
        if key is None:
            return

        if not is_current_event_safe():
            return

        # These imports all need to be internal to this function as this class
        # is set up by django while still parsing LOGGING settings and we
        # cannot import this stuff until settings are finalized.
        from sentry.web.api import StoreView
        from django.test import RequestFactory

        client_string = 'raven-python/%s' % (raven.VERSION,)
        headers = {
            'HTTP_X_SENTRY_AUTH': get_auth_header(
                protocol=self.protocol_version,
                timestamp=time.time(),
                client=client_string,
                api_key=key.public_key,
                api_secret=key.secret_key,
            ),
            'HTTP_CONTENT_ENCODING': self.get_content_encoding(),
        }
        self.request_factory = self.request_factory or RequestFactory()
        request = self.request_factory.post(
            '/api/{}/store/'.format(key.project_id),
            data=self.encode(kwargs),
            content_type='application/octet-stream',
            **headers
        )
        StoreView.as_view()(
            request,
            project_id=six.text_type(key.project_id),
        )


class SentryInternalFilter(logging.Filter):
    def filter(self, record):
        # TODO(mattrobenolt): handle an upstream Sentry
        metrics.incr('internal.uncaptured.logs')
        return is_current_event_safe()
