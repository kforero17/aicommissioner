# League Membership API Endpoints - Quick Reference

## Base URL
All endpoints are prefixed with `/members` (except public invite validation)

## Authentication
- 🔓 Public: No authentication required
- 🔐 User: Requires valid JWT token
- 👑 Owner: Requires user to be league owner/commissioner

---

## Admin Endpoints (Commissioner Only)

### Generate Invite Link
**POST** `/members/admin/leagues/{league_id}/invite`

👑 Owner only

**Request:**
```json
{
  "invite_email": "friend@example.com"  // Optional
}
```

**Response:**
```json
{
  "invite_url": "https://app.com/invite/WXRNIXxCNfm-PCdXAbtb_12345",
  "token": "WXRNIXxCNfm-PCdXAbtb_12345",
  "expires_in_days": 7
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/members/admin/leagues/1/invite \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"invite_email": "friend@example.com"}'
```

---

### List League Members
**GET** `/members/admin/leagues/{league_id}/members`

👑 Owner only

**Response:**
```json
[
  {
    "id": 1,
    "user_id": 42,
    "email": "member@example.com",
    "role": "member",
    "joined_at": "2024-01-15T10:30:00Z",
    "invited_at": "2024-01-14T08:00:00Z",
    "preferences": {
      "mute_waivers": false,
      "email_digest": "weekly"
    }
  },
  {
    "id": 2,
    "user_id": null,
    "email": "pending@example.com",
    "role": "member",
    "joined_at": null,
    "invited_at": "2024-01-20T12:00:00Z",
    "preferences": null
  }
]
```

**Example:**
```bash
curl http://localhost:8000/members/admin/leagues/1/members \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Remove Member
**DELETE** `/members/admin/leagues/{league_id}/members/{member_id}`

👑 Owner only

**Response:**
```json
{
  "message": "Member removed successfully"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:8000/members/admin/leagues/1/members/42 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Public Endpoints

### Validate Invite Token
**GET** `/members/invite/{token}`

🔓 Public (no auth required)

**Response (Valid):**
```json
{
  "valid": true,
  "league_name": "Fantasy Football 2024",
  "league_id": 1,
  "invited_by": "Commissioner Name"
}
```

**Response (Invalid):**
```json
{
  "valid": false,
  "error": "Invalid or expired invite"
}
```

**Example:**
```bash
curl http://localhost:8000/members/invite/WXRNIXxCNfm-PCdXAbtb_12345
```

---

## User Endpoints

### Accept Invite
**POST** `/members/invite/{token}/accept`

🔐 User authentication required

**Response:**
```json
{
  "message": "Successfully joined league",
  "league_id": 1,
  "league_name": "Fantasy Football 2024"
}
```

**Errors:**
- 404: Invalid or expired invite
- 400: Invite already used
- 400: Already a member of this league

**Example:**
```bash
curl -X POST http://localhost:8000/members/invite/WXRNIXxCNfm-PCdXAbtb_12345/accept \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Check League Access
**GET** `/members/leagues/{league_id}/access`

🔐 User authentication required

**Response:**
```json
{
  "has_access": true,
  "role": "member",
  "is_owner": false,
  "preferences": {
    "mute_waivers": false,
    "email_digest": "weekly"
  }
}
```

**Example:**
```bash
curl http://localhost:8000/members/leagues/1/access \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Get My Membership
**GET** `/members/leagues/{league_id}/members/me`

🔐 Member authentication required

**Response:**
```json
{
  "is_owner": false,
  "role": "member",
  "joined_at": "2024-01-15T10:30:00Z",
  "preferences": {
    "mute_waivers": false,
    "mute_power_rankings": false,
    "email_digest": "weekly"
  }
}
```

**Example:**
```bash
curl http://localhost:8000/members/leagues/1/members/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Update My Preferences
**PATCH** `/members/leagues/{league_id}/members/me/preferences`

🔐 Member authentication required

**Request:**
```json
{
  "mute_waivers": true,
  "mute_power_rankings": false,
  "mute_weekly_recaps": false,
  "email_digest": "daily"
}
```

**Response:**
```json
{
  "message": "Preferences updated successfully",
  "preferences": {
    "mute_waivers": true,
    "mute_power_rankings": false,
    "mute_weekly_recaps": false,
    "email_digest": "daily"
  }
}
```

**Notes:**
- Only provided fields are updated (partial updates supported)
- Set to `null` to remove a preference

**Example:**
```bash
curl -X PATCH http://localhost:8000/members/leagues/1/members/me/preferences \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mute_waivers": true, "email_digest": "daily"}'
```

---

## Updated Endpoints (Now Support Members)

These existing endpoints now allow member access (previously owner-only):

### Get League Standings
**GET** `/admin/leagues/{league_id}/standings`

🔐 Owner or Member

### Get League Matchups
**GET** `/admin/leagues/{league_id}/matchups`

🔐 Owner or Member

### Get League Transactions
**GET** `/admin/leagues/{league_id}/transactions`

🔐 Owner or Member

---

## Member Preferences Schema

```typescript
interface MemberPreferences {
  mute_waivers?: boolean;           // Hide waiver content
  mute_power_rankings?: boolean;    // Hide power rankings
  mute_weekly_recaps?: boolean;     // Hide weekly recaps
  email_digest?: "none" | "daily" | "weekly";  // Email frequency
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invite already used"
}
```

### 403 Forbidden
```json
{
  "detail": "Only league owner can perform this action"
}
```

### 404 Not Found
```json
{
  "detail": "League not found"
}
```

---

## Complete Flow Example

### 1. Commissioner generates invite
```bash
POST /members/admin/leagues/1/invite
→ Returns: { invite_url: "https://app.com/invite/abc123" }
```

### 2. Invitee validates invite (logged out)
```bash
GET /members/invite/abc123
→ Returns: { valid: true, league_name: "My League", invited_by: "John" }
```

### 3. Invitee logs in/signs up
```bash
POST /auth/login
→ Returns: { access_token: "user_token" }
```

### 4. Invitee accepts invite
```bash
POST /members/invite/abc123/accept
Headers: Authorization: Bearer user_token
→ Returns: { league_id: 1, league_name: "My League" }
```

### 5. Invitee checks access
```bash
GET /members/leagues/1/access
Headers: Authorization: Bearer user_token
→ Returns: { has_access: true, role: "member", is_owner: false }
```

### 6. Invitee views league content
```bash
GET /admin/leagues/1/standings
Headers: Authorization: Bearer user_token
→ Returns: [standings data]
```

### 7. Invitee updates preferences
```bash
PATCH /members/leagues/1/members/me/preferences
Headers: Authorization: Bearer user_token
Body: { "mute_waivers": true }
→ Returns: { message: "Updated", preferences: {...} }
```

---

## Testing Tips

1. **Test invite flow end-to-end** with two different users
2. **Verify access control** - members can view but not modify settings
3. **Test token invalidation** - used tokens should fail on reuse
4. **Test cascade deletion** - removing league removes all memberships
5. **Test preferences** - each league can have different member preferences

---

## Rate Limiting Recommendations

- Invite generation: 10 per hour per league
- Accept invite: 5 per hour per user
- Preference updates: 20 per hour per user

---

## Future Endpoints (Planned)

- `POST /members/admin/leagues/{id}/invite/bulk` - Bulk invite via email list
- `GET /members/admin/leagues/{id}/invites` - List all pending invites
- `POST /members/admin/leagues/{id}/invites/{token}/resend` - Resend invite email
- `POST /members/leagues/{id}/leave` - Leave a league voluntarily
