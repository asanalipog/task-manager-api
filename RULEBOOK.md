# Permissions Rulebook — who can do what

Roles live on Membership (user + project + role). A user's power on a project
= their Membership.role for THAT project. No membership = no access.

## Role ladder (cumulative)
- VIEWER : read only
- MEMBER : VIEWER + create/edit/complete TASKS, can be assignee
- ADMIN  : MEMBER + manage MEMBERSHIPS (add/remove/change NON-owner roles)
- OWNER  : ADMIN + delete PROJECT, manage owner/admins

## Rules per resource

### TASK  (needs: read=any member, write=MEMBER+)
- GET/list      -> any role (VIEWER included)
- POST/PATCH/DELETE/complete -> role in [OWNER, ADMIN, MEMBER]

### MEMBERSHIP  (needs: read=member, write=ADMIN+)
- GET           -> members of that project only
- POST/PATCH/DELETE -> role in [OWNER, ADMIN]
- extra: ADMIN cannot create/edit an OWNER row (only OWNER can)

### PROJECT
- GET/list      -> any membership (VIEWER+)
- create        -> any authenticated user (they become OWNER)
- delete        -> OWNER only

## The 2 hooks (MEMORIZE THIS)
- has_permission(request, view): runs on EVERY request. NO object yet.
  -> gate LIST and CREATE here. For create, read project from request.data.
- has_object_permission(request, view, obj): runs ONLY on retrieve/update/delete.
  -> gate per-object by role here (obj.project gives the project).
- CREATE is never checked by has_object_permission. If you only guard there,
  create is WIDE OPEN. This is the #1 bug.

## Return values
- Return True/False. False -> DRF sends 403 automatically. Don't raise.
- SAFE_METHODS = GET/HEAD/OPTIONS (reads).

## Where things go (layer discipline)
- Permission class = "may this user act?" -> 403
- Serializer validate = "is the data valid?" -> 400
- get_queryset = which rows the user can even SEE (scoping). Separate from permissions.

## Wiring (easy to forget)
On each viewset:  permission_classes = [IsAuthenticated, YourPermissionClass]
If not listed, the class never runs.

## Checklist to pass 2.3
[ ] TaskViewSet uses task permission class + scoped get_queryset
[ ] MembershipViewSet uses membership permission class + scoped get_queryset
[ ] Membership create checks role in has_permission (project from request.data)
[ ] VIEWER cannot POST a task or a membership (test it)
[ ] non-member gets 404/403 on another project's task
