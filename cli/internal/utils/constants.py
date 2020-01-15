from cli.internal.utils.store import Store

LOG_PROTOCOL_TRACE = 4

AUTH = Store('auth', {
    'api_key': None,
    'id_token': None,
    'access_token': None
})
ENDPOINTS = Store('endpoints', {
    'client_id': 'QLWpUwYOOcLlAJsmyQhQMXyeWn6RZpoc',
    'auth_url': 'https://bymason.auth0.com/oauth/ro',
    'user_info_url': 'https://bymason.auth0.com/userinfo',
    'registry_artifact_url': 'https://platform.bymason.com/api/registry/artifacts',
    'registry_signed_url': 'https://platform.bymason.com/api/registry/signedurl',
    'builder_url': 'https://platform.bymason.com/api/tracker/builder',
    'deploy_url': 'https://platform.bymason.com/api/deploy',
    'xray_url': 'wss://api.bymason.com/v1/global/xray',
    'config_version': 1
})
