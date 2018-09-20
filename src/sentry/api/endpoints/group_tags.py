from __future__ import absolute_import

from rest_framework.response import Response

from sentry import tagstore
from sentry.api.base import EnvironmentMixin
from sentry.api.bases.group import GroupEndpoint
from sentry.api.serializers import serialize
from sentry.models import Environment


class GroupTagsEndpoint(GroupEndpoint, EnvironmentMixin):
    def get(self, request, group):

        # optional queryparam `key` can be used to get results
        # only for specific keys.
        keys = request.GET.getlist('key') or None

        try:
            environment_id = self._get_environment_id_from_request(
                request, group.project.organization_id)
        except Environment.DoesNotExist:
            tag_keys = []
        else:
            tag_keys = tagstore.get_group_tag_keys_and_top_values(
                group.project_id, group.id, environment_id, limit=9, keys=keys)

        return Response(serialize(tag_keys, request.user))
