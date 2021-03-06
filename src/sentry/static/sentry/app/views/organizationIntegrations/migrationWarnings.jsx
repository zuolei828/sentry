import PropTypes from 'prop-types';
import React from 'react';
import {groupBy} from 'lodash';

import {tct} from 'app/locale';
import AddIntegration from 'app/views/organizationIntegrations/addIntegration';
import AlertLink from 'app/components/alertLink';
import AsyncComponent from 'app/components/asyncComponent';

export default class MigrationWarnings extends AsyncComponent {
  static propTypes = {
    orgId: PropTypes.string.isRequired,
    providers: PropTypes.array.isRequired,
    onInstall: PropTypes.func.isRequired,
  };

  getEndpoints() {
    let {orgId} = this.props;

    return [['unmigratableRepos', `/organizations/${orgId}/repos/?status=unmigratable`]];
  }

  get unmigratableReposByOrg() {
    // Group by [GitHub|BitBucket|VSTS] Org name
    return groupBy(this.state.unmigratableRepos, repo => repo.name.split('/')[0]);
  }

  render() {
    return Object.entries(this.unmigratableReposByOrg).map(([orgName, repos]) => {
      // Repos use 'visualstudio', Integrations use 'vsts'. Normalize to 'vsts'.
      const key = repos[0].provider.id == 'visualstudio' ? 'vsts' : repos[0].provider.id;
      const provider = this.props.providers.find(p => p.key === key);

      // The Org might not have access to this Integration yet.
      if (!provider) {
        return '';
      }

      return (
        <AddIntegration
          key={provider.key}
          provider={provider}
          onInstall={this.props.onInstall}
        >
          {onClick => (
            <AlertLink onClick={onClick} href="#">
              {tct(
                "Your [orgName] repositories can't send commit data to Sentry. Add a [orgName] [providerName] instance here.",
                {
                  orgName,
                  providerName: provider.name,
                }
              )}
            </AlertLink>
          )}
        </AddIntegration>
      );
    });
  }
}
