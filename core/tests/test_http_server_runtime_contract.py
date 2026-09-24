import unittest

from krishna_core.http_server_runtime import KrishnaThreadingHTTPServer


class HTTPServerRuntimeContractTests(unittest.TestCase):
    def test_server_backlog_supports_dashboard_burst(self):
        self.assertGreaterEqual(KrishnaThreadingHTTPServer.request_queue_size, 64)

    def test_request_threads_do_not_block_runtime_shutdown(self):
        self.assertTrue(KrishnaThreadingHTTPServer.daemon_threads)
        self.assertTrue(KrishnaThreadingHTTPServer.allow_reuse_address)


if __name__ == "__main__":
    unittest.main()
