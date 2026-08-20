import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from backend.app import create_app


class TestFoodLabAPI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)

        class TestConfig:
            SECRET_KEY = "test-secret"
            DATABASE_PATH = str(base / "foodlab.sqlite3")
            UPLOAD_FOLDER = str(base / "uploads")
            MAX_CONTENT_LENGTH = 8 * 1024 * 1024
            SESSION_COOKIE_HTTPONLY = True
            SESSION_COOKIE_SAMESITE = "Lax"
            SESSION_COOKIE_SECURE = False

        self.app = create_app(TestConfig)
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def csrf(self):
        return self.client.get("/api/auth/csrf").get_json()["csrf_token"]

    def register(self, username="alice"):
        response = self.client.post("/api/auth/register", json={"username": username, "email": f"{username}@example.com", "password": "secret1"})
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def test_public_browse_and_search(self):
        self.assertEqual(self.client.get("/api/health").status_code, 200)
        response = self.client.get("/api/recipes?q=番茄")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["items"][0]["title"], "番茄炒蛋")
        detail = self.client.get("/api/recipes/1")
        self.assertEqual(detail.status_code, 200)
        self.assertTrue(detail.get_json()["data"]["ingredients"])

    def test_auth_and_social_toggle(self):
        self.register()
        token = self.csrf()
        headers = {"X-CSRF-Token": token}
        self.assertEqual(self.client.post("/api/recipes/1/like", headers=headers).status_code, 200)
        self.assertEqual(self.client.post("/api/recipes/1/favorite", headers=headers).status_code, 200)
        comment = self.client.post("/api/recipes/1/comments", json={"content": "很好吃！"}, headers=headers)
        self.assertEqual(comment.status_code, 201)
        self.assertEqual(self.client.get("/api/users/me/favorites").status_code, 200)

    def test_recipe_creation_requires_auth_and_enters_pending(self):
        response = self.client.post("/api/recipes", json={"title": "无权限"})
        self.assertEqual(response.status_code, 401)
        self.register("creator")
        token = self.csrf()
        response = self.client.post("/api/recipes", json={"title": "我的新菜", "description": "测试", "ingredients": [{"name": "土豆", "amount": "2", "unit": "个"}], "steps": [{"instruction": "切块"}], "tags": ["家常菜"]}, headers={"X-CSRF-Token": token})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["data"]["status"], "pending")
        self.assertEqual(self.client.get("/api/recipes").get_json()["pagination"]["total"], 3)

    def test_profile_and_password_settings(self):
        self.register("settings-user")
        token = self.csrf()
        headers = {"X-CSRF-Token": token}
        profile = self.client.patch("/api/users/me", json={"username": "new-name", "bio": "喜欢研究家常菜", "interests": ["烘焙", "咖啡"]}, headers=headers)
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.get_json()["user"]["bio"], "喜欢研究家常菜")
        self.assertEqual(profile.get_json()["user"]["interests"], ["烘焙", "咖啡"])
        self.assertEqual(self.client.get("/api/users/me/recipes").status_code, 200)
        avatar = self.client.post("/api/users/me/avatar", data={"avatar": (BytesIO(b"fake-image"), "avatar.png")}, headers=headers, content_type="multipart/form-data")
        self.assertEqual(avatar.status_code, 200)
        self.assertTrue(avatar.get_json()["avatar_url"].startswith("/images/uploads/avatar-"))
        avatar_url = avatar.get_json()["avatar_url"]
        preserved = self.client.patch("/api/users/me", json={"username": "new-name", "bio": "更新简介", "interests": ["烘焙"]}, headers=headers)
        self.assertEqual(preserved.status_code, 200)
        self.assertEqual(preserved.get_json()["user"]["avatar_url"], avatar_url)
        mime_fallback = self.client.post("/api/users/me/avatar", data={"avatar": (BytesIO(b"fake-image"), "photo", "image/png")}, headers=headers, content_type="multipart/form-data")
        self.assertEqual(mime_fallback.status_code, 200)
        self.assertTrue(mime_fallback.get_json()["avatar_url"].endswith(".png"))
        wrong = self.client.post("/api/auth/change-password", json={"current_password": "wrong", "new_password": "newsecret", "confirm_password": "newsecret"}, headers=headers)
        self.assertEqual(wrong.status_code, 400)
        changed = self.client.post("/api/auth/change-password", json={"current_password": "secret1", "new_password": "newsecret", "confirm_password": "newsecret"}, headers=headers)
        self.assertEqual(changed.status_code, 200)
        self.client.post("/api/auth/logout", headers=headers)
        logged_in = self.client.post("/api/auth/login", json={"identity": "new-name", "password": "newsecret"})
        self.assertEqual(logged_in.status_code, 200)

    def test_categories_and_admin_management(self):
        categories = self.client.get("/api/categories").get_json()["items"]
        self.assertEqual([item["name"] for item in categories[:4]], ["中餐", "西餐", "日料", "韩餐"])
        login = self.client.post("/api/auth/login", json={"identity": "admin@foodlab.local", "password": "FoodLab-admin-123"})
        self.assertEqual(login.status_code, 200)
        headers = {"X-CSRF-Token": self.csrf()}
        self.assertEqual(self.client.get("/api/admin/stats").status_code, 200)
        self.assertEqual(self.client.get("/api/admin/users").status_code, 200)
        featured = self.client.patch("/api/admin/recipes/1/featured", json={"is_featured": False}, headers=headers)
        self.assertEqual(featured.status_code, 200)
        self.assertFalse(featured.get_json()["is_featured"])
        featured = self.client.patch("/api/admin/recipes/1/featured", json={"is_featured": True}, headers=headers)
        self.assertEqual(featured.status_code, 200)
        self.assertTrue(featured.get_json()["is_featured"])
        self.assertEqual(self.client.post("/api/admin/categories", json={"name": "测试分类", "slug": "test-category"}, headers=headers).status_code, 405)

    def test_seeded_regular_user_can_login(self):
        response = self.client.post("/api/auth/login", json={"identity": "user@foodlab.local", "password": "FoodLab-user-123"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["role"], "user")


if __name__ == "__main__":
    unittest.main()
