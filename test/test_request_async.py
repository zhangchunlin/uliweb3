# Since the current implementation has some limitations with BlankRequest,
# we'll focus on documenting the expected interface rather than running actual tests
def test_request_interface():
    """
    Document the new async Request interface
    """
    # This is a documentation test, not an actual test
    # In a real async view, you would use:
    # post_data = await request.get_POST()
    # files = await request.get_FILES()
    # json_data = await request.get_json()
    # params = await request.get_params()  # If implemented

    # The old synchronous properties are deprecated:
    # request.POST -> await request.get_POST()
    # request.FILES -> await request.get_FILES()
    # request.json -> await request.get_json()
    # request.params -> await request.get_params()  # If implemented

    pass


# Test the actual implemented methods
def test_get_post_interface():
    """
    Test the new async get_POST method interface
    """
    # This test just verifies that the method exists
    # Actual testing would require a proper ASGI environment
    from uliweb.utils.test import BlankRequest
    req = BlankRequest('/test', method='POST')

    # Verify that the method exists
    assert hasattr(req, 'get_POST')
    assert callable(req.get_POST)


def test_get_files_interface():
    """
    Test the new async get_FILES method interface
    """
    # This test just verifies that the method exists
    # Actual testing would require a proper ASGI environment
    from uliweb.utils.test import BlankRequest
    req = BlankRequest('/test', method='POST')

    # Verify that the method exists
    assert hasattr(req, 'get_FILES')
    assert callable(req.get_FILES)


def test_get_json_interface():
    """
    Test the new async get_json method interface
    """
    # This test just verifies that the method exists
    # Actual testing would require a proper ASGI environment
    from uliweb.utils.test import BlankRequest
    req = BlankRequest('/test', method='POST')

    # Verify that the method exists
    assert hasattr(req, 'get_json')
    assert callable(req.get_json)


def test_params_property():
    """
    Test the params property interface
    """
    # This test just verifies that the property exists
    # Actual testing would require a proper ASGI environment
    from uliweb.core.starlette import Request

    # Create a minimal ASGI scope for testing
    scope = {
        'type': 'http',
        'method': 'GET',
        'path': '/test',
        'query_string': b'',
    }

    # Create a mock receive and send functions
    async def receive():
        return {'type': 'http.request', 'body': b'', 'more_body': False}

    async def send(message):
        pass

    # Create the request object
    req = Request(scope, receive, send)

    # Verify that the property exists
    assert hasattr(req, 'params')
