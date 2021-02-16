from typing import Dict

import urllib3
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *

# Disable insecure warnings
urllib3.disable_warnings()


def execute_query(client: Client, args: Dict) -> CommandResults:
    query = gql(args.get('query'))
    variables_names = argToList(args.get('variables_names', ''))
    variables_values = argToList(args.get('variables_values', ''))
    if len(variables_names) != len(variables_values):
        raise ValueError('The variable lists are not in the same length')
    variables = {name: value for name, value in zip(variables_names, variables_values)}
    result = client.execute(query, variable_values=variables)
    if (result_size := sys.getsizeof(result)) > (max_result_size := float(args.get('max_result_size', 10))) * 10000:
        raise ValueError(f'Result size {result_size / 10000} KBs is larger then max result size {max_result_size} KBs')
    command_results_args = {
        'readable_output': tableToMarkdown('GraphQL Query Results', result),
        'raw_response': result,
        'outputs': result if argToBoolean(args.get('populate_context_data')) else None,
        'outputs_prefix': 'GraphQL'
    }
    if args.get('outputs_key_field'):
        command_results_args['outputs_key_field'] = args.get('outputs_key_field')
    return CommandResults(**command_results_args)


def main() -> None:
    command = demisto.command()
    try:
        params = demisto.params()
        request_params = {
            'url': params.get('url'),
            'verify': not params.get('insecure', False),
            'retries': 3,
        }
        if credentials := params.get('credentials'):
            if (identifier := credentials.get('identifier', '')).startswith('_header:'):
                header_name = identifier.split('_header:')[1]
                header_value = credentials.get('password', '')
                request_params['headers'] = {header_name: header_value}
            else:
                request_params['auth'] = (identifier, credentials.get('password'))

        transport = RequestsHTTPTransport(**request_params)
        handle_proxy()
        client = Client(transport=transport, fetch_schema_from_transport=True)

        demisto.debug(f'Command being called is {command}')
        if command == 'test-module':
            return_results('ok')
        elif command == 'graphql-query':
            return_results(execute_query(client, demisto.args()))
        elif command == 'graphql-mutation':
            return_results(execute_query(client, demisto.args()))
    except Exception as e:
        demisto.error(traceback.format_exc())
        return_error(f'Failed to execute {command} command. Error: {str(e)}')


if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
