def get_web_app(test_mode: bool = False):
    if test_mode:
        from web_ui.test_app import app
        return app

    from .web_app import create_app

    return create_app()
