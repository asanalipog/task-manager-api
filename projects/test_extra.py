"""
Additional coverage on top of tests.py:
  - filtering / ordering on TaskViewSet
  - malformed / missing-field input -> expect 400, not 500
  - anonymous access to custom actions specifically
  - duplicate membership creation via the API (not just direct ORM IntegrityError)

Import BaseAPITestCase from tests.py to reuse the same fixtures.
NOTE: the filter field names used below (status, project) are guesses based
on the Task model. If TaskFilter (filters.py) exposes different/fewer
fields, adjust test_filter_tasks_by_status / test_filter_tasks_by_project
accordingly.
"""

from django.utils import timezone
from datetime import timedelta
from rest_framework import status

from .models import Membership, Task
from .tests import BaseAPITestCase


class TaskFilteringOrderingTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.t_todo = Task.objects.create(
            title="todo1", description="d", project=self.project, status="TODO",
            due_date=timezone.localdate() + timedelta(days=5),
        )
        self.t_done = Task.objects.create(
            title="done1", description="d", project=self.project, status="DONE",
            due_date=timezone.localdate() + timedelta(days=1),
        )
        self.t_other_project = Task.objects.create(
            title="other", description="d", project=self.other_project, status="TODO",
        )

    def test_filter_tasks_by_status(self):
        self.as_(self.member)
        response = self.client.get("/api/tasks/?status=DONE")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        titles = [t["title"] for t in results]
        self.assertIn("done1", titles)
        self.assertNotIn("todo1", titles)

    def test_filter_tasks_by_project(self):
        self.as_(self.member)
        response = self.client.get(f"/api/tasks/?project={self.project.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        for row in results:
            self.assertEqual(row["project"], self.project.id)

    def test_filter_tasks_by_assignee(self):
        Task.objects.filter(id=self.t_todo.id).update(assignee=self.member.id)
        self.as_(self.member)
        response = self.client.get(f"/api/tasks/?assignee={self.member.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        titles = [t["title"] for t in results]
        self.assertIn("todo1", titles)
        self.assertNotIn("done1", titles)

    def test_order_tasks_by_due_date_ascending(self):
        self.as_(self.member)
        response = self.client.get("/api/tasks/?ordering=due_date")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        due_dates = [row["due_date"] for row in results if row["due_date"]]
        self.assertEqual(due_dates, sorted(due_dates))

    def test_order_tasks_by_created_at_descending(self):
        self.as_(self.member)
        response = self.client.get("/api/tasks/?ordering=-created_at")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        created = [row["created_at"] for row in results]
        self.assertEqual(created, sorted(created, reverse=True))

    def test_invalid_ordering_field_ignored_not_500(self):
        self.as_(self.member)
        response = self.client.get("/api/tasks/?ordering=not_a_real_field")
        # DRF's OrderingFilter silently ignores invalid fields rather than erroring.
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class MalformedInputTests(BaseAPITestCase):
    def test_create_task_missing_title(self):
        self.as_(self.member)
        response = self.client.post(
            "/api/tasks/", {"description": "d", "project": self.project.id}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data)

    def test_create_task_title_too_long(self):
        self.as_(self.member)
        response = self.client.post(
            "/api/tasks/",
            {"title": "x" * 1000, "description": "d", "project": self.project.id},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_task_nonexistent_project(self):
        self.as_(self.member)
        response = self.client.post(
            "/api/tasks/", {"title": "t", "description": "d", "project": 999999}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_task_invalid_status_value(self):
        self.as_(self.member)
        response = self.client.post(
            "/api/tasks/",
            {
                "title": "t",
                "description": "d",
                "project": self.project.id,
                "status": "NOT_A_STATUS",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_membership_invalid_role_string(self):
        self.as_(self.owner)
        response = self.client.post(
            "/api/memberships/",
            {"project": self.project.id, "user": self.outsider.id, "role": "SUPERADMIN"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_membership_missing_user(self):
        self.as_(self.owner)
        response = self.client.post(
            "/api/memberships/", {"project": self.project.id, "role": "MEMBER"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_project_description_too_long(self):
        self.as_(self.member)
        response = self.client.post(
            "/api/projects/", {"name": "ok", "description": "x" * 10051}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_membership_via_api_returns_400_not_500(self):
        # self.member is already a member of self.project (from BaseAPITestCase.setUp).
        self.as_(self.owner)
        response = self.client.post(
            "/api/memberships/",
            {"project": self.project.id, "user": self.member.id, "role": "VIEWER"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            Membership.objects.filter(project=self.project, user=self.member).count(), 1
        )


class PermissionClassUnitTests(BaseAPITestCase):
    """
    Exercise IsTaskEditorOrReadOnly.has_permission() directly, with no
    serializer in the loop. This is the layer that's supposed to enforce
    "only project members can create tasks" -- it should not depend on
    TaskSerializer.validate() as a safety net.
    """

    class _FakeView:
        action = "create"

    def _request(self, user, data):
        from types import SimpleNamespace
        return SimpleNamespace(method="POST", user=user, data=data)

    def test_outsider_with_string_project_id_denied_at_permission_layer(self):
        from .permissions import IsTaskEditorOrReadOnly
        perm = IsTaskEditorOrReadOnly()
        # self.outsider is not a member of self.project at all. project id
        # sent as a string, as it would be in any real multipart/form POST.
        request = self._request(self.outsider, {"project": str(self.project.id)})
        allowed = perm.has_permission(request, self._FakeView())
        self.assertFalse(
            allowed,
            "has_permission granted access to a non-member because project_id "
            "was a string -- the membership check is being bypassed for "
            "ordinary form-encoded requests, and only the serializer's "
            "redundant PermissionDenied check is catching this case.",
        )

    def test_member_with_string_project_id_allowed_at_permission_layer(self):
        from .permissions import IsTaskEditorOrReadOnly
        perm = IsTaskEditorOrReadOnly()
        request = self._request(self.member, {"project": str(self.project.id)})
        allowed = perm.has_permission(request, self._FakeView())
        self.assertTrue(allowed)


class AnonymousCustomActionTests(BaseAPITestCase):
    def test_anonymous_cannot_complete_task(self):
        task = Task.objects.create(title="t", description="d", project=self.project)
        response = self.client.post(f"/api/tasks/{task.id}/complete/")
        self.assertIn(response.status_code, (401, 403))

    def test_anonymous_cannot_leave_membership(self):
        membership = Membership.objects.get(user=self.member, project=self.project)
        response = self.client.post(f"/api/memberships/{membership.id}/leave/")
        self.assertIn(response.status_code, (401, 403))

    def test_anonymous_cannot_view_project_memberships_action(self):
        response = self.client.get(f"/api/projects/{self.project.id}/memberships/")
        self.assertIn(response.status_code, (401, 403))

    def test_anonymous_cannot_view_project_tasks_action(self):
        response = self.client.get(f"/api/projects/{self.project.id}/tasks/")
        self.assertIn(response.status_code, (401, 403))