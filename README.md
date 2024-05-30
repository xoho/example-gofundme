# Example Funding website

This is an example funding website like GoFundMe. Instead of actually receiving funds, which this can be modified
to do, it automatically randomly adjusts funding for funding projects with random users.

This was used for a technology demonstration.

** Tech used

 * Flask
 * WeedFs (distributed object store like S3)
 * PyDantic for model validation
 * Celery for task management


## Update algorithm

On each access of a post either directly or view the group view page (eg: search, latest, my campaigns)
the contributions are updated based on the last updated time.  The algo breaks the time since last
updated into chunks of random sizes based on the update time period (minutes) - see UPDATE_TIME_PERIOD_IN_MINUTES
in config.py. A higher value for UPDATE_TIME_PERIOD_IN_MINUTES results in less updates for the campaign. For each
of the time chunks, a random number of contribution updates are chosen based on the total goal for the campaign
divided by DIVISOR_UPDATES_PER_TIME_PERIOD in config.py. A higher value for DIVISOR_UPDATES_PER_TIME_PERIOD results
in less updates for the campaign. For each of the contribution updates, a random amount is chosen from the donation
distribution list found in donation_distribution.json.  Additionally, each chunk may or may not get a message pulled
from the comment_bank.json and may get a generated comment author or the author Anonymous.

The code for this is found in routes.py > populate_contributions.

The update amount for a campaign can also be artificially inflated by manually changing the last_contribution_datetime
field in the campagin's data.json file.