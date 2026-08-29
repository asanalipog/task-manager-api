from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from random import randint, choice
from datetime import date, timedelta

from projects.models import Project, Task, Membership, Status, Role


class Command(BaseCommand):
    help = "Generate a large dataset for query analysis"

    def handle(self, *args, **kwargs):
        User = get_user_model()
        Membership.objects.all().delete()
        Task.objects.all().delete()
        Project.objects.all().delete()
        User.objects.all().delete()
        with transaction.atomic():

            # Users
            users = [
                User(
                    username=f"user_{i}",
                    email=f"user_{i}@example.com",
                )
                for i in range(1000)
            ]

            User.objects.bulk_create(users, batch_size=1000)

            # Projects
            projects = [
                Project(
                    name=f"Project {i}",
                    description=f"Description for project {i}",
                )
                for i in range(100)
            ]

            Project.objects.bulk_create(projects, batch_size=100)

            # Refresh objects from DB so relationships are available
            projects = list(Project.objects.all())
            users = list(User.objects.all())

            # Memberships
            memberships = []

            for project in projects:
                selected_users = users[:20]

                for user in selected_users:
                    memberships.append(
                        Membership(
                            project=project,
                            user=user,
                            role=choice(Role.values),
                        )
                    )

            Membership.objects.bulk_create(
                memberships,
                batch_size=1000,
            )

            # Tasks
            tasks = []

            for i in range(100_000):
                project = choice(projects)
                assignee = choice(users)

                tasks.append(
                    Task(
                        title=f"Task {i}",
                        description=f"Description for task {i}",
                        project=project,
                        assignee=assignee,
                        status=choice(Status.values),
                        due_date=date.today() + timedelta(
                            days=randint(1, 365)
                        ),
                    )
                )

                if len(tasks) >= 5000:
                    Task.objects.bulk_create(
                        tasks,
                        batch_size=5000,
                    )
                    tasks = []

            if tasks:
                Task.objects.bulk_create(
                    tasks,
                    batch_size=5000,
                )

        self.stdout.write(
            self.style.SUCCESS("Dataset generated successfully.")
        )