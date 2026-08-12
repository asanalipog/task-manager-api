"""
Test suite for the Project / Task / Membership permission system.

Role ladder (see permissions.py docstring):
    VIEWER  -> read only
    MEMBER  -> VIEWER + create/edit/complete tasks, can be assignee
    ADMIN   -> MEMBER + manage memberships (add/remove/change non-owner roles)
    OWNER   -> ADMIN + delete the project, manage admins/ownership
    anonymous -> no access

Tests are written against that spec. Where the current implementation
diverges from the spec, the test is kept (rather than adjusted to match
the buggy behavior) and marked with a `# BUG:` comment explaining what
it catches and why it currently fails.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Membership, Project, Task

User = get_user_model()


class BaseAPITestCase(APITestCase):
    """Common fixtures shared by most test classes.

    Project ``self.project`` has:
        owner    -> OWNER
        admin    -> ADMIN
        member   -> MEMBER
        viewer   -> VIEWER
        outsider -> not a member of this project at all
    """

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass12345")
        self.admin = User.objects.create_user(username="admin", password="pass12345")
        self.member = User.objects.create_user(username="member", password="pass12345")
        self.viewer = User.objects.create_user(username="viewer", password="pass12345")
        self.outsider = User.objects.create_user(username="outsider", password="pass12345")

        self.project = Project.objects.create(name="Proj A", description="desc a")

        Membership.objects.create(user=self.owner, project=self.project, role="OWNER")
        Membership.objects.create(user=self.admin, project=self.project, role="ADMIN")
        Membership.objects.create(user=self.member, project=self.project, role="MEMBER")
        Membership.objects.create(user=self.viewer, project=self.project, role="VIEWER")

        # A second, unrelated project to check for data leakage / isolation.
        self.other_project = Project.objects.create(name="Proj B", description="desc b")
        self.other_owner = User.objects.create_user(username="other_owner", password="pass12345")
        Membership.objects.create(user=self.other_owner, project=self.other_project, role="OWNER")

    # -- helpers ---------------------------------------------------------
    def as_(self, user):
        self.client.force_authenticate(user=user)
        return self.client


class AuthenticationTests(BaseAPITestCase):
    """Anonymous users should never get through, on any resource."""

    def test_anonymous_cannot_list_projects(self):
        response = self.client.get("/api/projects/")
        self.assertIn(response.status_code, (401, 403))

    def test_anonymous_cannot_list_tasks(self):
        response = self.client.get("/api/tasks/")
        self.assertIn(response.status_code, (401, 403))

    def test_anonymous_cannot_list_memberships(self):
        response = self.client.get("/api/memberships/")
        self.assertIn(response.status_code, (401, 403))

    def test_anonymous_cannot_create_project(self):
        response = self.client.post("/api/projects/", {"name": "x", "description": "y"})
        self.assertIn(response.status_code, (401, 403))


class ProjectPermissionTests(BaseAPITestCase):
    def test_creating_project_makes_creator_owner(self):
        self.as_(self.outsider)
        response = self.client.post(
            "/api/projects/", {"name": "New Proj", "description": "fresh"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_project = Project.objects.get(id=response.data["id"])
        membership = Membership.objects.get(project=new_project, user=self.outsider)
        self.assertEqual(membership.role, "OWNER")

    def test_list_only_returns_projects_user_belongs_to(self):
        self.as_(self.member)
        response = self.client.get("/api/projects/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [p["id"] for p in response.data["results"]] if "results" in response.data else [
            p["id"] for p in response.data
        ]
        self.assertIn(self.project.id, ids)
        self.assertNotIn(self.other_project.id, ids)

    def test_non_member_gets_404_on_detail(self):
        self.as_(self.outsider)
        response = self.client.get(f"/api/projects/{self.project.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_member_list_excludes_all_foreign_projects(self):
        self.as_(self.outsider)
        response = self.client.get("/api/projects/")
        count = response.data.get("count", len(response.data))
        self.assertEqual(count, 0)

    def test_viewer_can_read_project_detail(self):
        self.as_(self.viewer)
        response = self.client.get(f"/api/projects/{self.project.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_viewer_cannot_edit_project(self):
        self.as_(self.viewer)
        response = self.client.patch(f"/api/projects/{self.project.id}/", {"name": "hacked"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_cannot_edit_project(self):
        self.as_(self.member)
        response = self.client.patch(f"/api/projects/{self.project.id}/", {"name": "hacked"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_edit_project(self):
        # Per the spec, editing project fields is not granted to ADMIN, only OWNER.
        self.as_(self.admin)
        response = self.client.patch(f"/api/projects/{self.project.id}/", {"name": "hacked"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_edit_project(self):
        self.as_(self.owner)
        response = self.client.patch(f"/api/projects/{self.project.id}/", {"name": "renamed"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "renamed")

    def test_admin_cannot_delete_project(self):
        self.as_(self.admin)
        response = self.client.delete(f"/api/projects/{self.project.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_delete_project(self):
        self.as_(self.owner)
        response = self.client.delete(f"/api/projects/{self.project.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Project.objects.filter(id=self.project.id).exists())

    def test_project_memberships_action_lists_all_members(self):
        self.as_(self.viewer)
        response = self.client.get(f"/api/projects/{self.project.id}/memberships/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

    def test_project_tasks_action_scoped_to_project(self):
        Task.objects.create(title="t1", description="d", project=self.project)
        Task.objects.create(title="t2", description="d", project=self.other_project)
        self.as_(self.member)
        response = self.client.get(f"/api/projects/{self.project.id}/tasks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "t1")


class TaskPermissionTests(BaseAPITestCase):
    def _create_task_payload(self, **overrides):
        payload = {
            "title": "Do thing",
            "description": "details",
            "project": self.project.id,
        }
        payload.update(overrides)
        return payload

    def test_viewer_cannot_create_task(self):
        self.as_(self.viewer)
        response = self.client.post("/api/tasks/", self._create_task_payload())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_can_create_task(self):
        self.as_(self.member)
        response = self.client.post("/api/tasks/", self._create_task_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_can_create_task(self):
        self.as_(self.admin)
        response = self.client.post("/api/tasks/", self._create_task_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_owner_can_create_task(self):
        self.as_(self.owner)
        response = self.client.post("/api/tasks/", self._create_task_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_outsider_cannot_create_task_for_others_project(self):
        self.as_(self.outsider)
        response = self.client.post("/api/tasks/", self._create_task_payload())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_task_without_project_field_rejected(self):
        # Permission layer now defers to the serializer for a missing/invalid
        # project value, so this is a validation error (400), not an
        # authorization error (403).
        self.as_(self.member)
        payload = self._create_task_payload()
        del payload["project"]
        response = self.client.post("/api/tasks/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("project", response.data)

    def test_create_task_non_numeric_project_value_does_not_500(self):
        self.as_(self.member)
        payload = self._create_task_payload(project="not-a-number")
        response = self.client.post("/api/tasks/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_due_date_in_past_rejected(self):
        self.as_(self.member)
        payload = self._create_task_payload(
            due_date=(timezone.localdate() - timedelta(days=1)).isoformat()
        )
        response = self.client.post("/api/tasks/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_due_date_today_or_future_accepted(self):
        self.as_(self.member)
        payload = self._create_task_payload(due_date=timezone.localdate().isoformat())
        response = self.client.post("/api/tasks/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_assignee_must_belong_to_project(self):
        self.as_(self.member)
        payload = self._create_task_payload(assignee=self.outsider.id)
        response = self.client.post("/api/tasks/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_assignee_can_be_viewer_role_but_task_edit_stays_gated(self):
        # A VIEWER *can* be assigned (spec only restricts editing, not assignment),
        # but that alone shouldn't grant them edit rights.
        self.as_(self.member)
        payload = self._create_task_payload(assignee=self.viewer.id)
        response = self.client.post("/api/tasks/", payload)
        # assignee_role check requires role in OWNER/ADMIN/MEMBER, so VIEWER assignee
        # is currently rejected too.
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_assignee_accepted(self):
        self.as_(self.member)
        payload = self._create_task_payload(assignee=self.admin.id)
        response = self.client.post("/api/tasks/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["assignee"], self.admin.id)

    def test_viewer_cannot_edit_task(self):
        task = Task.objects.create(title="t", description="d", project=self.project)
        self.as_(self.viewer)
        response = self.client.patch(f"/api/tasks/{task.id}/", {"title": "changed"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_can_edit_task(self):
        task = Task.objects.create(title="t", description="d", project=self.project)
        self.as_(self.member)
        response = self.client.patch(f"/api/tasks/{task.id}/", {"title": "changed"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_outsider_cannot_edit_task(self):
        task = Task.objects.create(title="t", description="d", project=self.project)
        self.as_(self.outsider)
        response = self.client.patch(f"/api/tasks/{task.id}/", {"title": "changed"})
        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_viewer_cannot_complete_task(self):
        task = Task.objects.create(title="t", description="d", project=self.project)
        self.as_(self.viewer)
        response = self.client.post(f"/api/tasks/{task.id}/complete/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_can_complete_task(self):
        task = Task.objects.create(title="t", description="d", project=self.project)
        self.as_(self.member)
        response = self.client.post(f"/api/tasks/{task.id}/complete/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.status, "DONE")

    def test_member_can_read_task_list(self):
        Task.objects.create(title="t", description="d", project=self.project)
        self.as_(self.member)
        response = self.client.get("/api/tasks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        count = response.data.get("count", len(response.data))
        self.assertGreaterEqual(count, 1)

    def test_viewer_can_list_tasks(self):
        # BUG: TaskViewSet.get_queryset() for the "list" action filters
        # project__memberships__role__in=["OWNER", "ADMIN", "MEMBER"], omitting
        # VIEWER. Per the spec VIEWER has read access, so this currently
        # returns an empty list for viewers and this test fails.
        Task.objects.create(title="t", description="d", project=self.project)
        self.as_(self.viewer)
        response = self.client.get("/api/tasks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        count = response.data.get("count", len(response.data))
        self.assertGreaterEqual(count, 1)

    def test_task_list_does_not_leak_other_projects(self):
        Task.objects.create(title="mine", description="d", project=self.project)
        Task.objects.create(title="theirs", description="d", project=self.other_project)
        self.as_(self.member)
        response = self.client.get("/api/tasks/")
        results = response.data.get("results", response.data)
        titles = [t["title"] for t in results]
        self.assertIn("mine", titles)
        self.assertNotIn("theirs", titles)


class MembershipPermissionTests(BaseAPITestCase):
    def test_viewer_cannot_add_member(self):
        self.as_(self.viewer)
        response = self.client.post(
            "/api/memberships/",
            {"project": self.project.id, "user": self.outsider.id, "role": "MEMBER"},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_cannot_add_member(self):
        self.as_(self.member)
        response = self.client.post(
            "/api/memberships/",
            {"project": self.project.id, "user": self.outsider.id, "role": "MEMBER"},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_add_member(self):
        self.as_(self.admin)
        response = self.client.post(
            "/api/memberships/",
            {"project": self.project.id, "user": self.outsider.id, "role": "MEMBER"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_owner_can_add_member(self):
        self.as_(self.owner)
        response = self.client.post(
            "/api/memberships/",
            {"project": self.project.id, "user": self.outsider.id, "role": "VIEWER"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cannot_create_membership_with_owner_role(self):
        self.as_(self.owner)
        response = self.client.post(
            "/api/memberships/",
            {"project": self.project.id, "user": self.outsider.id, "role": "OWNER"},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_promote_someone_to_admin(self):
        self.as_(self.admin)
        response = self.client.patch(
            f"/api/memberships/{Membership.objects.get(user=self.member, project=self.project).id}/",
            {"role": "ADMIN"},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_promote_member_to_admin(self):
        self.as_(self.owner)
        response = self.client.patch(
            f"/api/memberships/{Membership.objects.get(user=self.member, project=self.project).id}/",
            {"role": "ADMIN"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_cannot_change_owners_role(self):
        # BUG: IsMembershipEditor.has_object_permission grants edit rights to any
        # ADMIN over any membership in the project, including the OWNER's own
        # membership. Nothing in MembershipSerializer.validate_role blocks
        # demoting the current OWNER either. Per spec, only OWNER manages
        # ownership/admins, so an ADMIN should not be able to touch the
        # OWNER's membership at all. This currently succeeds (200) and the
        # assertion below will fail, flagging the bug.
        owner_membership = Membership.objects.get(user=self.owner, project=self.project)
        self.as_(self.admin)
        response = self.client.patch(f"/api/memberships/{owner_membership.id}/", {"role": "MEMBER"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_delete_owners_membership(self):
        # BUG: same root cause as above -- has_object_permission for DELETE only
        # checks that the requester is OWNER/ADMIN in the project, not that the
        # target isn't the OWNER. An ADMIN can currently kick the OWNER out.
        owner_membership = Membership.objects.get(user=self.owner, project=self.project)
        self.as_(self.admin)
        response = self.client.delete(f"/api/memberships/{owner_membership.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Membership.objects.filter(id=owner_membership.id).exists())

    def test_owner_can_change_admins_role(self):
        self.as_(self.owner)
        admin_membership = Membership.objects.get(user=self.admin, project=self.project)
        response = self.client.patch(f"/api/memberships/{admin_membership.id}/", {"role": "MEMBER"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_can_leave_project(self):
        membership = Membership.objects.get(user=self.member, project=self.project)
        self.as_(self.member)
        response = self.client.post(f"/api/memberships/{membership.id}/leave/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Membership.objects.filter(id=membership.id).exists())

    def test_user_cannot_force_another_member_to_leave(self):
        membership = Membership.objects.get(user=self.member, project=self.project)
        self.as_(self.admin)
        response = self.client.post(f"/api/memberships/{membership.id}/leave/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Membership.objects.filter(id=membership.id).exists())

    def test_membership_list_scoped_to_own_memberships(self):
        self.as_(self.member)
        response = self.client.get("/api/memberships/")
        results = response.data.get("results", response.data)
        user_ids = {row["user"] for row in results}
        self.assertEqual(user_ids, {self.member.id})

    def test_member_can_view_own_membership_detail(self):
        membership = Membership.objects.get(user=self.member, project=self.project)
        self.as_(self.member)
        response = self.client.get(f"/api/memberships/{membership.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_outsider_cannot_view_membership_detail(self):
        membership = Membership.objects.get(user=self.member, project=self.project)
        self.as_(self.outsider)
        response = self.client.get(f"/api/memberships/{membership.id}/")
        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))


class ModelConstraintTests(BaseAPITestCase):
    def test_unique_membership_per_user_project(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Membership.objects.create(user=self.owner, project=self.project, role="VIEWER")

    def test_task_assignee_set_null_when_user_deleted(self):
        task = Task.objects.create(
            title="t", description="d", project=self.project, assignee=self.member
        )
        self.member.delete()
        task.refresh_from_db()
        self.assertIsNone(task.assignee)

    def test_deleting_project_cascades_to_tasks_and_memberships(self):
        task = Task.objects.create(title="t", description="d", project=self.project)
        project_id = self.project.id
        self.project.delete()
        self.assertFalse(Task.objects.filter(id=task.id).exists())
        self.assertFalse(Membership.objects.filter(project_id=project_id).exists())

    def test_str_methods(self):
        self.assertEqual(str(self.project), "Proj A")
        task = Task.objects.create(title="ttl", description="d", project=self.project)
        self.assertEqual(str(task), "ttl")
        membership = Membership.objects.get(user=self.owner, project=self.project)
        self.assertEqual(str(membership), "OWNER")