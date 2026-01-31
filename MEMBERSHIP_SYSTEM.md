# League Membership System

## Overview

The league membership system allows non-commissioners to access league hubs through invite links. Commissioners can generate shareable invite links that allow other users to view league standings, matchups, and transactions.

## Architecture

### Database Model

**LeagueMember** (`models/league_member.py`)
- Stores membership relationships between users and leagues
- Supports invite-based onboarding flow
- Tracks role (commissioner/member) and preferences
- Automatic commissioner membership when leagues are created

### API Endpoints

#### Admin Endpoints (Commissioner Only)

**POST /members/admin/leagues/{league_id}/invite**
- Generate invite link for a league
- Optional `invite_email` parameter to track who was invited
- Returns invite URL and token
- Requires: User must be league owner

**GET /members/admin/leagues/{league_id}/members**
- List all members (active and pending invites)
- Shows user info, role, join date, and preferences
- Requires: User must be league owner

**DELETE /members/admin/leagues/{league_id}/members/{member_id}**
- Remove a member or revoke a pending invite
- Requires: User must be league owner

#### Public Endpoints

**GET /members/invite/{token}**
- Validate invite token and show league info
- Used by invite landing page
- Returns league name and commissioner info
- No authentication required

**POST /members/invite/{token}/accept**
- Accept invite and join league
- Consumes the invite token
- Creates membership record for user
- Requires: User must be logged in

#### Member Endpoints

**GET /members/leagues/{league_id}/access**
- Check if current user has access to a league
- Returns role (commissioner/member) and preferences
- Used by frontend for authorization

**GET /members/leagues/{league_id}/members/me**
- Get current user's membership details
- Returns role, join date, and preferences

**PATCH /members/leagues/{league_id}/members/me/preferences**
- Update member preferences
- Allows customizing content delivery settings
- Schema: `{mute_waivers, mute_power_rankings, mute_weekly_recaps, email_digest}`

## Member Preferences

Members can customize their experience with these preferences:

```json
{
  "mute_waivers": false,           // Hide waiver content
  "mute_power_rankings": false,    // Hide power rankings
  "mute_weekly_recaps": false,     // Hide weekly recaps
  "email_digest": "weekly"         // "none", "daily", "weekly"
}
```

## Authorization

### League Hub Access

The following endpoints now support member access (previously commissioner-only):
- `GET /admin/leagues/{league_id}/standings`
- `GET /admin/leagues/{league_id}/matchups`
- `GET /admin/leagues/{league_id}/transactions`

Authorization logic:
1. Check if user is league owner → allow access
2. Check if user is active member (joined_at != null) → allow access
3. Otherwise → deny access (403 Forbidden)

### Commissioner-Only Actions

These remain commissioner-only:
- League settings management
- Invite generation and member removal
- Content generation and publishing
- League sync operations

## Database Schema

```sql
CREATE TABLE league_members (
    id INTEGER PRIMARY KEY,
    league_id INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL DEFAULT 'member',  -- 'commissioner' or 'member'

    -- Invite tracking
    invite_token VARCHAR(64) UNIQUE,
    invite_email VARCHAR(255),
    invited_at TIMESTAMP,
    joined_at TIMESTAMP,

    -- Member preferences (JSON)
    preferences TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Indexes

- `league_id` - For querying all members of a league
- `user_id` - For querying all leagues a user is a member of
- `invite_token` - For validating invite links

## Migration

Run the migration script to add the table and create commissioner memberships:

```bash
python migrations/add_league_members_table.py
```

This will:
1. Create the `league_members` table
2. Create commissioner membership records for all existing league owners

## Frontend Integration

### Invite Flow

1. **Commissioner generates invite**
   ```typescript
   POST /members/admin/leagues/{leagueId}/invite
   Response: { invite_url, token }
   ```

2. **Share invite URL**
   ```
   https://app.com/invite/{token}
   ```

3. **Invitee visits link**
   ```typescript
   GET /members/invite/{token}
   Response: { valid, league_name, invited_by }
   ```

4. **Invitee logs in/signs up**
   - If not logged in, redirect to auth
   - Store token in URL/session

5. **Accept invite**
   ```typescript
   POST /members/invite/{token}/accept
   Response: { league_id, league_name }
   ```

6. **Redirect to league hub**
   ```
   /dashboard/leagues/{leagueId}
   ```

### Access Check

Before showing league content:

```typescript
const checkAccess = async (leagueId: string) => {
  const response = await fetch(`/members/leagues/${leagueId}/access`);
  const { has_access, role, is_owner } = await response.json();

  if (!has_access) {
    // Show "No access" page
    return;
  }

  // Show content based on role
  if (is_owner) {
    // Show commissioner controls
  } else {
    // Show member view (no settings/admin)
  }
};
```

### Member Management UI

For commissioners, show member list with:
- Active members (joined_at != null)
- Pending invites (joined_at == null)
- Remove member action
- Generate new invite button

## Security Considerations

1. **Invite tokens are single-use** - Consumed when accepted
2. **Tokens are 32-byte URL-safe strings** - Cryptographically secure
3. **No expiration for MVP** - Can add later if needed
4. **Invite validation is public** - But doesn't reveal sensitive info
5. **Member actions are scoped** - Can only access leagues they're members of

## Future Enhancements

### V2 Features
- Invite expiration (7 days, 30 days, etc.)
- Bulk invite via email
- Member roles (admin, viewer, etc.)
- Member-specific content muting
- Invite history and analytics
- Email notifications when invited

### V3 Features
- Team claiming (members link to their roster)
- Member-specific power rankings
- In-app notifications
- Member activity tracking
- Custom member permissions

## Error Handling

### Common Error Responses

**Invalid invite token**
```json
{
  "detail": "Invalid or expired invite"
}
```

**Already a member**
```json
{
  "detail": "You are already a member of this league"
}
```

**No access**
```json
{
  "detail": "You don't have access to this league"
}
```

**Not the owner**
```json
{
  "detail": "Only league owner can perform this action"
}
```

## Testing

### Manual Testing Checklist

1. Create league as user A
2. Generate invite link
3. Visit invite URL (logged out) → should show league info
4. Log in as user B
5. Accept invite → should join league
6. Access league hub as user B → should see standings/matchups
7. Try to access settings as user B → should be denied
8. Remove member as user A → user B loses access
9. Try to reuse invite token → should fail

### API Testing

```bash
# Generate invite
curl -X POST http://localhost:8000/members/admin/leagues/1/invite \
  -H "Authorization: Bearer {token}"

# Validate invite (public)
curl http://localhost:8000/members/invite/{token}

# Accept invite
curl -X POST http://localhost:8000/members/invite/{token}/accept \
  -H "Authorization: Bearer {token}"

# Check access
curl http://localhost:8000/members/leagues/1/access \
  -H "Authorization: Bearer {token}"

# Update preferences
curl -X PATCH http://localhost:8000/members/leagues/1/members/me/preferences \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"mute_waivers": true}'
```

## Implementation Notes

### Why Commissioner Membership Records?

Every league owner has a corresponding LeagueMember record with role=commissioner. This:
- Provides consistent authorization logic
- Allows tracking commissioner preferences too
- Simplifies "all my leagues" queries (owned + member)
- Enables future multi-commissioner support

### Why No Expiration?

For MVP, invite links don't expire because:
- Simpler implementation and testing
- Most leagues are private/trusted groups
- Can revoke invite by deleting the pending membership
- Easy to add expiration later without breaking changes

### Why Separate Member Preferences?

Member preferences are stored per-membership (not per-user) because:
- Users might want different settings for different leagues
- Preferences are scoped to league context
- Allows future per-league customization
- Keeps user model clean

## Support

For questions or issues with the membership system:
1. Check this documentation first
2. Review API endpoint docstrings
3. Check error responses for details
4. Test with the manual checklist above
