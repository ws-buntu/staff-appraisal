# Departments and employee records (Task 4)

This increment adds a backend directory. The frontend directory, appraisal records and audit/signature subsystem remain later work. It does not calculate appraisal scores or promotion eligibility.

## Records

Departments have a UUID, unique code and name, and an active flag. Employee records have a UUID, unique staff identifier, a one-to-one account link, name fields, optional gender/professional details and appointment date, a department, an optional appraiser and an active flag. These fields implement the existing project design; they are not a claim that the exact original appraisal form has been reproduced.

The employee record's account link is immutable after creation. Changing profile text cannot grant account roles, change a password or modify Django administrative flags. Appraisers must be active accounts with the APPRAISER role, and employees cannot be assigned themselves as appraiser.

## API permissions

| Role | Employee reads | Department reads | Create/update |
| --- | --- | --- | --- |
| EMPLOYEE | Own employee record | Own department | Denied |
| APPRAISER | Assigned employees and own record | Departments represented by those records | Denied |
| HOD | Own department | Own department | Denied |
| HR / ADMIN | All | All | Allowed |

A department head without an employee/department association receives an empty scope. Django's staff/superuser flags do not expand these business permissions. Anonymous requests are rejected. An authenticated request for an out-of-scope record returns 404; list results contain only visible records. Current database relationships determine access, so reassignment changes the scope without waiting for token expiry.

Endpoints: `/api/departments/`, `/api/departments/{id}/`, `/api/employees/`, `/api/employees/{id}/`. Lists are paginated. HR and ADMIN can use POST, PUT and PATCH. There is no hard-delete API. Use `is_active=false` to mark a directory record inactive; this is separate from disabling its login account. Account/department/appraiser references are protected at the database layer. Employee responses are non-cacheable.

Historical audit events are not implemented in this increment. Do not treat current department/appraiser assignments as immutable historical appraisal assignments; the appraisal/audit domain will preserve its own relationships and revisions.

## Verification

PostgreSQL tests cover role-based list/detail isolation, record management, ownership/role tampering, reassignment, required fields, uniqueness and protected references. CI also exercises the actual HTTP API using disposable accounts and records. The CI script never prints credentials or tokens and removes only its own test records. No production employee data or seeded accounts are introduced.
