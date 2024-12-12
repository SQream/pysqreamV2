
def pytest_addoption(parser):
    parser.addoption("--domain", action="store", help="Blue Domain ip", required=True)
    parser.addoption("--access_token", action="store", help="Blue Access token", required=True)
    parser.addoption("--use_logs", action="store_true", help="use logs", default=False)
    parser.addoption("--log_path", action="store", help="path of logs", default=None)
    parser.addoption("--log_level", action="store", help="log level", default='INFO')


def pytest_generate_tests(metafunc):
    metafunc.config.getoption("domain")
    metafunc.config.getoption("access_token")
