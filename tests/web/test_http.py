"""Real HTTP requests to server.py running in a background thread (standard library only)."""
import http.client
import http.server
import threading
import unittest
import urllib.parse

import db
import server
from tests.support import day, use_temp_db


class WebServer(unittest.TestCase):
    def setUp(self):
        use_temp_db(self)
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.port = self.httpd.server_address[1]
        self.host = f"127.0.0.1:{self.port}"
        old_hosts = server.ALLOWED_HOSTS
        server.ALLOWED_HOSTS = [self.host]
        thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        thread.start()

        def stop():
            self.httpd.shutdown()
            self.httpd.server_close()
            server.ALLOWED_HOSTS = old_hosts

        self.addCleanup(stop)

    def request(self, method, path, fields=None, headers=None, cookie="", raw_body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        all_headers = {"Host": self.host}
        if cookie != "":
            all_headers["Cookie"] = cookie
        body = raw_body
        if fields is not None:
            body = urllib.parse.urlencode(fields, doseq=True)
            all_headers["Content-Type"] = "application/x-www-form-urlencoded"
        if headers is not None:
            all_headers.update(headers)
        conn.request(method, path, body=body, headers=all_headers)
        response = conn.getresponse()
        text = response.read().decode("utf-8", errors="replace")
        conn.close()
        return response, text

    def sign_up_and_set_up(self, username="alice", activities=None):
        if activities is None:
            activities = ["Gym", "Yoga"]
        response, text = self.request("POST", "/signup",
                                      {"username": username, "password": "password-123"})
        cookie = response.getheader("Set-Cookie").split(";")[0]
        self.request("POST", "/setup", {"name": username.title(), "gender": "female", "age": "30",
                                        "height": "165", "weight": "60", "activities": activities,
                                        "weekly_goal": "3"}, cookie=cookie)
        return cookie

    def log(self, cookie, **fields):
        base = {"choice": "Yoga|Relax", "date": day(0), "exercise": "Cat-Cow", "duration": "20"}
        base.update(fields)
        return self.request("POST", "/log", base, cookie=cookie)

    # Logging in

    def test_pages_need_login(self):
        for path in ["/", "/log", "/setup", "/log?choice=Gym%7CUpper+Body"]:
            response, text = self.request("GET", path)
            self.assertEqual(response.status, 303, path)
            self.assertEqual(response.getheader("Location"), "/login")

    def test_signup_goes_to_setup_then_dashboard(self):
        response, text = self.request("POST", "/signup", {"username": "alice", "password": "password-123"})
        self.assertEqual(response.status, 303)
        cookie = response.getheader("Set-Cookie")
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertNotIn("Secure", cookie)
        session = cookie.split(";")[0]
        self.assertEqual(self.request("GET", "/", cookie=session)[0].getheader("Location"), "/setup")
        cookie = self.sign_up_and_set_up("bob")
        response, text = self.request("GET", "/", cookie=cookie)
        self.assertEqual(response.status, 200)
        self.assertIn("Hi Bob", text)

    def test_cookie_is_secure_behind_https_proxy(self):
        response, text = self.request("POST", "/signup", {"username": "alice", "password": "password-123"},
                                      headers={"X-Forwarded-Proto": "https"})
        self.assertIn("Secure", response.getheader("Set-Cookie"))

    def test_logout_ends_the_session(self):
        cookie = self.sign_up_and_set_up()
        response, text = self.request("POST", "/logout", {}, cookie=cookie)
        self.assertEqual(response.getheader("Location"), "/login")
        self.assertIn("Max-Age=0", response.getheader("Set-Cookie"))
        self.assertEqual(self.request("GET", "/", cookie=cookie)[0].status, 303)

    def test_forged_session_cookie(self):
        response, text = self.request("GET", "/", cookie="session=made-up-token")
        self.assertEqual(response.getheader("Location"), "/login")

    def test_login_page_redirects_when_logged_in(self):
        cookie = self.sign_up_and_set_up()
        self.assertEqual(self.request("GET", "/login", cookie=cookie)[0].getheader("Location"), "/")

    def test_wrong_password_shows_form_again(self):
        self.sign_up_and_set_up()
        response, text = self.request("POST", "/login", {"username": "alice", "password": "wrong-one"})
        self.assertEqual(response.status, 200)
        self.assertIn("Wrong username or password.", text)
        self.assertIsNone(response.getheader("Set-Cookie"))

    # Each account sees only its own data

    def test_accounts_are_separate(self):
        alice = self.sign_up_and_set_up("alice")
        bob = self.sign_up_and_set_up("bob")
        response, text = self.log(alice)
        saved = response.getheader("Location")
        self.assertTrue(saved.startswith("/?saved="))
        self.assertIn("Cat-Cow", self.request("GET", "/", cookie=alice)[1])
        bob_page = self.request("GET", saved, cookie=bob)[1]
        self.assertNotIn("Cat-Cow", bob_page)
        self.assertNotIn("Saved workout", bob_page)

    def test_cannot_log_an_activity_outside_the_profile(self):
        cookie = self.sign_up_and_set_up(activities=["Yoga"])
        response, text = self.log(cookie, choice="Gym|Upper Body", exercise="Pull Up")
        self.assertEqual(response.status, 200)
        self.assertIn("Pick an activity", text)

    # Security

    def test_security_headers(self):
        response, text = self.request("GET", "/login")
        csp = response.getheader("Content-Security-Policy")
        self.assertIn("default-src 'none'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertEqual(response.getheader("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.getheader("Cache-Control"), "no-store")

    def test_unknown_host_is_refused(self):
        response, text = self.request("GET", "/login", headers={"Host": "evil.example"})
        self.assertEqual(response.status, 400)

    def test_cross_site_post_is_refused(self):
        cookie = self.sign_up_and_set_up()
        response, text = self.request("POST", "/log", {"choice": "Yoga|Relax", "date": day(0),
                                                       "exercise": "Cat-Cow", "duration": "20"},
                                      cookie=cookie, headers={"Origin": "https://evil.example"})
        self.assertEqual(response.status, 403)
        response, text = self.request("POST", "/login", {"username": "alice", "password": "password-123"},
                                      headers={"Origin": "https://evil.example"})
        self.assertEqual(response.status, 403)
        self.assertEqual(db.load_all(2)["logs"], [])

    def test_same_site_post_is_allowed(self):
        cookie = self.sign_up_and_set_up()
        response, text = self.request("POST", "/log", {"choice": "Yoga|Relax", "date": day(0),
                                                       "exercise": "Cat-Cow", "duration": "20"},
                                      cookie=cookie, headers={"Origin": f"http://{self.host}"})
        self.assertEqual(response.status, 303)

    def test_oversized_and_broken_requests(self):
        cookie = self.sign_up_and_set_up()
        too_big = self.request("POST", "/log", raw_body="x" * 20000, cookie=cookie)[0]
        self.assertEqual(too_big.status, 413)
        broken = self.request("POST", "/log", raw_body=b"choice=Yoga%7CRelax&exercise=\xff\xfe",
                              cookie=cookie)[0]
        self.assertEqual(broken.status, 200)

    def test_saved_message_cannot_be_made_up(self):
        cookie = self.sign_up_and_set_up()
        text = self.request("GET", "/?saved=%3Cb%3Ehacked", cookie=cookie)[1]
        self.assertNotIn("hacked", text)
        location = self.log(cookie)[0].getheader("Location")
        self.assertIn("Saved workout #", self.request("GET", location, cookie=cookie)[1])

    def test_unknown_page(self):
        cookie = self.sign_up_and_set_up()
        self.assertEqual(self.request("GET", "/admin", cookie=cookie)[0].status, 404)

    # Day page

    def test_day_page_and_bad_dates(self):
        cookie = self.sign_up_and_set_up()
        self.log(cookie, date=day(-1))
        response, text = self.request("GET", f"/day?date={day(-1)}", cookie=cookie)
        self.assertEqual(response.status, 200)
        self.assertIn("Cat-Cow", text)
        for bad in [day(1), "yesterday", "2026-02-30", ""]:
            response, text = self.request("GET", "/day?date=" + bad, cookie=cookie)
            self.assertEqual(response.status, 303, bad)
            self.assertEqual(response.getheader("Location"), "/")

    def test_log_for_a_chosen_day(self):
        cookie = self.sign_up_and_set_up()
        text = self.request("GET", f"/log?date={day(-4)}", cookie=cookie)[1]
        self.assertIn(f"name='date' value='{day(-4)}'", text)
        text = self.request("GET", f"/log?choice=Yoga%7CRelax&date={day(-4)}", cookie=cookie)[1]
        self.assertIn(f"id='date' type='date' name='date' value='{day(-4)}'", text)
        text = self.request("GET", f"/log?choice=Yoga%7CRelax&date={day(3)}", cookie=cookie)[1]
        self.assertIn(f"id='date' type='date' name='date' value='{day(0)}'", text)

    # Calendar

    def test_calendar_page_and_bad_months(self):
        cookie = self.sign_up_and_set_up()
        self.log(cookie, date=day(0))
        response, text = self.request("GET", "/calendar", cookie=cookie)
        self.assertEqual(response.status, 200)
        self.assertIn("<b>Yoga</b>", text)
        self.assertEqual(self.request("GET", "/calendar?month=2024-02", cookie=cookie)[0].status, 200)
        for bad in ["2999-01", "nope", "2026-00", "<script>"]:
            response, text = self.request("GET", "/calendar?month=" + urllib.parse.quote(bad),
                                          cookie=cookie)
            self.assertEqual(response.status, 303, bad)
            self.assertEqual(response.getheader("Location"), "/calendar")
        self.assertEqual(self.request("GET", "/calendar")[0].getheader("Location"), "/login")

    # Theme

    def test_theme_is_remembered_and_redirect_stays_on_site(self):
        response, text = self.request("GET", "/theme?set=dark",
                                      headers={"Referer": f"http://{self.host}/login"})
        self.assertEqual(response.getheader("Location"), "/login")
        cookie = response.getheader("Set-Cookie").split(";")[0]
        self.assertEqual(cookie, "theme=dark")
        self.assertIn("data-theme='dark'", self.request("GET", "/login", cookie=cookie)[1])
        evil = self.request("GET", "/theme?set=light", headers={"Referer": "https://evil.example/x"})[0]
        self.assertEqual(evil.getheader("Location"), "/")

    def test_halloween_theme(self):
        response = self.request("GET", "/theme?set=halloween")[0]
        cookie = response.getheader("Set-Cookie").split(";")[0]
        self.assertEqual(cookie, "theme=halloween")
        text = self.request("GET", "/login", cookie=cookie)[1]
        self.assertIn("data-theme='halloween'", text)
        self.assertIn("href='/theme?set=halloween'", text)

    def test_bad_theme_values_fall_back_to_auto(self):
        self.assertIn("theme=auto", self.request("GET", "/theme?set=%3Cx%3E")[0].getheader("Set-Cookie"))
        text = self.request("GET", "/login", cookie='theme="><x')[1]
        self.assertIn("data-theme='auto'", text)


if __name__ == "__main__":
    unittest.main()
