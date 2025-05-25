import webbrowser
from plexapi.myplex import MyPlexAccount, MyPlexPinLogin

def login_to_plex(timeout: int = 120) -> object:
    """
    Log in to Plex via pin and return a connected server instance.

    Args:
        timeout (int): Maximum time to wait for login (seconds). Default is 120.

    Returns:
        object: Connected Plex server instance (plexapi.server.PlexServer).

    Raises:
        Exception: If login fails or no server is available.
    """
    """
    Log in to Plex via pin and return a connected server instance.
    """
    headers = {'X-Plex-Client-Identifier': 'unique_client_identifier'}
    pinlogin = MyPlexPinLogin(headers=headers, oauth=True)
    webbrowser.open(pinlogin.oauthUrl())
    pinlogin.run(timeout=timeout)
    pinlogin.waitForLogin()
    if not pinlogin.token:
        raise Exception("Plex login failed.")
    account = MyPlexAccount(token=pinlogin.token)
    # Select first available server
    resources = [r for r in account.resources() if r.provides == 'server' and r.connections]
    if not resources:
        raise Exception("No Plex servers available.")
    server = account.resource(resources[0].name).connect()
    return server

def get_playlists(server: object) -> list:
    """
    Retrieve all playlists from the Plex server.

    Args:
        server (object): Connected Plex server instance.

    Returns:
        list: List of Plex playlist objects.

    Raises:
        Exception: If playlist retrieval fails.
    """
    """
    Retrieve all playlists from the Plex server.
    """
    try:
        return server.playlists()
    except Exception as e:
        raise Exception(f"Failed to fetch playlists: {e}")
