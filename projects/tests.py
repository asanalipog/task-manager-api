from rest_framework.test import APITestCase

from django.contrib.auth import get_user_model

from .models import Project


class ProjectAPITests(APITestCase):

    def setUp(self,):
            self.user = get_user_model().objects.create_user(username= "Tester", password = "testerpass")
            self.other_user = get_user_model().objects.create_user(username= "who", password = "unknown")
    def test_unauthorized_401(self):
        response = self.client.get("/api/projects/")
        self.assertEqual(response.status_code, 401)

    

    def test_creating_project(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/projects/", {"name": "something", "description": "nothing to add"})
        new_item = Project.objects.last()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(new_item.owner, self.user)

    def test_user_cannot_see_others_project(self):
        project = Project.objects.create(owner=self.user, name="temporary", description = "dont know waht to fill here")

        self.client.force_authenticate(user = self.other_user)
        response_1 = self.client.get(f"/api/projects/{project.id}/")
        response_2 = self.client.get(f"/api/projects/")
        self.assertEqual(response_1.status_code, 404)
        self.assertEqual(response_2.data["count"], 0)


