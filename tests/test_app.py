import os
import sqlite3
import tempfile
import unittest
import gc

from app import app, init_db


class FarmFinanceTests(unittest.TestCase):
    def setUp(self):
        self.original_cwd = os.getcwd()
        self.temp_dir = tempfile.TemporaryDirectory()
        os.chdir(self.temp_dir.name)
        app.config.update(TESTING=True, SECRET_KEY='test-secret')
        init_db()
        self.client = app.test_client()

    def tearDown(self):
        self.client = None
        os.chdir(self.original_cwd)
        gc.collect()
        self.temp_dir.cleanup()

    def register(self, username='farmer', password='secure-pass'):
        return self.client.post('/register', data={
            'username': username,
            'password': password,
        })

    def login(self, username='farmer', password='secure-pass'):
        return self.client.post('/login', data={
            'username': username,
            'password': password,
        })

    def test_clean_database_contains_complete_schema(self):
        with sqlite3.connect('users.db') as conn:
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        self.assertTrue({'users', 'tarlalar', 'seasons', 'gelirler', 'giderler', 'islemler'} <= tables)

    def test_registration_hashes_password_and_login_succeeds(self):
        self.register()
        with sqlite3.connect('users.db') as conn:
            stored = conn.execute(
                'SELECT password FROM users WHERE username = ?', ('farmer',)
            ).fetchone()[0]
        self.assertNotEqual(stored, 'secure-pass')
        response = self.login()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers['Location'].endswith('/index'))

    def test_short_password_is_rejected(self):
        self.register(password='short')
        with sqlite3.connect('users.db') as conn:
            count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        self.assertEqual(count, 0)

    def test_user_cannot_delete_another_users_field(self):
        self.register('owner', 'owner-pass')
        self.register('other', 'other-pass')
        with sqlite3.connect('users.db') as conn:
            owner_id = conn.execute(
                'SELECT id FROM users WHERE username = ?', ('owner',)
            ).fetchone()[0]
            field_id = conn.execute(
                'INSERT INTO tarlalar (user_id, name, size, parcel_no) VALUES (?, ?, ?, ?)',
                (owner_id, 'North Field', 10, 'P-1'),
            ).lastrowid
            conn.commit()

        self.login('other', 'other-pass')
        self.client.post(f'/tarla_sil/{field_id}')

        with sqlite3.connect('users.db') as conn:
            field = conn.execute(
                'SELECT id FROM tarlalar WHERE id = ?', (field_id,)
            ).fetchone()
        self.assertIsNotNone(field)


if __name__ == '__main__':
    unittest.main()
