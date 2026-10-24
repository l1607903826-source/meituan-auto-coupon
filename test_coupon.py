"""Synthetic responses only; every test forbids network sockets."""

import contextlib
import io
import os
import unittest
from unittest import mock
from urllib import error

import coupon


class CouponTests(unittest.TestCase):
    def setUp(self):
        socket_guard = mock.patch(
            "socket.socket", side_effect=AssertionError("Network forbidden in tests")
        )
        socket_guard.start()
        self.addCleanup(socket_guard.stop)

    def test_success_uses_expected_payload_and_only_counts_coupons(self):
        transport = mock.Mock(
            return_value={
                "code": 200,
                "data": {"couponList": [{"couponName": "untrusted content"}, {}]},
            }
        )
        result = coupon.claim("fake-token", transport)
        transport.assert_called_once_with(
            {"token": "fake-token", "aiScene": "", "version": 2}
        )
        self.assertEqual(result, coupon.Result("success", 2))
        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("untrusted content", coupon.summary_line(result))

    def test_expired_authorization_fails(self):
        result = coupon.claim("fake-token", lambda _: {"code": 401})
        self.assertEqual(result.status, "auth_failed")
        self.assertNotEqual(result.exit_code, 0)

    def test_empty_is_not_success(self):
        result = coupon.claim(
            "fake-token", lambda _: {"code": 200, "data": {"couponList": []}}
        )
        self.assertEqual(result.status, "empty")
        self.assertNotEqual(result.exit_code, 0)

    def test_missing_token_never_calls_transport(self):
        transport = mock.Mock()
        result = coupon.claim("  ", transport)
        transport.assert_not_called()
        self.assertEqual(result.status, "no_token")
        self.assertNotEqual(result.exit_code, 0)

    def test_already_received_is_completed(self):
        result = coupon.claim("fake-token", lambda _: {"code": 1014})
        self.assertEqual(result.status, "already_received")
        self.assertEqual(result.exit_code, 0)

    def test_api_failure_does_not_echo_message(self):
        result = coupon.claim(
            "fake-token", lambda _: {"code": 500, "msg": "private server content"}
        )
        self.assertEqual(result.status, "failed")
        self.assertNotEqual(result.exit_code, 0)
        self.assertNotIn("private", coupon.summary_line(result))

    def test_network_error_does_not_echo_exception(self):
        transport = mock.Mock(side_effect=error.URLError("fake-token private data"))
        result = coupon.claim("fake-token", transport)
        self.assertEqual(result.status, "error")
        self.assertNotEqual(result.exit_code, 0)
        self.assertNotIn("fake-token", coupon.summary_line(result))

    def test_malformed_response_fails(self):
        for response in (None, [], {}, {"code": 200}, {"code": 200, "data": []}):
            with self.subTest(response=response):
                self.assertNotEqual(coupon.interpret_response(response).exit_code, 0)

    def test_main_reports_nonzero_without_exposing_secret(self):
        with mock.patch.dict(
            os.environ, {"MEITUAN_TOKEN": "fake-token"}, clear=True
        ), mock.patch.object(
            coupon, "post_payload", return_value={"code": 401, "msg": "private data"}
        ), contextlib.redirect_stdout(io.StringIO()) as output:
            exit_code = coupon.main()
        self.assertNotEqual(exit_code, 0)
        self.assertIn("status=auth_failed", output.getvalue())
        self.assertNotIn("fake-token", output.getvalue())
        self.assertNotIn("private data", output.getvalue())


if __name__ == "__main__":
    unittest.main()
