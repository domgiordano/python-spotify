import json
import traceback
import inspect
import asyncio

from lambdas.common.utility_helpers import build_successful_handler_response, build_error_handler_response
from lambdas.common.errors import ReleaseRadarError
from release_radar import release_radar_chron_job

HANDLER = 'release-radar'


def handler(event, context):
    try:

        # Monthly Wrapped Chron Job
        if 'body' not in event and event.get("source") == 'aws.events':
            users_downloaded = asyncio.run(release_radar_chron_job(event))
            return build_successful_handler_response({"usersDownloaded": users_downloaded}, False)

        else:
            raise Exception("Invalid Call: Must call from chron job.", 400)

    except Exception as err:
        message = err.args[0]
        function = f'handler.{__name__}'
        if len(err.args) > 1:
            function = err.args[1]
        print(traceback.print_exc())
        error = ReleaseRadarError(message, HANDLER, function) if 'Invalid User Input' not in message else ReleaseRadarError(message, HANDLER, function, 400)
        return build_error_handler_response(str(error))
