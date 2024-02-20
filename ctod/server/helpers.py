from fastapi import Request


def get_extensions(request: Request) -> str:
    """Get the accept header from the request

    Returns:
        str: The accept header. Defaults to image/png
    """

    extensions = check_extensions(
        request, ["octvertexnormals", "watermask", "metadata"]
    )

    return extensions


def check_extensions(request: Request, extensions_to_check: list) -> dict:
    """Check the extensions in the accept header

    Args:
        extensions_to_check (list): list of extensions to check

    Returns:
        dict: extensions found in the accept header
    """

    accept_header = request.headers.get("Accept")
    content_types = accept_header.split(",")

    found_extensions = {}
    for extension in extensions_to_check:
        found_extensions[extension] = False

    for content_type in content_types:
        if "extensions=" in content_type:
            for part in content_type.split(";"):
                if "extensions=" in part:
                    extension = part.split("=")[1]
                    if extension in extensions_to_check:
                        found_extensions[extension] = True

    return found_extensions
