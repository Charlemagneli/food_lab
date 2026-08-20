import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from backend.app import create_app
from backend.database.db import connect


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
        blocked_comment = self.client.post("/api/recipes/1/comments", json={"content": "参加刷 单-返 利项目"}, headers=headers)
        self.assertEqual(blocked_comment.status_code, 422)
        self.assertEqual(blocked_comment.get_json()["code"], "content_blocked")
        allowed_comment = self.client.post("/api/recipes/1/comments", json={"content": "分享一条反诈骗提醒。"}, headers=headers)
        self.assertEqual(allowed_comment.status_code, 201)
        db = connect(self.app.config["DATABASE_PATH"])
        moderation_event = db.execute("SELECT reason_code,rule_hash FROM comment_moderation_events").fetchone()
        event_columns = {row["name"] for row in db.execute("PRAGMA table_info(comment_moderation_events)").fetchall()}
        blocked_saved = db.execute("SELECT 1 FROM comments WHERE content LIKE '%刷 单%'").fetchone()
        db.close()
        self.assertEqual(moderation_event["reason_code"], "fraud")
        self.assertEqual(len(moderation_event["rule_hash"]), 16)
        self.assertNotIn("content", event_columns)
        self.assertIsNone(blocked_saved)
        comments = self.client.get("/api/recipes/1/comments").get_json()["items"]
        comment_id = next(item["id"] for item in comments if item["content"] == "很好吃！")
        liked_comment = self.client.post(f"/api/comments/{comment_id}/like", headers=headers)
        self.assertEqual(liked_comment.status_code, 200)
        self.assertTrue(liked_comment.get_json()["active"])
        self.assertEqual(liked_comment.get_json()["count"], 1)
        detail_comment = next(item for item in self.client.get("/api/recipes/1").get_json()["data"]["comments"] if item["id"] == comment_id)
        self.assertEqual(detail_comment["user_id"], self.client.get("/api/auth/me").get_json()["user"]["id"])
        self.assertTrue(detail_comment["is_liked"])
        self.assertEqual(self.client.get("/api/users/me/favorites").status_code, 200)
        self.assertEqual(self.client.post("/api/recipes/99999/like", headers=headers).status_code, 404)
        self.assertEqual(self.client.post("/api/comments/99999/like", headers=headers).status_code, 404)
        self.assertEqual(self.client.delete("/api/admin/recipes/1", headers=headers).status_code, 403)
        self.assertEqual(self.client.delete(f"/api/comments/{comment_id}", headers=headers).status_code, 200)

    def test_recipe_creation_requires_auth_and_enters_pending(self):
        response = self.client.post("/api/recipes", json={"title": "无权限"})
        self.assertEqual(response.status_code, 401)
        self.register("creator")
        token = self.csrf()
        invalid = self.client.post("/api/recipes", json={"title": "任意菜系", "cuisine": "自定义类型"}, headers={"X-CSRF-Token": token})
        self.assertEqual(invalid.status_code, 400)
        response = self.client.post("/api/recipes", json={"title": "我的新菜", "description": "测试", "cuisine": "中餐", "meal_type": "该字段应被忽略", "ingredients": [{"name": "土豆", "amount": "2", "unit": "个"}], "steps": [{"instruction": "切块"}], "tags": ["家常菜"]}, headers={"X-CSRF-Token": token})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["data"]["status"], "pending")
        self.assertNotIn("meal_type", response.get_json()["data"])
        bypass = self.client.put(f"/api/recipes/{response.get_json()['data']['id']}", json={"status": "published"}, headers={"X-CSRF-Token": token})
        self.assertEqual(bypass.status_code, 200)
        self.assertEqual(bypass.get_json()["data"]["status"], "pending")
        uploaded = self.client.post("/api/recipes", data={
            "title": "带步骤图片的菜谱", "description": "上传测试", "cuisine": "西餐", "servings": "99", "status": "draft",
            "ingredients": '[{"name":"面粉","amount":"100","unit":"克"}]',
            "steps": '[{"instruction":"混合食材"}]', "tags": '["烘焙","快手"]',
            "cover_image": (BytesIO(b"cover-image"), "cover.png", "image/png"),
            "step_image_0": (BytesIO(b"step-image"), "step.webp", "image/webp"),
        }, headers={"X-CSRF-Token": token}, content_type="multipart/form-data")
        self.assertEqual(uploaded.status_code, 201)
        uploaded_data = uploaded.get_json()["data"]
        self.assertTrue(uploaded_data["cover_image"].startswith("/images/uploads/"))
        self.assertTrue(uploaded_data["steps"][0]["image_url"].endswith(".webp"))
        self.assertNotIn("servings", uploaded_data)
        self.assertEqual(uploaded_data["tags"], ["烘焙", "快手"])
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
        self.assertEqual(self.client.patch("/api/admin/recipes/1", json={"status": "hidden"}, headers=headers).status_code, 400)
        hidden = self.client.patch("/api/admin/recipes/1", json={"status": "hidden", "reason": "内容需要复核"}, headers=headers)
        self.assertEqual(hidden.status_code, 200)
        self.assertEqual(hidden.get_json()["status"], "hidden")
        self.assertEqual(self.client.get("/api/recipes").get_json()["pagination"]["total"], 2)
        self.assertEqual(self.client.get("/api/recipes/1").status_code, 200)
        hidden_item = self.client.get("/api/admin/recipes?status=hidden").get_json()["items"][0]
        self.assertEqual(hidden_item["rejection_reason"], "内容需要复核")
        self.assertTrue(hidden_item["reviewed_at"])
        self.assertEqual(hidden_item["reviewer"], "FoodLab 管理员")
        restored = self.client.patch("/api/admin/recipes/1", json={"status": "published"}, headers=headers)
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.get_json()["rejection_reason"], "")
        featured = self.client.patch("/api/admin/recipes/1/featured", json={"is_featured": False}, headers=headers)
        self.assertEqual(featured.status_code, 200)
        self.assertFalse(featured.get_json()["is_featured"])
        featured = self.client.patch("/api/admin/recipes/1/featured", json={"is_featured": True}, headers=headers)
        self.assertEqual(featured.status_code, 200)
        self.assertTrue(featured.get_json()["is_featured"])
        deleted = self.client.delete("/api/admin/recipes/3", headers=headers)
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(len(self.client.get("/api/admin/recipes").get_json()["items"]), 2)
        self.assertEqual(self.client.post("/api/admin/categories", json={"name": "测试分类", "slug": "test-category"}, headers=headers).status_code, 405)

    def test_seeded_regular_user_can_login(self):
        response = self.client.post("/api/auth/login", json={"identity": "user@foodlab.local", "password": "FoodLab-user-123"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["role"], "user")

    def test_system_messages(self):
        self.assertEqual(self.client.get("/api/messages").status_code, 401)
        self.register("message-user")
        headers = {"X-CSRF-Token": self.csrf()}
        inbox = self.client.get("/api/messages").get_json()
        self.assertEqual(len(inbox["items"]), 1)
        self.assertEqual(inbox["unread"], 1)
        self.assertNotIn("followers", inbox)
        self.assertNotIn("direct", inbox)
        self.assertEqual(self.client.post("/api/messages/direct", json={"recipient": "FoodLab 管理员", "content": "你好"}, headers=headers).status_code, 405)
        recipe_payload = {"description": "审核通知测试", "cuisine": "中餐", "ingredients": [{"name": "测试食材", "amount": "1", "unit": "份"}], "steps": [{"instruction": "完成测试步骤"}]}
        approved_id = self.client.post("/api/recipes", json={"title": "等待通过的菜谱", **recipe_payload}, headers=headers).get_json()["data"]["id"]
        rejected_id = self.client.post("/api/recipes", json={"title": "等待修改的菜谱", **recipe_payload}, headers=headers).get_json()["data"]["id"]
        marked = self.client.patch("/api/messages/read", headers=headers)
        self.assertEqual(marked.status_code, 200)
        self.assertEqual(self.client.get("/api/messages").get_json()["unread"], 0)
        self.client.post("/api/auth/logout", headers=headers)
        self.client.post("/api/auth/login", json={"identity": "admin@foodlab.local", "password": "FoodLab-admin-123"})
        admin_headers = {"X-CSRF-Token": self.csrf()}
        approved = self.client.patch(f"/api/admin/recipes/{approved_id}", json={"status": "published"}, headers=admin_headers)
        rejected = self.client.patch(f"/api/admin/recipes/{rejected_id}", json={"status": "rejected", "reason": "步骤说明不够完整"}, headers=admin_headers)
        self.assertTrue(approved.get_json()["notification_sent"])
        self.assertTrue(rejected.get_json()["notification_sent"])
        duplicate = self.client.patch(f"/api/admin/recipes/{rejected_id}", json={"status": "rejected", "reason": "步骤说明不够完整"}, headers=admin_headers)
        self.assertFalse(duplicate.get_json()["notification_sent"])
        self.client.post("/api/auth/logout", headers=admin_headers)
        self.client.post("/api/auth/login", json={"identity": "message-user", "password": "secret1"})
        user_inbox = self.client.get("/api/messages").get_json()
        contents = [item["content"] for item in user_inbox["items"]]
        self.assertEqual(user_inbox["unread"], 2)
        self.assertEqual(self.client.get("/api/messages/unread-count").get_json()["count"], 2)
        self.assertTrue(any("等待通过的菜谱" in content and "已通过审核" in content for content in contents))
        self.assertTrue(any("等待修改的菜谱" in content and "步骤说明不够完整" in content for content in contents))
        self.assertEqual(sum("等待修改的菜谱" in content for content in contents), 1)


if __name__ == "__main__":
    unittest.main()
